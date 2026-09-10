import pandas as pd
from sqlalchemy import func
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Reappropriation, Section, User, WorkOrder, BaseAllocationLog


def render_dashboard(db):
    st.subheader("📊 Executive Financial Overview")

    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()

    # --- 1. FILTERING LOGIC ---
    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()
    selected_section_id = None

    if current_user and current_user.role == "Section" and current_user.section_id:
        selected_section_id = current_user.section_id
        st.info(
            f"Displaying metrics for section: **{current_user.section.name}**"
        )
    else:
        sec_options = {"All Sections": None}
        for s in sections:
            sec_options[s.name] = s.id

        chosen_sec = st.selectbox(
            "Filter Overview by Section", list(sec_options.keys())
        )
        selected_section_id = sec_options[chosen_sec]

    # --- 2. CALCULATE HIGH-LEVEL METRICS ---
    if selected_section_id:
        target_heads = [
            h for h in budget_heads 
            if any(s.id == selected_section_id for s in h.sections)
        ]
        total_base = 0.0
        for head in target_heads:
            h_log = db.query(func.coalesce(func.sum(BaseAllocationLog.amount), 0.0)).filter(BaseAllocationLog.budget_head_id == head.id).scalar() or 0.0
            h_col = getattr(head, "base_allocation", 0.0) or 0.0
            total_base += (h_log + h_col)
            
        total_released = 0.0
        total_re_in = 0.0
        total_re_out = 0.0
        total_spent = 0.0
        total_wo = 0.0

        for head in target_heads:
            h_rel = (
                db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
                .filter(FundRelease.budget_head_id == head.id, FundRelease.section_id == selected_section_id)
                .scalar() or 0.0
            )
            re_in = (
                db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0))
                .filter(Reappropriation.target_head_id == head.id, Reappropriation.reap_type == "IN")
                .scalar() or 0.0
            )
            re_out = (
                db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0))
                .filter(Reappropriation.source_head_id == head.id, Reappropriation.reap_type == "OUT")
                .scalar() or 0.0
            )
            h_exp = (
                db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))
                .filter(Expenditure.budget_head_id == head.id, Expenditure.section_id == selected_section_id)
                .scalar() or 0.0
            )
            wo_amt = (
                db.query(func.coalesce(func.sum(WorkOrder.amount), 0.0))
                .filter(WorkOrder.budget_head_id == head.id, WorkOrder.section_id == selected_section_id, WorkOrder.status == "Pending Expenditure")
                .scalar() or 0.0
            )
            total_released += h_rel
            total_re_in += re_in
            total_re_out += re_out
            total_spent += h_exp
            total_wo += wo_amt
    else:
        target_heads = budget_heads
        log_base_sum = db.query(func.coalesce(func.sum(BaseAllocationLog.amount), 0.0)).scalar() or 0.0
        head_base_sum = db.query(func.coalesce(func.sum(BudgetHead.base_allocation), 0.0)).scalar() or 0.0
        total_base = log_base_sum + head_base_sum
        total_released = db.query(func.coalesce(func.sum(FundRelease.amount), 0.0)).scalar() or 0.0
        total_re_in = db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0)).filter(Reappropriation.reap_type == "IN").scalar() or 0.0
        total_re_out = db.query(func.coalesce(func.sum(Reappropriation.amount), 0.0)).filter(Reappropriation.reap_type == "OUT").scalar() or 0.0
        total_spent = db.query(func.coalesce(func.sum(Expenditure.amount), 0.0)).scalar() or 0.0
        total_wo = db.query(func.coalesce(func.sum(WorkOrder.amount), 0.0)).filter(WorkOrder.status == "Pending Expenditure").scalar() or 0.0

    net_available_pool = total_released + total_re_in - total_re_out
    net_bal_after_exp = net_available_pool - total_spent
    net_bal_after_wo = net_bal_after_exp - total_wo
    unreleased_base_pool = max(0.0, total_base - total_released)

    utilization_pct = (
        (total_spent / net_available_pool * 100) if net_available_pool > 0 else 0.0
    )

    # CSS to ensure metric card numbers never truncate with ...
    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] {
            font-size: 1.15rem !important;
            white-space: nowrap !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. METRIC CARDS DISPLAY (Clean 2-Row Layout) ---
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
    r1_c1.metric("Base Allocation", f"PKR {total_base:,.2f}")
    r1_c2.metric("Unreleased Base Pool", f"PKR {unreleased_base_pool:,.2f}")
    r1_c3.metric("Total Released", f"PKR {total_released:,.2f}")
    r1_c4.metric("Re+ (Added)", f"PKR {total_re_in:,.2f}")

    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
    r2_c1.metric("Re- (Surrendered)", f"PKR {total_re_out:,.2f}")
    r2_c2.metric("Total Spent", f"PKR {total_spent:,.2f}")
    r2_c3.metric("Net Bal (After W/O)", f"PKR {net_bal_after_wo:,.2f}", delta=f"{utilization_pct:.1f}% Used")
    r2_c4.metric("Net Bal (After Exp)", f"PKR {net_bal_after_exp:,.2f}")

    st.markdown("---")

    # --- 4. BREAKDOWN BY BUDGET HEAD TABLE ---
    st.markdown("##### Budget Head Summary Breakdown")

    breakdown_data = []

    for head in target_heads:
        h_log = db.query(func.coalesce(func.sum(BaseAllocationLog.amount), 0.0)).filter(BaseAllocationLog.budget_head_id == head.id).scalar() or 0.0
        h_col = getattr(head, "base_allocation", 0.0) or 0.0
        h_base = h_log + h_col

        rel_q = db.query(func.coalesce(func.sum(FundRelease.amount), 0.0)).filter(FundRelease.budget_head_id == head.id)
        if selected_section_id:
            rel_q = rel_q.filter(FundRelease.section_id == selected_section_id)
        h_released = rel_q.scalar() or 0.0

        re_in = db.query(
            func.coalesce(func.sum(Reappropriation.amount), 0.0)
        ).filter(Reappropriation.target_head_id == head.id, Reappropriation.reap_type == "IN").scalar() or 0.0

        re_out = db.query(
            func.coalesce(func.sum(Reappropriation.amount), 0.0)
        ).filter(Reappropriation.source_head_id == head.id, Reappropriation.reap_type == "OUT").scalar() or 0.0

        exp_q = db.query(func.coalesce(func.sum(Expenditure.amount), 0.0)).filter(Expenditure.budget_head_id == head.id)
        if selected_section_id:
            exp_q = exp_q.filter(Expenditure.section_id == selected_section_id)
        h_spent = exp_q.scalar() or 0.0

        wo_q = db.query(func.coalesce(func.sum(WorkOrder.amount), 0.0)).filter(WorkOrder.budget_head_id == head.id, WorkOrder.status == "Pending Expenditure")
        if selected_section_id:
            wo_q = wo_q.filter(WorkOrder.section_id == selected_section_id)
        wo_amt = wo_q.scalar() or 0.0

        h_net_pool = h_released + re_in - re_out
        h_bal_after_exp = h_net_pool - h_spent
        h_bal_after_wo = h_bal_after_exp - wo_amt

        if h_base > 0 or h_released > 0 or h_spent > 0 or re_in > 0 or re_out > 0 or wo_amt > 0 or selected_section_id:
            breakdown_data.append(
                {
                    "Head Code": head.code,
                    "Description": head.description,
                    "Type": getattr(head, "category", "ERE"),
                    "Base Allocation (PKR)": f"{h_base:,.2f}",
                    "Released (PKR)": f"{h_released:,.2f}",
                    "Re+ (PKR)": f"{re_in:,.2f}",
                    "Re- (PKR)": f"{re_out:,.2f}",
                    "Spent (PKR)": f"{h_spent:,.2f}",
                    "Work Orders (PKR)": f"{wo_amt:,.2f}",
                    "Net Bal (After W/O) (PKR)": f"{h_bal_after_wo:,.2f}",
                    "Net Bal (After Exp) (PKR)": f"{h_bal_after_exp:,.2f}",
                }
            )

    if breakdown_data:
        df_breakdown = pd.DataFrame(breakdown_data)
        st.dataframe(df_breakdown, use_container_width=True)
    else:
        st.info("No active budget allocations or expenditures found.")