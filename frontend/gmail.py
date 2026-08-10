"""
Gmail connection UI for Public Pulse.

This module allows the logged-in user to:

- see Gmail connection status,
- connect Gmail,
- disconnect Gmail.
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    disconnect_gmail,
    get_gmail_connect_url,
    get_gmail_status,
)


def show_gmail_section() -> None:
    """
    Display Gmail connection controls for the authenticated user.
    """

    st.subheader(
        "Gmail"
    )

    access_token = (
        st.session_state.access_token
    )

    try:
        gmail_status = get_gmail_status(
            access_token=access_token,
        )

    except APIClientError as exc:
        st.error(
            str(exc),
        )

        return

    connected = gmail_status["connected"]

    # -----------------------------------------------------
    # Gmail is already connected
    # -----------------------------------------------------

    if connected:
        google_email = gmail_status.get(
            "google_email"
        )

        st.success(
            f"Gmail connected: {google_email}"
        )

        if st.button(
            "Disconnect Gmail",
        ):
            try:
                disconnect_gmail(
                    access_token=access_token,
                )

            except APIClientError as exc:
                st.error(
                    str(exc),
                )

                return

            st.success(
                "Gmail disconnected successfully."
            )

            # Run Streamlit again so that the Gmail status
            # changes from connected → disconnected.
            st.rerun()

        return

    # -----------------------------------------------------
    # Gmail is not connected
    # -----------------------------------------------------

    st.warning(
        "Gmail is not connected."
    )

    try:
        google_authorization_url = (
            get_gmail_connect_url(
                access_token=access_token,
            )
        )

    except APIClientError as exc:
        st.error(
            str(exc),
        )

        return

    st.link_button(
        "Connect Gmail",
        google_authorization_url,
    )