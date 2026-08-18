import io
import pandas as pd
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Section, User


def convert_df_to_excel(df: pd.DataFrame, sheet_name: str = "Report") -> bytes:
    """Converts a pandas DataFrame into an Excel file in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def render_reports(db):
    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()
    is_secretary = (st.session_state.get("role") == "Secretary" or (current_user and current_user.role == "Secretary"))

    # Apply typography & hover animations ONLY FOR SECRETARY
    if is_secretary:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

            .sec-report-container, .sec-report-container * {
                font-family: 'Plus Jakarta Sans', 'Outfit', system-ui, -apple-system, sans-serif !important;
            }

            .sec-report-title {
                font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif !important;
                font-size: 2.2rem;
                font-weight: 800;
                color: #F8FAFC;
                letter-spacing: -0.5px;
                margin-bottom: 5px;
                transition: transform 0.25s ease;
            }
            .sec-report-title:hover {
                transform: translateY(-2px);
                color: #38BDF8;
            }

            .sec-report-sub {
                font-family: 'Outfit', sans-serif !important;
                font-size: 1.3rem;
                font-weight: 700;
                color: #E2E8F0;
                margin-top: 10px;
                margin-bottom: 10px;
                transition: transform 0.25s ease;
            }
            .sec-report-sub:hover {
                transform: translateY(-2px);
                color: #38BDF8;
            }

            div[data-testid="stMetricValue"] {
                font-family: 'Outfit', sans-serif !important;
                font-weight: 700 !important;
                transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), color 0.25s ease !important;
            }
            div[data-testid="stMetricValue"]:hover {
                transform: translateY(-3px) scale(1.03) !important;
                color: #38BDF8 !important;
            }

            .stDataFrame tbody tr {
                transition: transform 0.2s ease, background-color 0.2s ease !important;
            }
            .stDataFrame tbody tr:hover {
                transform: translateY(-2px) scale(1.005) !important;
                background-color: rgba(56, 189, 248, 0.08) !important;
            }
            </style>
        """, unsafe_allow_html=True)

    if is_secretary:
        st.markdown('<div class="sec-report-container"><div class="sec-report-title">Financial Reports & Excel Export</div></div>', unsafe_allow_html=True)
    else:
        st.subheader("📈 Financial Reports & Excel Export")

    sections = db.query(Section).all()
    budget_heads = db.query(BudgetHead).all()

    # --- FILTER SECTION ---
    if is_secretary:
        st.markdown('<div class="sec-report-container"><div class="sec-report-sub">Filter Report Data</div></div>', unsafe_allow_html=True)
    else:
        st.markdown("##### 🔍 Filter Report Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Section Filter
        if current_user and current_user.role == "Section" and current_user.section_id:
            sec_filter = current_user.section_id
            st.info(f"Section Locked: **{current_user.section.name}**")
        else:
            sec_options = {"All Sections": None}
            for s in sections:
                sec_options[s.name] = s.id
            selected_sec_name = st.selectbox(
                "Filter by Section", list(sec_options.keys())
            )
            sec_filter = sec_options[selected_sec_name]

    with col2:
        # Budget Head Filter
        head_options = {"All Budget Heads": None}
        filtered_heads = [
            h for h in budget_heads
            if not sec_filter or any(s.id == sec_filter for s in h.sections)
        ]
        for h in filtered_heads:
            head_options[f"{h.code} - {h.description}"] = h.id
        selected_head_label = st.selectbox(
            "Filter by Budget Head", list(head_options.keys())
        )
        head_filter = head_options[selected_head_label]

    with col3:
        # Report Type Selector
        report_type = st.selectbox(
            "Select Report Type",
            ["Expenditure Report", "Fund Release Report", "Combined Summary"],
        )

    st.markdown("---")

    # --- REPORT GENERATION ---

    # 1. EXPENDITURE REPORT
    if report_type == "Expenditure Report":
        if is_secretary:
            st.markdown('<div class="sec-report-container"><div class="sec-report-sub">Expenditure Report</div></div>', unsafe_allow_html=True)
        else:
            st.markdown("#### 📝 Expenditure Report")
        query = db.query(Expenditure)

        if sec_filter:
            query = query.filter(Expenditure.section_id == sec_filter)
        if head_filter:
            query = query.filter(Expenditure.budget_head_id == head_filter)

        expenditures = query.order_by(Expenditure.expenditure_date.desc()).all()

        if expenditures:
            data = [
                {
                    "ID": e.id,
                    "Date": e.expenditure_date,
                    "Bill No": e.bill_no,
                    "Section": e.section.name if e.section else "N/A",
                    "Budget Head Code": e.budget_head.code if e.budget_head else "N/A",
                    "Budget Head Description": (
                        e.budget_head.description if e.budget_head else "N/A"
                    ),
                    "Type": getattr(e.budget_head, "category", "ERE") if e.budget_head else "N/A",
                    "Purpose": e.purpose,
                    "Amount (PKR)": e.amount,
                }
                for e in expenditures
            ]
            df = pd.DataFrame(data)

            # Display total metric
            total_exp = df["Amount (PKR)"].sum()
            st.metric("Total Filtered Expenditure", f"PKR {total_exp:,.2f}")

            # Display Data Table
            st.dataframe(df, use_container_width=True)

            # Export Button
            excel_data = convert_df_to_excel(df, sheet_name="Expenditures")
            st.download_button(
                label="Export Expenditure Report to Excel" if is_secretary else "📥 Export Expenditure Report to Excel",
                data=excel_data,
                file_name="Expenditure_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No expenditure records match the selected filters.")

    # 2. FUND RELEASE REPORT
    elif report_type == "Fund Release Report":
        if is_secretary:
            st.markdown('<div class="sec-report-container"><div class="sec-report-sub">Fund Release Report</div></div>', unsafe_allow_html=True)
        else:
            st.markdown("#### 💸 Fund Release Report")
        query = db.query(FundRelease)

        if sec_filter:
            query = query.filter(FundRelease.section_id == sec_filter)
        if head_filter:
            query = query.filter(FundRelease.budget_head_id == head_filter)

        releases = query.order_by(FundRelease.release_date.desc()).all()

        if releases:
            data = [
                {
                    "ID": r.id,
                    "Release Date": r.release_date,
                    "Section": r.section.name if r.section else "N/A",
                    "Budget Head Code": r.budget_head.code if r.budget_head else "N/A",
                    "Budget Head Description": (
                        r.budget_head.description if r.budget_head else "N/A"
                    ),
                    "Amount (PKR)": r.amount,
                }
                for r in releases
            ]
            df = pd.DataFrame(data)

            total_rel = df["Amount (PKR)"].sum()
            st.metric("Total Filtered Releases", f"PKR {total_rel:,.2f}")

            st.dataframe(df, use_container_width=True)

            excel_data = convert_df_to_excel(df, sheet_name="Fund Releases")
            st.download_button(
                label="Export Fund Release Report to Excel" if is_secretary else "📥 Export Fund Release Report to Excel",
                data=excel_data,
                file_name="Fund_Release_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No fund release records match the selected filters.")

    # 3. COMBINED SUMMARY REPORT
    elif report_type == "Combined Summary":
        if is_secretary:
            st.markdown('<div class="sec-report-container"><div class="sec-report-sub">Combined Section & Head Financial Summary</div></div>', unsafe_allow_html=True)
        else:
            st.markdown("#### 📊 Combined Section & Head Financial Summary")

        summary_rows = []
        target_sections = (
            [s for s in sec_filter] if isinstance(sec_filter, list) else ([s for s in sections if s.id == sec_filter] if sec_filter else sections)
        )
        target_heads = (
            [h for h in budget_heads if h.id == head_filter]
            if head_filter
            else budget_heads
        )

        for sec in target_sections:
            sec_heads = [h for h in target_heads if any(s.id == sec.id for s in h.sections)]
            for head in sec_heads:
                # Sum Released for head (shared pool)
                total_rel = (
                    db.query(func.coalesce(func.sum(FundRelease.amount), 0.0))
                    .filter(FundRelease.budget_head_id == head.id)
                    .scalar()
                )

                # Sum Spent for head across all assigned expenditures
                total_spent = (
                    db.query(func.coalesce(func.sum(Expenditure.amount), 0.0))
                    .filter(Expenditure.budget_head_id == head.id)
                    .scalar()
                )

                if total_rel > 0 or total_spent > 0:
                    summary_rows.append(
                        {
                            "Section": sec.name,
                            "Budget Head": f"{head.code} - {head.description}",
                            "Shared Total Released (PKR)": total_rel,
                            "Shared Total Spent (PKR)": total_spent,
                            "Shared Remaining Balance (PKR)": total_rel - total_spent,
                        }
                    )

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)
            st.dataframe(df_summary, use_container_width=True)

            excel_data = convert_df_to_excel(df_summary, sheet_name="Financial Summary")
            st.download_button(
                label="Export Financial Summary to Excel" if is_secretary else "📥 Export Financial Summary to Excel",
                data=excel_data,
                file_name="Financial_Summary_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No summary data available for selected filters.")