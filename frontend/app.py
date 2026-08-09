"""
Public pulse streamlit frontend

Current frontend milestone:
- Register a new user
- Login
- Store JWT access token in Streamlit session
- Show authenticated page
- Logout

Later we will add
- Gmail connect/disconnect
- Complaint conversation
- Email draft approval
- Complaint sending
- Dashboard
"""

"""
Main Streamlit entrypoint for Public Pulse.
"""

import streamlit as st

from frontend.auth import show_auth_page


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
    Temporary page shown after login.

    We will replace this with the real Public Pulse interface
    in the next milestones.
    """

    st.title("Public Pulse")

    st.success(
        "You are logged in."
    )

    st.write(
        "Complaint creation will be added next."
    )

    if st.button("Logout"):
        logout()


def main() -> None:
    """
    Main frontend entrypoint.
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