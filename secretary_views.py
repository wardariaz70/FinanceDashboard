from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Section, User


def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"


def render_secretary_dashboard(db):
    # --- 1. SCOPED CUSTOM CSS & GOOGLE FONT TYPOGRAPHY ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        /* Scope typography strictly to Secretary Dashboard */
        .sec-dashboard-container, .sec-dashboard-container * {
            font-family: 'Plus Jakarta Sans', 'Outfit', system-ui, -apple-system, sans-serif !important;
        }

        @keyframes secretarySlideDown {
            0% { opacity: 0; transform: translateY(-30px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes secretaryFadeInUp {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        .sec-greeting-main {
            animation: secretarySlideDown 1.1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            background: linear-gradient(135deg, #38BDF8 0%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3.4rem;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.5px;
            margin-bottom: 2px;
            transition: all 0.3s ease;
        }
        .sec-greeting-main:hover {
            transform: translateY(-2px) scale(1.01);
        }

        .sec-greeting-sub {
            animation: secretaryFadeInUp 1.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            color: #94A3B8;
            font-size: 1.7rem;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 25px;
        }

        .sec-section-heading {
            animation: secretaryFadeInUp 1s ease-out forwards;
            font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif !important;
            font-size: 1.35rem;
            font-weight: 700;
            color: #F8FAFC;
            letter-spacing: 0.3px;
            margin-top: 15px;
            margin-bottom: 15px;
            display: inline-block;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .sec-section-heading:hover {
            transform: translateY(-3px) scale(1.01);
            color: #38BDF8;
        }

        /* Wells Fargo Style Hero Top Card */
        .wf-hero-card {
            background: radial-gradient(circle at top left, #1E293B, #0F172A);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, border-color 0.3s ease;
        }
        .wf-hero-card:hover {
            transform: translateY(-3px) scale(1.01);
            border-color: rgba(56, 189, 248, 0.6);
        }
        .wf-account-badge {
            color: #94A3B8;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .wf-big-balance {
            font-family: 'Outfit', sans-serif !important;
            font-size: 3.8rem;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -1px;
            margin-bottom: 8px;
            transition: transform 0.3s ease, color 0.3s ease;
        }
        .wf-big-balance:hover {
            transform: translateY(-2px) scale(1.02);
            color: #38BDF8;
        }
        .wf-status-pill {
            display: inline-flex;
            align-items: center;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.3);
            color: #4ADE80;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 15px;
        }
        .wf-dot {
            height: 8px;
            width: 8px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }

        /* Metric values hover animation */
        div[data-testid="stMetricValue"] {
            animation: secretaryFadeInUp 1.1s ease-out forwards;
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), color 0.25s ease !important;
        }
        div[data-testid="stMetricValue"]:hover {
            transform: translateY(-3px) scale(1.03) !important;
            color: #38BDF8 !important;
        }

        /* Hover animation for table rows */
        .stDataFrame tbody tr {
            transition: transform 0.2s ease, background-color 0.2s ease !important;
        }
        .stDataFrame tbody tr:hover {
            transform: translateY(-2px) scale(1.005) !important;
            background-color: rgba(56, 189, 248, 0.08) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. GREETING HEADER ---
    greeting_text = get_greeting()
    st.markdown(f'<div class="sec-dashboard-container"><div class="sec-greeting-main">{greeting_text}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-dashboard-container"><div class="sec-greeting-sub">Secretary</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- 3. INTERACTIVE FILTER CONTROLS ---
    st.markdown('<div class="sec-section-heading">Executive Analytics & Filter Controls</div>', unsafe_allow_html=True)

    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        cat_options = ["All Categories", "ERE", "NON-ERE"]
        selected_cat = st.selectbox("Category Filter", cat_options)

    with col_f2:
        sec_options = {"All Sections": None}
        for s in sections:
            sec_options[s.name] = s.id
        selected_sec_label = st.selectbox("Section Filter", list(sec_options.keys()))
        selected_sec_id = sec_options[selected_sec_label]

    with col_f3:
        head_options = {"All Budget Heads": None}
        for h in budget_heads:
            head_options[f"{h.code} - {h.description}"] = h.id
        selected_head_label = st.selectbox("Budget Head Filter", list(head_options.keys()))
        selected_head_id = head_options[selected_head_label]

    with col_f4:
        date_range = st.date_input(
            "Date Range Filter",
            value=[],
            help="Select start and end dates to filter analytics."
        )

    st.markdown("---")

    # --- 4. DATA FILTERING & STATISTICAL COMPUTATION ---
    rel_query = db.query(FundRelease)
    exp_query = db.query(Expenditure)

    # Apply Section Filter
    if selected_sec_id:
        rel_query = rel_query.filter(FundRelease.section_id == selected_sec_id)
        exp_query = exp_query.filter(Expenditure.section_id == selected_sec_id)

    # Apply Budget Head Filter
    if selected_head_id:
        rel_query = rel_query.filter(FundRelease.budget_head_id == selected_head_id)
        exp_query = exp_query.filter(Expenditure.budget_head_id == selected_head_id)

    # Apply Date Range Filter
    if len(date_range) == 2:
        start_d, end_d = date_range[0], date_range[1]
        rel_query = rel_query.filter(FundRelease.release_date >= start_d, FundRelease.release_date <= end_d)
        exp_query = exp_query.filter(Expenditure.expenditure_date >= start_d, Expenditure.expenditure_date <= end_d)

    all_releases = rel_query.all()
    all_expenditures = exp_query.all()

    # Apply Category Filter on fetched records
    if selected_cat != "All Categories":
        all_releases = [r for r in all_releases if r.budget_head and getattr(r.budget_head, "category", "ERE") == selected_cat]
        all_expenditures = [e for e in all_expenditures if e.budget_head and getattr(e.budget_head, "category", "ERE") == selected_cat]

    # Metrics calculation
    total_released = sum(r.amount for r in all_releases)
    total_spent = sum(e.amount for e in all_expenditures)
    remaining_balance = total_released - total_spent
    utilization_pct = (total_spent / total_released * 100) if total_released > 0 else 0.0

    # ERE vs NON-ERE Spending breakdown
    ere_spent = sum(e.amount for e in all_expenditures if e.budget_head and getattr(e.budget_head, "category", "ERE") == "ERE")
    non_ere_spent = sum(e.amount for e in all_expenditures if e.budget_head and getattr(e.budget_head, "category", "ERE") == "NON-ERE")

    # --- 5. WELLS FARGO EXECUTIVE STYLE TOP CARD & TREND GRAPH ---
    st.markdown(f"""
        <div class="wf-hero-card">
            <div class="wf-account-badge">NH&CD Finance &bull; Executive Portfolio</div>
            <div class="wf-big-balance">PKR {total_released:,.2f}</div>
            <div class="wf-status-pill"><span class="wf-dot"></span> Budget Allocation Active</div>
        </div>
    """, unsafe_allow_html=True)

    # Time Horizon Pills & Smooth Trend Line Curve Chart
    time_horizon = st.radio(
        "Time Horizon",
        ["1M", "3M", "6M", "1Y", "All Time"],
        index=4,
        horizontal=True,
        label_visibility="collapsed"
    )

    # Generate trend data for clean spline curve area chart (Wells Fargo style)
    if all_expenditures:
        df_trend = pd.DataFrame([{
            "Date": e.expenditure_date,
            "Amount": e.amount
        } for e in all_expenditures])
        df_trend["Date"] = pd.to_datetime(df_trend["Date"])
        # Aggregate multiple expenditures on the same date to prevent looping distortion
        df_trend = df_trend.groupby("Date")["Amount"].sum().reset_index()
        df_trend = df_trend.sort_values("Date")
        df_trend["Cumulative Spent"] = df_trend["Amount"].cumsum()

        # Apply Time Horizon filtering
        if time_horizon != "All Time" and not df_trend.empty:
            max_date = df_trend["Date"].max()
            if time_horizon == "1M":
                cutoff = max_date - pd.DateOffset(months=1)
            elif time_horizon == "3M":
                cutoff = max_date - pd.DateOffset(months=3)
            elif time_horizon == "6M":
                cutoff = max_date - pd.DateOffset(months=6)
            elif time_horizon == "1Y":
                cutoff = max_date - pd.DateOffset(years=1)
            df_filtered_trend = df_trend[df_trend["Date"] >= cutoff]
            if not df_filtered_trend.empty:
                df_trend = df_filtered_trend

        fig_trend = px.area(
            df_trend,
            x="Date",
            y="Cumulative Spent",
            labels={"Cumulative Spent": "Cumulative Expenditure (PKR)"}
        )
        fig_trend.update_traces(
            line_shape="linear",
            line_color="#22C55E",
            line_width=2.5,
            fillcolor="rgba(34, 197, 94, 0.15)",
            mode="lines+markers",
            marker=dict(size=6, color="#4ADE80")
        )
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#94A3B8"),
            xaxis=dict(showgrid=False, zeroline=False, title=None),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, title=None),
            margin=dict(t=15, b=20, l=10, r=10),
            height=250
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # --- 6. HIGH-LEVEL EXECUTIVE METRICS ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Released", f"PKR {total_released:,.2f}")
    m2.metric("Total Spent", f"PKR {total_spent:,.2f}")
    m3.metric("ERE Spent", f"PKR {ere_spent:,.2f}")
    m4.metric("NON-ERE Spent", f"PKR {non_ere_spent:,.2f}")
    m5.metric("Utilization Rate", f"{utilization_pct:.1f}%")

    st.markdown("---")

    # --- 7. VISUAL GRAPHICAL ANALYTICS (PLOTLY) ---
    st.markdown('<div class="sec-section-heading">Graphical Analytics & Visual Distribution</div>', unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    # Chart 1: Donut Chart - ERE vs NON-ERE Spending
    with col_chart1:
        st.markdown("###### ERE vs NON-ERE Expenditure Distribution")
        cat_df = pd.DataFrame([
            {"Category": "ERE (Employees Related)", "Amount": ere_spent},
            {"Category": "NON-ERE (Non-Employees)", "Amount": non_ere_spent}
        ])

        if total_spent > 0:
            fig_pie = px.pie(
                cat_df,
                values="Amount",
                names="Category",
                hole=0.45,
                color="Category",
                color_discrete_map={
                    "ERE (Employees Related)": "#00CC96",
                    "NON-ERE (Non-Employees)": "#AB63FA"
                }
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans, sans-serif", color="white"),
                margin=dict(t=30, b=30, l=20, r=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expenditure recorded for current filter criteria.")

    # Chart 2: Released vs Spent per Budget Head Bar Chart
    with col_chart2:
        st.markdown("###### Released vs Spent by Budget Head")
        head_data = []
        target_heads = [h for h in budget_heads if not selected_head_id or h.id == selected_head_id]
        if selected_cat != "All Categories":
            target_heads = [h for h in target_heads if getattr(h, "category", "ERE") == selected_cat]

        for h in target_heads:
            h_rel = sum(r.amount for r in all_releases if r.budget_head_id == h.id)
            h_exp = sum(e.amount for e in all_expenditures if e.budget_head_id == h.id)
            cat_name = getattr(h, "category", "ERE")
            if h_rel > 0 or h_exp > 0:
                head_data.append({"Head Code": f"{h.code} ({cat_name})", "Metric": "Released", "Amount (PKR)": h_rel})
                head_data.append({"Head Code": f"{h.code} ({cat_name})", "Metric": "Spent", "Amount (PKR)": h_exp})

        if head_data:
            df_head_bar = pd.DataFrame(head_data)
            fig_bar = px.bar(
                df_head_bar,
                x="Head Code",
                y="Amount (PKR)",
                color="Metric",
                barmode="group",
                color_discrete_map={"Released": "#636EFA", "Spent": "#EF553B"}
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans, sans-serif", color="white"),
                margin=dict(t=30, b=30, l=20, r=20)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No budget head allocations match the selected criteria.")

    st.markdown("---")

    # --- 8. DETAILED ERE & NON-ERE SUMMARY TABLE WITH SORTING ---
    col_sum_h, col_sort = st.columns([2, 1])
    with col_sum_h:
        st.markdown('<div class="sec-section-heading">ERE vs NON-ERE Financial Summary Table</div>', unsafe_allow_html=True)
    with col_sort:
        sort_choice = st.selectbox(
            "Sort Summary By",
            ["Head Code (A-Z)", "Highest Released", "Highest Spent", "Highest Remaining", "Highest Utilization"]
        )

    summary_rows = []
    for h in budget_heads:
        if selected_head_id and h.id != selected_head_id:
            continue
        h_cat = getattr(h, "category", "ERE")
        if selected_cat != "All Categories" and h_cat != selected_cat:
            continue

        h_rel = sum(r.amount for r in all_releases if r.budget_head_id == h.id)
        h_exp = sum(e.amount for e in all_expenditures if e.budget_head_id == h.id)
        h_bal = h_rel - h_exp
        h_util = (h_exp / h_rel * 100) if h_rel > 0 else 0.0

        if h_rel > 0 or h_exp > 0:
            summary_rows.append({
                "Head Code": h.code,
                "Description": h.description,
                "Type": h_cat,
                "_raw_rel": h_rel,
                "_raw_exp": h_exp,
                "_raw_bal": h_bal,
                "_raw_util": h_util,
                "Released (PKR)": f"{h_rel:,.2f}",
                "Spent (PKR)": f"{h_exp:,.2f}",
                "Remaining (PKR)": f"{h_bal:,.2f}",
                "Utilization Rate": f"{h_util:.1f}%"
            })

    # Apply Sorting
    if sort_choice == "Highest Released":
        summary_rows.sort(key=lambda x: x["_raw_rel"], reverse=True)
    elif sort_choice == "Highest Spent":
        summary_rows.sort(key=lambda x: x["_raw_exp"], reverse=True)
    elif sort_choice == "Highest Remaining":
        summary_rows.sort(key=lambda x: x["_raw_bal"], reverse=True)
    elif sort_choice == "Highest Utilization":
        summary_rows.sort(key=lambda x: x["_raw_util"], reverse=True)
    else:
        summary_rows.sort(key=lambda x: x["Head Code"])

    if summary_rows:
        # Clean temporary raw sorting keys
        display_summary = []
        for r in summary_rows:
            clean_r = {k: v for k, v in r.items() if not k.startswith("_raw_")}
            display_summary.append(clean_r)
        df_sec_summary = pd.DataFrame(display_summary)
        st.dataframe(df_sec_summary, use_container_width=True)
    else:
        st.info("No active summary data for current filter criteria.")

    st.markdown("---")

    # --- 9. EXPENDITURE LOG HISTORY ---
    st.markdown('<div class="sec-section-heading">Detailed Expenditure Log History</div>', unsafe_allow_html=True)

    if all_expenditures:
        exp_table_data = []
        for e in all_expenditures:
            exp_table_data.append({
                "Bill No": e.bill_no,
                "Date": e.expenditure_date,
                "Section": e.section.name if e.section else "N/A",
                "Budget Head": f"{e.budget_head.code} ({getattr(e.budget_head, 'category', 'ERE')})" if e.budget_head else "N/A",
                "Purpose": e.purpose,
                "Amount (PKR)": f"{e.amount:,.2f}",
            })
        df_exp_hist = pd.DataFrame(exp_table_data)
        st.dataframe(df_exp_hist, use_container_width=True)
    else:
        st.info("No expenditure history recorded.")
