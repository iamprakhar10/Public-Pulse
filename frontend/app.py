"""
Main Streamlit entrypoint for Public Pulse.
"""

import streamlit as st

from frontend.auth import show_auth_page
from frontend.complaints import show_complaint_section
from frontend.dashboard import show_dashboard
from frontend.gmail import show_gmail_section
from frontend.history import (
    show_complaint_history,
    show_start_new_complaint_button,
)


def initialize_session_state() -> None:
    """
    Initialize values that should survive Streamlit reruns.
    """

    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "current_complaint" not in st.session_state:
        st.session_state.current_complaint = None


def logout() -> None:
    """
    Clear the authenticated frontend session.
    """

    st.session_state.access_token = None
    st.session_state.logged_in = False
    st.session_state.current_complaint = None

    st.rerun()


def show_authenticated_app() -> None:
    """
    Show sidebar navigation for authenticated users.
    """

    st.sidebar.title(
        "Public Pulse"
    )

    page = st.sidebar.radio(
        "Navigation",
        [
            "Complaint",
            "My Complaints",
            "Dashboard",
            "Gmail",
        ],
    )

    st.sidebar.divider()

    if st.sidebar.button(
        "Logout",
    ):
        logout()

    if page == "Complaint":
        st.title(
            "Report a Problem"
        )

        show_start_new_complaint_button()

        st.divider()

        show_complaint_section()

    elif page == "My Complaints":
        st.title(
            "My Complaints"
        )

        show_complaint_history()

        st.divider()

        # Selected complaint appears underneath history.
        if st.session_state.current_complaint is not None:
            show_complaint_section()

    elif page == "Dashboard":
        show_dashboard()

    elif page == "Gmail":
        st.title(
            "Gmail Connection"
        )

        show_gmail_section()


def main() -> None:
    """
    Main Streamlit application entrypoint.
    """

    st.set_page_config(
        page_title="Public Pulse",
        page_icon="📢",
        layout="wide",
    )

    initialize_session_state()

    if st.session_state.logged_in:
        show_authenticated_app()

    else:
        show_auth_page()


if __name__ == "__main__":
    main()