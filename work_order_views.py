from datetime import date
import pandas as pd
import streamlit as st
from models import BudgetHead, Section, WorkOrder, User


from expenditure_views import get_budget_head_balance


def render_work_orders_module(db):
    st.title("📋 Work Orders & Committed Future Expenses")
    st.caption("Record Sanctioned Work Orders Before Final Expenditure Voucher Generation")

    st.markdown("""
        > [!NOTE]
        > **Work Orders** represent approved future commitments (e.g. office renovation contracts).
        > Submitting a Work Order commits and deducts the amount from the Budget Head balance immediately, while keeping it ready for conversion to a final expenditure voucher.
    """)

    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()

    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()

    if not sections or not budget_heads:
        st.warning("Please configure sections and budget heads first.")
        return

    sec_map = {s.name: s.id for s in sections}

    col_form, col_table = st.columns([1, 2])

    with col_form:
        st.markdown("##### Submit New Work Order")

        # Section selection
        if current_user and current_user.role == "Section" and current_user.section_id:
            selected_sec_id = current_user.section_id
            st.info(f"Section: **{current_user.section.name}**")
        else:
            sec_name = st.selectbox("Select Section", list(sec_map.keys()))
            selected_sec_id = sec_map[sec_name]

        # Available heads for section
        available_heads = [
            h for h in budget_heads 
            if not h.sections or any(s.id == selected_sec_id for s in h.sections)
        ]

        if not available_heads:
            st.warning("No budget heads assigned to selected section.")
        else:
            head_map = {f"{h.code} - {h.description}": h.id for h in available_heads}

            def_order_no = st.session_state.get("wo_order_no", "")
            def_vendor = st.session_state.get("wo_vendor", "")
            def_amount = float(st.session_state.get("wo_amount", 1.0))
            def_desc = st.session_state.get("wo_description", "")
            form_ver = st.session_state.get("wo_form_ver", 0)

            with st.form(f"create_work_order_form_v{form_ver}", clear_on_submit=False):
                head_label = st.selectbox("Budget Head", list(head_map.keys()))
                order_no = st.text_input("Work Order No (e.g., WO-2026-88)", value=def_order_no)
                vendor_name = st.text_input("Vendor / Contractor Name", value=def_vendor)
                amount = st.number_input("Committed Amount (PKR)", min_value=1.0, value=max(1.0, def_amount), step=5000.0)
                description = st.text_area("Scope of Work / Description", value=def_desc)

                submit_wo = st.form_submit_button("Submit Work Order")

                if submit_wo:
                    head_id = head_map[head_label]
                    curr_bal = get_budget_head_balance(db, head_id)

                    missing = []
                    if not order_no.strip():
                        missing.append("Work Order No")
                    if not vendor_name.strip():
                        missing.append("Vendor / Contractor Name")
                    if not description.strip():
                        missing.append("Scope of Work / Description")

                    if missing:
                        st.error(f"Please fill in the missing required field(s): {', '.join(missing)}")
                    elif amount > curr_bal:
                        st.error(f"⚠️ Cannot commit Work Order of PKR {amount:,.2f}. It exceeds the available net balance of PKR {curr_bal:,.2f}.")
                    else:
                        wo = WorkOrder(
                            section_id=selected_sec_id,
                            budget_head_id=head_id,
                            order_no=order_no.strip(),
                            vendor_name=vendor_name.strip(),
                            description=description.strip(),
                            amount=amount,
                            order_date=date.today(),
                            status="Pending Expenditure",
                            created_by=username or "admin"
                        )
                        db.add(wo)
                        db.commit()

                        # Reset form fields safely
                        st.session_state["wo_order_no"] = ""
                        st.session_state["wo_vendor"] = ""
                        st.session_state["wo_amount"] = 1.0
                        st.session_state["wo_description"] = ""
                        st.session_state["wo_form_ver"] = form_ver + 1

                        st.success(f"Work Order '{order_no.strip()}' submitted and committed successfully!")
                        st.rerun()

    with col_table:
        st.markdown("##### Work Orders Log History")
        query = db.query(WorkOrder)
        if current_user and current_user.role == "Section" and current_user.section_id:
            query = query.filter(WorkOrder.section_id == current_user.section_id)
        
        all_wos = query.order_by(WorkOrder.id.desc()).all()

        if all_wos:
            wo_data = []
            for w in all_wos:
                badge = "🟢 Converted" if w.status == "Converted" else ("🟡 Pending Expenditure" if w.status == "Pending Expenditure" else "🔴 Cancelled")
                wo_data.append({
                    "Order No": w.order_no,
                    "Date": w.order_date,
                    "Section": w.section.name if w.section else "N/A",
                    "Head": w.budget_head.code if w.budget_head else "N/A",
                    "Vendor": w.vendor_name,
                    "Amount (PKR)": f"{w.amount:,.2f}",
                    "Status": badge,
                    "Description": w.description
                })
            df_wo = pd.DataFrame(wo_data)
            st.dataframe(df_wo, use_container_width=True)
        else:
            st.info("No work orders logged.")
