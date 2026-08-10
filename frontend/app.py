"""
Main Streamlit entrypoint for Public Pulse.
"""

import streamlit as st

from frontend.auth import show_auth_page
from frontend.gmail import show_gmail_section


def initialize_session_state() -> None:
    """
    Initialize values that should survive Streamlit reruns.
    """

    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False


def logout() -> None:
    """
    Remove authentication information from the Streamlit session.
    """

    st.session_state.access_token = None
    st.session_state.logged_in = False

    st.rerun()


def show_authenticated_page() -> None:
    """
    Show the current authenticated Public Pulse interface.

    At this stage it contains:

    - Gmail connection management
    - logout

    Complaint creation will be added next.
    """

    st.title(
        "Public Pulse"
    )

    st.success(
        "You are logged in."
    )

    st.divider()

    show_gmail_section()

    st.divider()

    st.write(
        "Complaint creation will be added next."
    )

    st.divider()

    if st.button(
        "Logout",
    ):
        logout()


def main() -> None:
    """
    Main Streamlit application entrypoint.
    """

    st.set_page_config(
        page_title="Public Pulse",
        page_icon="📢",
        layout="centered",
    )

    initialize_session_state()

    if st.session_state.logged_in:
        show_authenticated_page()

    else:
        show_auth_page()


if __name__ == "__main__":
    main()