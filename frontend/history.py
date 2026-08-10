"""
Complaint history UI for Public Pulse.

This module allows the authenticated user to:

- view previous complaints,
- open a previous complaint,
- start a new complaint.
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    get_complaint,
    get_my_complaints,
)


def start_new_complaint() -> None:
    """
    Clear the currently selected complaint.

    This does not delete anything from PostgreSQL.

    It only tells the frontend that no complaint is currently
    selected, so the complaint chat can start fresh.
    """

    st.session_state.current_complaint = None

    st.rerun()


def open_complaint(
        *,
        complaint_id: int,
) -> None:
    """
    Load one complaint from FastAPI and make it the active complaint.

    The individual complaint endpoint returns the full conversation,
    unlike the complaint history list which is mainly for summaries.
    """

    try:
        complaint = get_complaint(
            access_token=(
                st.session_state.access_token
            ),
            complaint_id=complaint_id,
        )

    except APIClientError as exc:
        st.error(
            str(exc),
        )
        return

    st.session_state.current_complaint = complaint

    st.rerun()


def show_start_new_complaint_button() -> None:
    """
    Display the button used to begin a fresh complaint.
    """

    if st.button(
        "Start new complaint",
        type="primary",
    ):
        start_new_complaint()


def show_complaint_history() -> None:
    """
    Display all complaints belonging to the authenticated user.

    Each complaint can be opened.

    Opening it loads the complete complaint from the backend and
    places it into st.session_state.current_complaint.
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

        with st.expander(
            f"Complaint #{complaint_id} — {status}"
        ):

            if summary:
                st.write(
                    f"**Summary:** {summary}"
                )

            category = complaint.get(
                "category"
            )

            if category:
                st.write(
                    f"**Category:** {category}"
                )

            city = complaint.get(
                "city"
            )

            if city:
                st.write(
                    f"**City:** {city}"
                )

            area = complaint.get(
                "area"
            )

            if area:
                st.write(
                    f"**Area:** {area}"
                )

            pincode = complaint.get(
                "pincode"
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

            # Unique key is required because there is one Open
            # button for every complaint.
            if st.button(
                "Open complaint",
                key=f"open_complaint_{complaint_id}",
            ):
                open_complaint(
                    complaint_id=complaint_id,
                )