import pandas as pd
import streamlit as st
from models import BudgetHead, FundRelease, Section


# --- 1. BUDGET HEADS MANAGEMENT ---
def render_budget_heads_management(db):
    st.subheader("📋 Budget Head Management")

    col1, col2 = st.columns([1, 2])

    # Form to add a new Budget Head
    with col1:
        st.markdown("##### Add New Budget Head")
        with st.form("add_budget_head_form", clear_on_submit=True):
            code = st.text_input("Head Code (e.g., A03901)")
            description = st.text_input(
                "Description (e.g., Stationery & Printing)"
            )
            submit = st.form_submit_button("Add Budget Head")

            if submit:
                if code.strip() and description.strip():
                    existing = (
                        db.query(BudgetHead)
                        .filter(BudgetHead.code == code.strip().upper())
                        .first()
                    )
                    if existing:
                        st.error("Budget Head Code already exists!")
                    else:
                        new_head = BudgetHead(
                            code=code.strip().upper(),
                            description=description.strip(),
                        )
                        db.add(new_head)
                        db.commit()
                        st.success(f"Budget Head '{code.upper()}' added!")
                        st.rerun()
                else:
                    st.warning("Please fill in both Code and Description.")

    # Table displaying existing Budget Heads
    with col2:
        st.markdown("##### Existing Budget Heads")
        heads = db.query(BudgetHead).all()
        if heads:
            df_heads = pd.DataFrame(
                [{"ID": h.id, "Code": h.code, "Description": h.description} for h in heads]
            )
            st.dataframe(df_heads, use_container_width=True)
        else:
            st.info("No Budget Heads added yet.")


# --- 2. FUND RELEASE MODULE ---
def render_fund_release(db):
    st.subheader("💸 Release Funds to Section")

    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()

    if not sections or not budget_heads:
        st.warning(
            "⚠️ Please make sure at least one Section and one Budget Head exist before releasing funds."
        )
        return

    sec_map = {s.name: s.id for s in sections}
    head_map = {f"{h.code} - {h.description}": h.id for h in budget_heads}

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Fund Allocation Form")
        with st.form("release_fund_form", clear_on_submit=True):
            selected_sec_name = st.selectbox(
                "Select Section", list(sec_map.keys())
            )
            selected_head_label = st.selectbox(
                "Select Budget Head", list(head_map.keys())
            )
            amount = st.number_input("Release Amount (PKR)", min_value=1.0, step=1000.0)
            release_date = st.date_input("Release Date")

            submit = st.form_submit_button("Release Funds")

            if submit:
                sec_id = sec_map[selected_sec_name]
                head_id = head_map[selected_head_label]

                new_release = FundRelease(
                    section_id=sec_id,
                    budget_head_id=head_id,
                    amount=amount,
                    release_date=release_date,
                )
                db.add(new_release)
                db.commit()
                st.success(
                    f"Successfully released PKR {amount:,.2f} to {selected_sec_name}!"
                )
                st.rerun()

    # Table displaying recent fund releases
    with col2:
        st.markdown("##### Fund Release History")
        releases = db.query(FundRelease).order_by(FundRelease.id.desc()).all()

        if releases:
            rel_data = []
            for r in releases:
                rel_data.append(
                    {
                        "ID": r.id,
                        "Date": r.release_date,
                        "Section": r.section.name if r.section else "N/A",
                        "Budget Head": (
                            f"{r.budget_head.code} - {r.budget_head.description}"
                            if r.budget_head
                            else "N/A"
                        ),
                        "Amount (PKR)": f"{r.amount:,.2f}",
                    }
                )
            df_rel = pd.DataFrame(rel_data)
            st.dataframe(df_rel, use_container_width=True)
        else:
            st.info("No fund releases recorded yet.")