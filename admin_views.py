from auth import hash_password
import pandas as pd
import streamlit as st
from models import Section, User


def render_section_management(db):
    st.subheader("🏢 Section Management")

    col1, col2 = st.columns([1, 2])

    # Form to add a new section
    with col1:
        st.markdown("##### Add New Section")
        with st.form("add_section_form", clear_on_submit=True):
            section_name = st.text_input("Section Name")
            submit = st.form_submit_button("Add Section")

            if submit:
                if section_name.strip():
                    existing = (
                        db.query(Section)
                        .filter(Section.name == section_name.strip())
                        .first()
                    )
                    if existing:
                        st.error("Section already exists!")
                    else:
                        new_sec = Section(name=section_name.strip())
                        db.add(new_sec)
                        db.commit()
                        st.success(f"Section '{section_name}' added!")
                        st.rerun()
                else:
                    st.warning("Please enter a section name.")

    # View existing sections
    with col2:
        st.markdown("##### Existing Sections")
        sections = db.query(Section).all()
        if sections:
            df = pd.DataFrame(
                [{"ID": s.id, "Section Name": s.name} for s in sections]
            )
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sections added yet.")


def render_user_management(db):
    st.subheader("👥 User Management")

    col1, col2 = st.columns([1, 2])

    sections = db.query(Section).all()
    section_dict = {s.name: s.id for s in sections}

    # Form to create a new user
    with col1:
        st.markdown("##### Create New User")
        with st.form("add_user_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox(
                "Role", ["Finance", "Section"]
            )  # Finance = Admin, Section = User

            # Only assign section if role is "Section"
            sec_choice = None
            if role == "Section":
                sec_choice = st.selectbox(
                    "Assign to Section", list(section_dict.keys())
                )

            submit = st.form_submit_button("Create User")

            if submit:
                if not username or not password:
                    st.warning("Username and password are required.")
                else:
                    existing = (
                        db.query(User).filter(User.username == username).first()
                    )
                    if existing:
                        st.error("Username already taken!")
                    else:
                        sec_id = (
                            section_dict.get(sec_choice)
                            if role == "Section"
                            else None
                        )
                        hashed_pwd = hash_password(password)

                        new_user = User(
                            username=username,
                            password=hashed_pwd,
                            role=role,
                            section_id=sec_id,
                        )
                        db.add(new_user)
                        db.commit()
                        st.success(f"User '{username}' created successfully!")
                        st.rerun()

    # Table displaying all registered users
    with col2:
        st.markdown("##### System Users")
        users = db.query(User).all()
        if users:
            user_data = []
            for u in users:
                sec_name = u.section.name if u.section else "N/A (Finance)"
                user_data.append(
                    {
                        "ID": u.id,
                        "Username": u.username,
                        "Role": u.role,
                        "Section": sec_name,
                    }
                )
            df_users = pd.DataFrame(user_data)
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("No users found.")