import importlib
import secretary_views
import reports_views
from secretary_views import render_secretary_dashboard
from reports_views import render_reports
from admin_views import render_section_management, render_user_management
from auth import authenticate_user, create_initial_admin, create_initial_secretary
from dashboard_views import render_dashboard
from database import SessionLocal
from expenditure_views import render_expenditure_entry
from finance_views import render_budget_heads_management, render_fund_release
import streamlit as st
from models import init_db

importlib.reload(secretary_views)
importlib.reload(reports_views)

st.set_page_config(
    page_title="NH&CD Finance Portal", page_icon="💰", layout="wide"
)

init_db()
db = SessionLocal()
create_initial_admin(db)
create_initial_secretary(db)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None


def login_screen():
    st.title("🏛️ NH&CD Finance Management Portal")
    st.subheader("Login to your account")

    col1, _ = st.columns([1, 2])
    with col1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                user = authenticate_user(db, username, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user.username
                    st.session_state["role"] = user.role
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")


def main_portal():
    col_sb_title, col_sb_ref = st.sidebar.columns([4, 1])
    with col_sb_title:
        st.title(f"Welcome, {st.session_state['username']}")
    with col_sb_ref:
        if st.button("", icon=":material/refresh:", help="Refresh Portal Data", key="top_left_refresh"):
            st.rerun()

    st.sidebar.caption(f"Role: {st.session_state['role']}")

    if st.session_state["role"] == "Finance":
        menu = [
            "Dashboard",
            "Fund Release",
            "Expenditure Entry",
            "Reports",
            "Users & Sections",
            "Budget Heads",
            "Settings",
        ]
    elif st.session_state["role"] == "Secretary":
        menu = ["Executive Dashboard", "Reports"]
    else:
        menu = ["Dashboard", "Expenditure Entry", "Reports"]

    choice = st.sidebar.radio("Navigation", menu)

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.rerun()

    # --- ROUTING ---
    if choice in ("Dashboard", "Executive Dashboard"):
        if st.session_state["role"] == "Secretary":
            render_secretary_dashboard(db)
        else:
            render_dashboard(db)

    elif choice == "Fund Release":
        st.title("💸 Fund Release Module")
        render_fund_release(db)

    elif choice == "Expenditure Entry":
        render_expenditure_entry(db)

    elif choice == "Reports":
        render_reports(db)

    elif choice == "Users & Sections":
        st.title("⚙️ User & Section Management")
        tab1, tab2 = st.tabs(["🏢 Sections", "👥 Users"])
        with tab1:
            render_section_management(db)
        with tab2:
            render_user_management(db)

    elif choice == "Budget Heads":
        st.title("📋 Budget Head Setup")
        render_budget_heads_management(db)

    elif choice == "Settings":
        st.title("⚙️ System Settings")


if not st.session_state["authenticated"]:
    login_screen()
else:
    main_portal()