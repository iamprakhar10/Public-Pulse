"""
Complaint history UI for Public Pulse.

This module allows the authenticated user to:

- view previous complaints,
- inspect their statuses,
- start a new complaint.
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    get_my_complaints,
)


def start_new_complaint() -> None:
    """
    Clear the complaint currently stored in Streamlit session state.

    The next rerun will show the fresh complaint input again.
    """

    st.session_state.current_complaint = None

    st.rerun()


def show_start_new_complaint_button() -> None:
    """
    Display a button for beginning another complaint.
    """

    if st.button(
        "Start new complaint",
        type="primary",
    ):
        start_new_complaint()


def show_complaint_history() -> None:
    """
    Load and display all complaints belonging to the logged-in user.
    """

    st.subheader(
        "My Complaints"
    )

    try:
        complaints = get_my_complaints(
            access_token=(
                st.session_state.access_token
            ),
        )

    except APIClientError as exc:
        st.error(
            str(exc),
        )
        return

    if not complaints:
        st.info(
            "You have not created any complaints yet."
        )
        return

    for complaint in complaints:

        complaint_id = complaint["id"]

        status = complaint.get(
            "status",
            "unknown",
        )

        summary = complaint.get(
            "summary"
        )

        category = complaint.get(
            "category"
        )

        with st.expander(
            f"Complaint #{complaint_id} — {status}"
        ):

            if summary:
                st.write(
                    f"**Summary:** {summary}"
                )

            if category:
                st.write(
                    f"**Category:** {category}"
                )

            city = complaint.get(
                "city"
            )

            area = complaint.get(
                "area"
            )

            pincode = complaint.get(
                "pincode"
            )

            if city:
                st.write(
                    f"**City:** {city}"
                )

            if area:
                st.write(
                    f"**Area:** {area}"
                )

            if pincode:
                st.write(
                    f"**Pincode:** {pincode}"
                )

            email_subject = complaint.get(
                "email_subject"
            )

            if email_subject:
                st.write(
                    f"**Email subject:** {email_subject}"
                )