import os
import pandas as pd
from sqlalchemy import func
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Section, User

# Ensure uploads directory exists on disk
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_budget_head_balance(db, budget_head_id: int) -> float:
    """Calculates shared remaining balance for a budget head across all assigned sections."""
    total_released = (
        db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
        .filter(FundRelease.budget_head_id == budget_head_id)
        .scalar()
    )

    total_spent = (
        db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))
        .filter(Expenditure.budget_head_id == budget_head_id)
        .scalar()
    )

    return total_released - total_spent


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
            st.error(f"Shared Available Balance: PKR {current_balance:,.2f}")
        else:
            st.success(f"Shared Available Balance: PKR {current_balance:,.2f}")

        with st.form("expenditure_form", clear_on_submit=True):
            bill_no = st.text_input("Bill / Voucher Number")
            purpose = st.text_area("Purpose / Description")
            amount = st.number_input(
                "Amount (PKR)", min_value=1.0, step=500.0
            )
            exp_date = st.date_input("Expenditure Date")

            # File Upload Input Component
            uploaded_file = st.file_uploader(
                "Attach Invoice / Receipt (PDF, PNG, JPG)",
                type=["pdf", "png", "jpg", "jpeg"],
            )

            submit = st.form_submit_button("Record Expenditure")

            if submit:
                if not bill_no.strip() or not purpose.strip():
                    st.warning("Please enter both a Bill Number and Purpose.")
                elif amount > current_balance:
                    st.error(
                        f"Insufficient balance! Available: PKR {current_balance:,.2f}"
                    )
                else:
                    saved_file_path = None

                    # Handle File Saving locally
                    if uploaded_file is not None:
                        # Clean filename to avoid overwrite conflicts
                        ext = uploaded_file.name.split(".")[-1]
                        clean_bill_no = "".join(
                            c for c in bill_no if c.isalnum() or c in ("_", "-")
                        )
                        filename = f"bill_{clean_bill_no}_{uploaded_file.name}"
                        saved_file_path = os.path.join(UPLOAD_DIR, filename)

                        # Save binary content to disk
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
                    )
                    db.add(new_exp)
                    db.commit()
                    st.success(
                        f"Recorded PKR {amount:,.2f} against Bill #{bill_no}!"
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
                        with open(e.invoice_path, "rb") as file_data:
                            filename = os.path.basename(e.invoice_path)
                            st.download_button(
                                label=f"📎 Download Attached Invoice ({filename})",
                                data=file_data,
                                file_name=filename,
                                key=f"dl_{e.id}",
                            )
                    else:
                        st.caption("No invoice attached for this bill.")
        else:
            st.info("No expenditures recorded yet.")