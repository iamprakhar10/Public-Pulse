"""
Authentication UI for public pulse

Contains:
- Login 
- Registration
"""


"""
Authentication UI for Public Pulse.

Contains:
- Login form
- Registration form
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    login_user,
    register_user,
)


def show_login_form() -> None:
    """
    Render the login form.

    On successful login, save the JWT in Streamlit session state.
    """

    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input(
            "Email",
            key="login_email",
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        submitted = st.form_submit_button(
            "Login",
        )

    if not submitted:
        return

    if not email or not password:
        st.error(
            "Email and password are required."
        )
        return

    try:
        token_response = login_user(
            email=email,
            password=password,
        )

    except APIClientError as exc:
        st.error(str(exc))
        return

    st.session_state.access_token = (
        token_response["access_token"]
    )

    st.session_state.logged_in = True

    st.rerun()


def show_registration_form() -> None:
    """
    Render the registration form.
    """

    st.subheader("Create account")

    with st.form("registration_form"):
        name = st.text_input(
            "Name",
            key="register_name",
        )

        email = st.text_input(
            "Email",
            key="register_email",
        )

        phone = st.text_input(
            "Phone",
            key="register_phone",
        )

        password = st.text_input(
            "Password",
            type="password",
            key="register_password",
        )

        submitted = st.form_submit_button(
            "Register",
        )

    if not submitted:
        return

    if (
        not name
        or not email
        or not phone
        or not password
    ):
        st.error(
            "All fields are required."
        )
        return

    try:
        register_user(
            name=name,
            email=email,
            phone=phone,
            password=password,
        )

    except APIClientError as exc:
        st.error(str(exc))
        return

    st.success(
        "Account created successfully. You can now log in."
    )


def show_auth_page() -> None:
    """
    Show login and registration tabs.
    """

    st.title("Public Pulse")

    st.write(
        "Report civic problems and send complaints "
        "to the appropriate authorities."
    )

    login_tab, register_tab = st.tabs(
        [
            "Login",
            "Register",
        ]
    )

    with login_tab:
        show_login_form()

    with register_tab:
        show_registration_form()