import pandas as pd
from sqlalchemy import func
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Section, User


def render_dashboard(db):
    st.subheader("📊 Executive Financial Overview")

    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()

    # --- 1. FILTERING LOGIC ---
    sections = db.query(Section).all()
    selected_section_id = None

    if current_user and current_user.role == "Section" and current_user.section_id:
        # Lock to user's assigned section
        selected_section_id = current_user.section_id
        st.info(
            f"Displaying metrics for section: **{current_user.section.name}**"
        )
    else:
        # Admin / Finance view: Allow filtering by section or viewing overall
        sec_options = {"All Sections": None}
        for s in sections:
            sec_options[s.name] = s.id

        chosen_sec = st.selectbox(
            "Filter Overview by Section", list(sec_options.keys())
        )
        selected_section_id = sec_options[chosen_sec]

    # --- 2. CALCULATE HIGH-LEVEL METRICS ---
    rel_query = db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
    exp_query = db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))

    if selected_section_id:
        rel_query = rel_query.filter(
            FundRelease.section_id == selected_section_id
        )
        exp_query = exp_query.filter(
            Expenditure.section_id == selected_section_id
        )

    total_released = rel_query.scalar()
    total_spent = exp_query.scalar()
    remaining_balance = total_released - total_spent

    # Calculate utilization percentage
    utilization_pct = (
        (total_spent / total_released * 100) if total_released > 0 else 0.0
    )

    # # --- 3. METRIC CARDS DISPLAY ---
    # col1, col2, col3, col4 = st.columns(4)

    # col1.metric("Total Released", f"PKR {total_released:,.2f}")
    # col2.metric("Total Spent", f"PKR {total_spent:,.2f}")
    # col3.metric(
    #     "Remaining Balance",
    #     f"PKR {remaining_balance:,.2f}",
    #     delta=f"{-utilization_pct:.1f}% Used",
    #     delta_color="inverse",
    # )
    # col4.metric("Budget Utilization", f"{utilization_pct:.1f}%")
# --- 3. METRIC DISPLAY (Stacked Line-by-Line) ---
    st.metric("Total Released", f"PKR {total_released:,.2f}")
    st.metric("Total Spent", f"PKR {total_spent:,.2f}")
    st.metric(
        "Remaining Balance",
        f"PKR {remaining_balance:,.2f}",
        delta=f"{-utilization_pct:.1f}% Used",
        delta_color="inverse",
    )
    st.metric("Budget Utilization", f"{utilization_pct:.1f}%")
    st.markdown("---")

    # --- 4. BREAKDOWN BY BUDGET HEAD TABLE ---
    st.markdown("##### 📌 Budget Head Summary Breakdown")

    budget_heads = db.query(BudgetHead).all()
    breakdown_data = []

    for head in budget_heads:
        # Calculate released for head
        rel_head_q = db.query(
            func.coalesce(func.sum(FundRelease.amount), 0.0)
        ).filter(FundRelease.budget_head_id == head.id)
        # Calculate spent for head
        exp_head_q = db.query(
            func.coalesce(func.sum(Expenditure.amount), 0.0)
        ).filter(Expenditure.budget_head_id == head.id)

        if selected_section_id:
            rel_head_q = rel_head_q.filter(
                FundRelease.section_id == selected_section_id
            )
            exp_head_q = exp_head_q.filter(
                Expenditure.section_id == selected_section_id
            )

        h_released = rel_head_q.scalar()
        h_spent = exp_head_q.scalar()
        h_balance = h_released - h_spent

        # Only list heads that have had releases or expenditures
        if h_released > 0 or h_spent > 0:
            breakdown_data.append(
                {
                    "Head Code": head.code,
                    "Description": head.description,
                    "Released (PKR)": f"{h_released:,.2f}",
                    "Spent (PKR)": f"{h_spent:,.2f}",
                    "Balance (PKR)": f"{h_balance:,.2f}",
                }
            )

    if breakdown_data:
        df_breakdown = pd.DataFrame(breakdown_data)
        st.dataframe(df_breakdown, use_container_width=True)
    else:
        st.info("No active budget allocations or expenditures found.")