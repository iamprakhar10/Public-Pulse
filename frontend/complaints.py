"""
Complaint conversation UI for Public Pulse.

This module allows an authenticated user to:

- start a complaint,
- see the user/assistant conversation,
- answer clarification questions,
- continue until the backend marks the complaint complete.
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    send_complaint_message,
    start_complaint,
)


def initialize_complaint_session() -> None:
    """
    Initialize frontend state for the current complaint.

    current_complaint stores the complete complaint dictionary
    returned by FastAPI.
    """

    if "current_complaint" not in st.session_state:
        st.session_state.current_complaint = None


def display_conversation(
        complaint: dict,
) -> None:
    """
    Display all saved complaint messages as a chat conversation.

    The backend returns messages containing:

    {
        "role": "user" | "assistant",
        "content": "..."
    }
    """

    messages = complaint.get(
        "messages",
        [],
    )

    for message in messages:
        role = message["role"]
        content = message["content"]

        with st.chat_message(role):
            st.write(content)


def show_start_complaint() -> None:
    """
    Show the UI used to create the first complaint message.
    """

    st.subheader(
        "Report a problem"
    )

    st.write(
        "Describe the civic problem in your own words. "
        "Public Pulse will ask for any missing details."
    )

    first_message = st.chat_input(
        "Describe the problem..."
    )

    if not first_message:
        return

    access_token = (
        st.session_state.access_token
    )

    try:
        with st.spinner(
            "Understanding your complaint..."
        ):
            complaint = start_complaint(
                access_token=access_token,
                message=first_message,
            )

    except APIClientError as exc:
        st.error(
            str(exc),
        )
        return

    st.session_state.current_complaint = complaint

    st.rerun()


def show_active_complaint(
        complaint: dict,
) -> None:
    """
    Show an existing complaint conversation.

    While status is 'draft', the user can continue answering
    the assistant's clarification questions.

    Once the backend moves the complaint to awaiting_approval,
    conversation input is stopped.
    """

    complaint_id = complaint["id"]
    complaint_status = complaint["status"]

    st.subheader(
        f"Complaint #{complaint_id}"
    )

    display_conversation(
        complaint,
    )

    # -----------------------------------------------------
    # Complaint is still being collected
    # -----------------------------------------------------

    if complaint_status == "draft":

        user_message = st.chat_input(
            "Reply with the missing details..."
        )

        if not user_message:
            return

        access_token = (
            st.session_state.access_token
        )

        try:
            with st.spinner(
                "Updating your complaint..."
            ):
                updated_complaint = (
                    send_complaint_message(
                        access_token=access_token,
                        complaint_id=complaint_id,
                        content=user_message,
                    )
                )

        except APIClientError as exc:
            st.error(
                str(exc),
            )
            return

        st.session_state.current_complaint = (
            updated_complaint
        )

        st.rerun()

        return

    # -----------------------------------------------------
    # Complaint is complete
    # -----------------------------------------------------

    if complaint_status == "awaiting_approval":
        st.success(
            "The complaint details are complete."
        )

        st.write(
            "Next we will generate and review the email draft "
            "before sending anything."
        )

        return

    st.info(
        f"Complaint status: {complaint_status}"
    )


def show_complaint_section() -> None:
    """
    Main complaint UI controller.

    Decides whether to show:
    - the start screen, or
    - the active complaint conversation.
    """

    initialize_complaint_session()

    complaint = (
        st.session_state.current_complaint
    )

    if complaint is None:
        show_start_complaint()
        return

    show_active_complaint(
        complaint,
    )