import os
import pandas as pd
from sqlalchemy import func
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Reappropriation, Section, User, WorkOrder

# Ensure uploads directory exists on disk
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_budget_head_balance(db, budget_head_id: int) -> float:
    """Calculates shared net balance for a budget head taking into account Releases, Re+, Re-, Expenditures, and Work Orders."""
    total_released = (
        db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
        .filter(FundRelease.budget_head_id == budget_head_id)
        .scalar()
    )

    reap_in = (
        db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0))
        .filter(Reappropriation.target_head_id == budget_head_id, Reappropriation.reap_type == "IN")
        .scalar()
    )

    reap_out = (
        db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0))
        .filter(Reappropriation.source_head_id == budget_head_id, Reappropriation.reap_type == "OUT")
        .scalar()
    )

    total_spent = (
        db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))
        .filter(Expenditure.budget_head_id == budget_head_id)
        .scalar()
    )

    committed_wo = (
        db.query(func.coalesce(func.sum(WorkOrder.amount), 0.0))
        .filter(WorkOrder.budget_head_id == budget_head_id, WorkOrder.status == "Pending Expenditure")
        .scalar()
    )

    return (total_released + reap_in - reap_out) - total_spent - committed_wo


def render_expenditure_entry(db):
    st.subheader("📝 Expenditure Entry & Invoice Uploads")

    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()

    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()

    if not sections or not budget_heads:
        st.warning(
            "⚠️ Please ensure Sections and Budget Heads exist before logging expenditures."
        )
        return

    sec_map = {s.name: s.id for s in sections}

    # --- PENDING WORK ORDERS PANEL ---
    wo_query = db.query(WorkOrder).filter(WorkOrder.status == "Pending Expenditure")
    if current_user and current_user.role == "Section" and current_user.section_id:
        wo_query = wo_query.filter(WorkOrder.section_id == current_user.section_id)
    pending_wos = wo_query.all()

    if pending_wos:
        with st.expander(f"Pending Unrecorded Work Orders ({len(pending_wos)}) - Click to Convert"):
            st.info("The following Work Orders have been committed but not yet recorded as final expenditure vouchers:")
            for wo in pending_wos:
                col_wo1, col_wo2 = st.columns([3, 1])
                with col_wo1:
                    st.write(f"**WO #{wo.order_no}** | Vendor: `{wo.vendor_name}` | Head: `{wo.budget_head.code if wo.budget_head else 'N/A'}` | Amount: **PKR {wo.amount:,.2f}**\n\n*Scope:* {wo.description}")
                with col_wo2:
                    if st.button("Convert to Expenditure", key=f"conv_wo_{wo.id}"):
                        st.session_state["active_convert_wo_id"] = wo.id
                        st.session_state["exp_bill_no"] = wo.order_no
                        st.session_state["exp_purpose"] = f"Work Order #{wo.order_no}: {wo.description} (Vendor: {wo.vendor_name})"
                        st.session_state["exp_amount"] = float(wo.amount)
                        st.success(f"Loaded Work Order #{wo.order_no} details into form below!")
                        st.rerun()
            st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Log Expenditure")

        if current_user and current_user.role == "Section" and current_user.section:
            selected_sec_name = current_user.section.name
            st.info(f"Section: **{selected_sec_name}**")
            sec_id = current_user.section_id
        else:
            selected_sec_name = st.selectbox(
                "Select Section", list(sec_map.keys())
            )
            sec_id = sec_map[selected_sec_name]

        # Filter available budget heads: only budget heads assigned to this section
        available_heads = [
            h for h in budget_heads
            if any(s.id == sec_id for s in h.sections)
        ]

        if not available_heads:
            st.warning(f"No budget heads assigned to section **{selected_sec_name}**.")
            return

        head_map = {f"{h.code} - {h.description}": h.id for h in available_heads}

        selected_head_label = st.selectbox(
            "Select Budget Head", list(head_map.keys())
        )
        head_id = head_map[selected_head_label]

        current_balance = get_budget_head_balance(db, head_id)

        if current_balance <= 0:
            st.error(f"Shared Net Available Balance: PKR {current_balance:,.2f}")
        else:
            st.success(f"Shared Net Available Balance: PKR {current_balance:,.2f}")

        # Get pre-filled session state values (e.g. from Work Order conversion)
        def_bill_no = st.session_state.get("exp_bill_no", "")
        def_purpose = st.session_state.get("exp_purpose", "")
        def_amount = float(st.session_state.get("exp_amount", 1.0))

        with st.form("expenditure_form", clear_on_submit=False):
            bill_no = st.text_input("Bill / Voucher Number", value=def_bill_no)
            purpose = st.text_area("Purpose / Description", value=def_purpose)
            amount = st.number_input(
                "Amount (PKR)", min_value=1.0, value=max(1.0, def_amount), step=500.0
            )
            exp_date = st.date_input("Expenditure Date")

            uploaded_file = st.file_uploader(
                "Attach Invoice / Receipt (PDF, PNG, JPG)",
                type=["pdf", "png", "jpg", "jpeg"],
            )

            submit = st.form_submit_button("Record Expenditure")

            if submit:
                missing_fields = []
                if not bill_no.strip():
                    missing_fields.append("Bill / Voucher Number")
                if not purpose.strip():
                    missing_fields.append("Purpose / Description")

                if missing_fields:
                    st.error(f"Please fill in the missing required field(s): {', '.join(missing_fields)}")
                else:
                    saved_file_path = None

                    # Handle File Saving locally
                    if uploaded_file is not None:
                        ext = uploaded_file.name.split(".")[-1]
                        clean_bill_no = "".join(
                            c for c in bill_no if c.isalnum() or c in ("_", "-")
                        )
                        filename = f"bill_{clean_bill_no}_{uploaded_file.name}"
                        saved_file_path = os.path.join(UPLOAD_DIR, filename)

                        with open(saved_file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    # Save DB entry
                    new_exp = Expenditure(
                        section_id=sec_id,
                        budget_head_id=head_id,
                        amount=amount,
                        purpose=purpose.strip(),
                        bill_no=bill_no.strip(),
                        expenditure_date=exp_date,
                        invoice_path=saved_file_path,
                        ddo_status="PENDING"
                    )
                    db.add(new_exp)

                    # If converted from Work Order, update Work Order status
                    converting_wo_id = st.session_state.get("active_convert_wo_id")
                    if converting_wo_id:
                        wo_obj = db.query(WorkOrder).filter(WorkOrder.id == converting_wo_id).first()
                        if wo_obj:
                            wo_obj.status = "Converted"
                        st.session_state.pop("active_convert_wo_id", None)

                    db.commit()

                    # Reset pre-filled session state values safely
                    st.session_state["exp_bill_no"] = ""
                    st.session_state["exp_purpose"] = ""
                    st.session_state["exp_amount"] = 1.0

                    st.success(
                        f"Successfully recorded PKR {amount:,.2f} against Bill #{bill_no}!"
                    )
                    st.rerun()

    # Table displaying expenditure logs with invoice download options
    with col2:
        st.markdown("##### Expenditure Log History")

        query = db.query(Expenditure)
        if current_user and current_user.role == "Section" and current_user.section_id:
            query = query.filter(Expenditure.section_id == current_user.section_id)

        expenditures = query.order_by(Expenditure.id.desc()).all()

        if expenditures:
            for e in expenditures:
                with st.expander(
                    f"Bill #{e.bill_no} | PKR {e.amount:,.2f} | {e.expenditure_date}"
                ):
                    st.write(f"**Section:** {e.section.name if e.section else 'N/A'}")
                    st.write(f"**Budget Head:** {e.budget_head.code if e.budget_head else 'N/A'}")
                    st.write(f"**Purpose:** {e.purpose}")

                    # Check and present invoice download button if file exists
                    if e.invoice_path and os.path.exists(e.invoice_path):
                        ext = os.path.splitext(e.invoice_path)[1].lower()
                        mime_map = {
                            ".pdf": "application/pdf",
                            ".png": "image/png",
                            ".jpg": "image/jpeg",
                            ".jpeg": "image/jpeg",
                        }
                        file_mime = mime_map.get(ext, "application/octet-stream")
                        filename = os.path.basename(e.invoice_path)

                        with open(e.invoice_path, "rb") as file_data:
                            st.download_button(
                                label=f"Download Attached Invoice ({filename})",
                                data=file_data.read(),
                                file_name=filename,
                                mime=file_mime,
                                key=f"dl_{e.id}",
                            )
                    else:
                        st.caption("No invoice attached for this bill.")
        else:
            st.info("No expenditures recorded yet.")