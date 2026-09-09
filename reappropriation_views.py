from datetime import date
import pandas as pd
import streamlit as st
from models import BudgetHead, Reappropriation


def render_reappropriation_module(db):
    st.title("🔄 Reappropriation Management (Re+ & Re-)")
    st.caption("Transfer & Adjust Sanctioned Budget Allocations Between Heads")

    st.markdown("""
        > [!NOTE]
        > **Re+ (Reappropriate In):** Increases budget allocation for a target budget head.\n
        > **Re- (Reappropriate Out):** Surrenders / transfers out funds from a source budget head.
    """)

    budget_heads = db.query(BudgetHead).all()

    if not budget_heads:
        st.warning("Please add budget heads first before creating reappropriation entries.")
        return

    head_map = {f"{h.code} - {h.description} ({getattr(h, 'category', 'ERE')})": h.id for h in budget_heads}

    tab_in, tab_out = st.tabs(["📥 Reappropriate In (Re+)", "📤 Reappropriate Out (Re-)"])

    # 1. REAPPROPRIATE IN (Re+)
    with tab_in:
        st.markdown("##### Add Budget Funds (Re+)")
        with st.form("reap_in_form", clear_on_submit=True):
            target_label = st.selectbox("Target Budget Head (Receiving Re+)", list(head_map.keys()), key="reap_in_target")
            amount = st.number_input("Reappropriation In Amount (PKR)", min_value=1.0, step=5000.0, key="reap_in_amt")
            reason = st.text_input("Reason / Government Sanction Ref", placeholder="e.g. Sanction letter #FD-2026/04", key="reap_in_reason")

            submit_in = st.form_submit_button("Submit Re+ (Reappropriate In)")

            if submit_in:
                target_id = head_map[target_label]
                username = st.session_state.get("username", "admin")

                reap_entry = Reappropriation(
                    section_id=None,
                    target_head_id=target_id,
                    amount=amount,
                    reap_type="IN",
                    reason=reason.strip() if reason else None,
                    created_by=username,
                    reap_date=date.today()
                )
                db.add(reap_entry)
                db.commit()
                st.success(f"Successfully recorded Re+ of PKR {amount:,.2f} into '{target_label}'!")
                st.rerun()

    # 2. REAPPROPRIATE OUT (Re-)
    with tab_out:
        st.markdown("##### Surrender / Transfer Out Budget Funds (Re-)")
        with st.form("reap_out_form", clear_on_submit=True):
            source_label = st.selectbox("Source Budget Head (Surrendering Re-)", list(head_map.keys()), key="reap_out_source")
            amount = st.number_input("Reappropriation Out Amount (PKR)", min_value=1.0, step=5000.0, key="reap_out_amt")
            reason = st.text_input("Reason / Surrender Letter Ref", placeholder="e.g. Surrender letter #FD-2026/09", key="reap_out_reason")

            submit_out = st.form_submit_button("Submit Re- (Reappropriate Out)")

            if submit_out:
                source_id = head_map[source_label]
                username = st.session_state.get("username", "admin")

                reap_entry = Reappropriation(
                    section_id=None,
                    source_head_id=source_id,
                    amount=amount,
                    reap_type="OUT",
                    reason=reason.strip() if reason else None,
                    created_by=username,
                    reap_date=date.today()
                )
                db.add(reap_entry)
                db.commit()
                st.success(f"Successfully recorded Re- of PKR {amount:,.2f} out of '{source_label}'!")
                st.rerun()

    st.markdown("---")

    # --- REAPPROPRIATION AUDIT LOG TABLE ---
    st.markdown("##### Reappropriation Audit Log History")
    all_reaps = db.query(Reappropriation).order_by(Reappropriation.id.desc()).all()

    if all_reaps:
        reap_data = []
        for r in all_reaps:
            head_str = "-"
            if r.reap_type == "IN" and r.target_head:
                head_str = f"{r.target_head.code} - {r.target_head.description}"
            elif r.reap_type == "OUT" and r.source_head:
                head_str = f"{r.source_head.code} - {r.source_head.description}"

            reap_data.append({
                "ID": r.id,
                "Date": r.reap_date,
                "Type": "🟢 Re+" if r.reap_type == "IN" else "🔴 Re-",
                "Budget Head": head_str,
                "Amount (PKR)": f"{r.amount:,.2f}",
                "Reason / Ref": r.reason or "-",
                "Created By": r.created_by
            })
        df_reap = pd.DataFrame(reap_data)
        st.dataframe(df_reap, use_container_width=True)
    else:
        st.info("No reappropriation entries recorded yet.")
