from datetime import date
import pandas as pd
import streamlit as st
from models import Expenditure, User, Section, BudgetHead


def render_ddo_module(db):
    st.title("🛡️ DDO Scrutiny & Verification Module")
    st.caption("Role: Drawing & Disbursing Officer (DDO)")

    st.markdown("""
        > [!NOTE]
        > The DDO scrutinizes expenditures submitted by sections and marks them as **IN PROGRESS**, **AUTHORISED**, **OBJECTION**, or **REJECTED**.
        > DDO status decisions reflect immediately across the entire portal.
    """)

    all_exps = db.query(Expenditure).order_by(Expenditure.id.desc()).all()

    # Metrics Summary Cards
    in_prog_count = sum(1 for e in all_exps if getattr(e, "ddo_status", "PENDING") in ("IN PROGRESS", "IN_PROGRESS"))
    auth_count = sum(1 for e in all_exps if getattr(e, "ddo_status", "PENDING") == "AUTHORISED")
    obj_count = sum(1 for e in all_exps if getattr(e, "ddo_status", "PENDING") == "OBJECTION")
    rej_count = sum(1 for e in all_exps if getattr(e, "ddo_status", "PENDING") == "REJECTED")
    pend_count = sum(1 for e in all_exps if getattr(e, "ddo_status", "PENDING") == "PENDING")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Pending", pend_count)
    m2.metric("In Progress", in_prog_count)
    m3.metric("Authorised", auth_count)
    m4.metric("Objection", obj_count)
    m5.metric("Rejected", rej_count)

    st.markdown("---")

    # --- 1. SEARCH BAR ---
    search_query = st.text_input("🔍 Search Expenditure Entries (by Bill #, Section, Head Code, Purpose, or Status)", placeholder="e.g. Bill #104, Admin, A01101, Authorised...").strip().lower()

    filtered_exps = all_exps
    if search_query:
        filtered_exps = [
            e for e in all_exps
            if search_query in (e.bill_no or "").lower()
            or search_query in (e.section.name if e.section else "").lower()
            or search_query in (e.budget_head.code if e.budget_head else "").lower()
            or search_query in (e.purpose or "").lower()
            or search_query in (getattr(e, "ddo_status", "PENDING") or "").lower()
        ]

    st.markdown(f"##### Expenditure Verification Table ({len(filtered_exps)} entries)")

    if filtered_exps:
        status_options = ["PENDING", "IN PROGRESS", "AUTHORISED", "OBJECTION", "REJECTED"]

        # Render Interactive Table Row by Row with direct status update
        for exp in filtered_exps:
            current_status = getattr(exp, "ddo_status", "PENDING")
            if current_status == "IN_PROGRESS":
                current_status = "IN PROGRESS"

            status_color_map = {
                "AUTHORISED": "🟢",
                "IN PROGRESS": "🔵",
                "OBJECTION": "🟡",
                "REJECTED": "🔴",
                "PENDING": "⏳"
            }
            icon = status_color_map.get(current_status, "⏳")

            with st.expander(f"{icon} Bill #{exp.bill_no} | {exp.section.name if exp.section else 'N/A'} | PKR {exp.amount:,.2f} | Status: **{current_status}**"):
                st.write(f"**Expenditure Purpose:** {exp.purpose}")
                st.write(f"**Budget Head:** {exp.budget_head.code if exp.budget_head else 'N/A'} - {exp.budget_head.description if exp.budget_head else ''}")
                st.write(f"**Expenditure Date:** {exp.expenditure_date}")

                with st.form(key=f"ddo_row_form_{exp.id}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        curr_idx = status_options.index(current_status) if current_status in status_options else 0
                        selected_new_status = st.selectbox(
                            "Update DDO Status",
                            status_options,
                            index=curr_idx,
                            key=f"status_sel_{exp.id}"
                        )
                    with c2:
                        remarks_input = st.text_input(
                            "DDO Remarks / Objections",
                            value=exp.ddo_remarks or "",
                            placeholder="Enter DDO scrutiny notes...",
                            key=f"remarks_in_{exp.id}"
                        )

                    save_row = st.form_submit_button("Save DDO Decision")

                    if save_row:
                        exp.ddo_status = selected_new_status
                        exp.ddo_remarks = remarks_input.strip() if remarks_input else None
                        exp.ddo_action_date = date.today()
                        db.commit()
                        st.success(f"Updated Bill #{exp.bill_no} status to '{selected_new_status}'!")
                        st.rerun()

        st.markdown("---")

        # Summary Log DataFrame for Export / Viewing
        st.markdown("##### DDO Verification Summary Table")
        log_data = []
        for e in filtered_exps:
            st_val = getattr(e, "ddo_status", "PENDING")
            badge = "🟢 AUTHORISED" if st_val == "AUTHORISED" else ("🔵 IN PROGRESS" if st_val in ("IN PROGRESS", "IN_PROGRESS") else ("🟡 OBJECTION" if st_val == "OBJECTION" else ("🔴 REJECTED" if st_val == "REJECTED" else "⏳ PENDING")))
            log_data.append({
                "Bill No": e.bill_no,
                "Date": e.expenditure_date,
                "Section": e.section.name if e.section else "N/A",
                "Head Code": e.budget_head.code if e.budget_head else "N/A",
                "Amount (PKR)": f"{e.amount:,.2f}",
                "DDO Status": badge,
                "Remarks": e.ddo_remarks or "-",
                "Action Date": e.ddo_action_date or "-"
            })
        df_log = pd.DataFrame(log_data)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No expenditure records match your search query.")
