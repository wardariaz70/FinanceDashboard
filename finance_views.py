import os
import pandas as pd
import streamlit as st
from models import BudgetHead, Expenditure, FundRelease, Section, User


# --- 1. BUDGET HEADS MANAGEMENT ---
def render_budget_heads_management(db):
    st.subheader("📋 Budget Head Management")

    username = st.session_state.get("username")
    current_user = db.query(User).filter(User.username == username).first()

    all_sections = db.query(Section).all()
    
    def get_sec_label(sec):
        usernames = [u.username for u in sec.users]
        if usernames:
            return f"{sec.name} ({', '.join(usernames)})"
        return sec.name

    label_to_sec = {get_sec_label(s): s for s in all_sections}
    sec_id_to_label = {s.id: get_sec_label(s) for s in all_sections}

    col1, col2 = st.columns([1, 2])

    # Form to add a new Budget Head
    with col1:
        st.markdown("##### Add New Budget Head")
        with st.form("add_budget_head_form", clear_on_submit=True):
            code = st.text_input("Head Code (e.g., A03901)")
            description = st.text_input(
                "Description (e.g., Stationery & Printing)"
            )
            category = st.radio(
                "Budget Head Type (Required)",
                ["ERE", "NON-ERE"],
                horizontal=True,
                help="Specify if this head belongs to ERE (Employees Related Expenses) or NON-ERE."
            )
            selected_labels = st.multiselect(
                "Assign to Sections / Officers",
                options=list(label_to_sec.keys()),
                help="Select section(s) or section officers (e.g. so_admin) allowed to view and spend under this budget head."
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
                        assigned_sections = [label_to_sec[lbl] for lbl in selected_labels if lbl in label_to_sec]
                        new_head = BudgetHead(
                            code=code.strip().upper(),
                            description=description.strip(),
                            category=category,
                            sections=assigned_sections,
                        )
                        db.add(new_head)
                        db.commit()
                        st.success(f"Budget Head '{code.upper()}' ({category}) added successfully!")
                        st.rerun()
                else:
                    st.warning("Please fill in both Code and Description.")

    # Table displaying existing Budget Heads & Edit/Delete Options
    with col2:
        st.markdown("##### Existing Budget Heads")
        heads = db.query(BudgetHead).all()
        if heads:
            heads_data = []
            for h in heads:
                assigned_sec_names = ", ".join([get_sec_label(s) for s in h.sections]) if h.sections else "None (Unassigned)"
                heads_data.append({
                    "ID": h.id,
                    "Code": h.code,
                    "Description": h.description,
                    "Type": getattr(h, "category", "ERE"),
                    "Assigned Sections / Officers": assigned_sec_names
                })
            df_heads = pd.DataFrame(heads_data)
            st.dataframe(df_heads, use_container_width=True)

            # Update Section Assignments & Category for an existing Budget Head
            st.markdown("---")
            st.markdown("##### Edit Budget Head Setup")
            head_options = {f"{h.code} - {h.description}": h for h in heads}
            selected_head_label = st.selectbox(
                "Select Budget Head to Edit", list(head_options.keys())
            )
            target_head = head_options[selected_head_label]
            current_assigned_labels = [sec_id_to_label[s.id] for s in target_head.sections if s.id in sec_id_to_label]
            current_category = getattr(target_head, "category", "ERE")

            with st.form("edit_budget_head_sections_form"):
                new_category = st.radio(
                    f"Update Type for {target_head.code}",
                    ["ERE", "NON-ERE"],
                    index=0 if current_category == "ERE" else 1,
                    horizontal=True
                )
                new_sec_selection = st.multiselect(
                    f"Assigned Sections / Officers for {target_head.code}",
                    options=list(label_to_sec.keys()),
                    default=current_assigned_labels
                )
                save_changes = st.form_submit_button("Update Budget Head Setup")

                if save_changes:
                    target_head.category = new_category
                    target_head.sections = [label_to_sec[lbl] for lbl in new_sec_selection if lbl in label_to_sec]
                    db.commit()
                    st.success(f"Updated setup for '{target_head.code}'!")
                    st.rerun()

            # Admin-Only Delete Budget Head Section
            if current_user and current_user.role == "Finance":
                st.markdown("---")
                st.markdown("##### 🗑️ Delete Budget Head (Admin Only)")
                del_head_label = st.selectbox(
                    "Select Budget Head to Delete", 
                    list(head_options.keys()), 
                    key="del_budget_head_select"
                )
                target_del_head = head_options[del_head_label]

                with st.expander(f"⚠️ Confirm Deletion for {target_del_head.code}"):
                    st.warning(
                        f"Deleting **{target_del_head.code} - {target_del_head.description}** will permanently remove it along with all associated fund releases, expenditures, and attached invoice files!"
                    )
                    with st.form("delete_budget_head_form"):
                        confirm_check = st.checkbox(f"I confirm deletion of {target_del_head.code}")
                        delete_btn = st.form_submit_button("Permanently Delete Budget Head")

                        if delete_btn:
                            if not confirm_check:
                                st.error("Please check the confirmation box to proceed with deletion.")
                            else:
                                # 1. Delete associated expenditures and file attachments
                                exps = db.query(Expenditure).filter(Expenditure.budget_head_id == target_del_head.id).all()
                                for exp in exps:
                                    if exp.invoice_path and os.path.exists(exp.invoice_path):
                                        try:
                                            os.remove(exp.invoice_path)
                                        except Exception:
                                            pass
                                    db.delete(exp)

                                # 2. Delete associated fund releases
                                rels = db.query(FundRelease).filter(FundRelease.budget_head_id == target_del_head.id).all()
                                for rel in rels:
                                    db.delete(rel)

                                # 3. Clear section links
                                target_del_head.sections = []

                                # 4. Delete budget head entity
                                del_code = target_del_head.code
                                db.delete(target_del_head)
                                db.commit()

                                st.success(f"Budget Head '{del_code}' and all associated records deleted!")
                                st.rerun()
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

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Fund Allocation Form")
        selected_sec_name = st.selectbox("Select Section", list(sec_map.keys()))
        selected_sec_id = sec_map[selected_sec_name]

        # Filter budget heads assigned to this section or unassigned
        sec_obj = db.query(Section).filter(Section.id == selected_sec_id).first()
        available_heads = [
            h for h in budget_heads 
            if not h.sections or any(s.id == selected_sec_id for s in h.sections)
        ]

        if not available_heads:
            st.warning(f"No budget heads are currently assigned to {selected_sec_name}.")
            return

        head_map = {f"{h.code} - {h.description}": h.id for h in available_heads}

        with st.form("release_fund_form", clear_on_submit=True):
            selected_head_label = st.selectbox(
                "Select Budget Head", list(head_map.keys())
            )
            amount = st.number_input("Release Amount (PKR)", min_value=1.0, step=1000.0)
            release_date = st.date_input("Release Date")

            submit = st.form_submit_button("Release Funds")

            if submit:
                head_id = head_map[selected_head_label]

                new_release = FundRelease(
                    section_id=selected_sec_id,
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