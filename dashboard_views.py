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
    budget_heads = db.query(BudgetHead).all()

    if selected_section_id:
        target_heads = [
            h for h in budget_heads 
            if any(s.id == selected_section_id for s in h.sections)
        ]
        total_released = 0.0
        total_spent = 0.0
        for head in target_heads:
            h_rel = (
                db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
                .filter(FundRelease.budget_head_id == head.id)
                .scalar()
            )
            h_exp = (
                db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))
                .filter(Expenditure.budget_head_id == head.id)
                .scalar()
            )
            total_released += h_rel
            total_spent += h_exp
    else:
        target_heads = budget_heads
        total_released = (
            db.query(func.coalesce(func.sum(FundRelease.amount), 0.0)).scalar()
        )
        total_spent = (
            db.query(func.coalesce(func.sum(Expenditure.amount), 0.0)).scalar()
        )

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

    breakdown_data = []

    for head in target_heads:
        # Calculate shared released for head across all releases
        h_released = db.query(
            func.coalesce(func.sum(FundRelease.amount), 0.0)
        ).filter(FundRelease.budget_head_id == head.id).scalar()

        # Calculate shared spent for head across all assigned expenditures
        h_spent = db.query(
            func.coalesce(func.sum(Expenditure.amount), 0.0)
        ).filter(Expenditure.budget_head_id == head.id).scalar()

        h_balance = h_released - h_spent

        # List heads with allocations or assigned to the section
        if h_released > 0 or h_spent > 0 or selected_section_id:
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