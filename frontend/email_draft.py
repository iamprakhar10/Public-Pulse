"""
Email draft review UI for Public Pulse.

This module allows the user to:

- generate a complaint email draft,
- review it,
- edit it,
- approve it,
- send it through Gmail.
"""

import streamlit as st

from frontend.api_client import (
    APIClientError,
    approve_email_draft,
    generate_email_draft,
    send_complaint_email,
    update_email_draft,
)


def show_generate_draft_button(
        complaint: dict,
) -> None:
    """
    Show the button that generates the initial email draft.

    This is used when the complaint is complete but no draft
    has been generated yet.
    """

    complaint_id = complaint["id"]

    st.subheader(
        "Prepare complaint email"
    )

    st.write(
        "The complaint details are complete. "
        "Generate the email before reviewing it."
    )

    if not st.button(
        "Generate email draft",
    ):
        return

    try:
        with st.spinner(
            "Generating email draft..."
        ):
            updated_complaint = generate_email_draft(
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

    st.session_state.current_complaint = (
        updated_complaint
    )

    st.rerun()


def show_draft_editor(
        complaint: dict,
) -> None:
    """
    Display the generated draft and allow the user to edit it.
    """

    complaint_id = complaint["id"]

    email_subject = (
        complaint.get("email_subject") or ""
    )

    email_body = (
        complaint.get("email_body") or ""
    )

    st.subheader(
        "Review email draft"
    )

    st.write(
        "Review the email carefully before approving it."
    )

    with st.form(
        "email_draft_form",
    ):
        edited_subject = st.text_input(
            "Subject",
            value=email_subject,
        )

        edited_body = st.text_area(
            "Email body",
            value=email_body,
            height=350,
        )

        save_clicked = st.form_submit_button(
            "Save changes",
        )

    if save_clicked:

        if not edited_subject.strip():
            st.error(
                "Email subject cannot be empty."
            )
            return

        if not edited_body.strip():
            st.error(
                "Email body cannot be empty."
            )
            return

        try:
            updated_complaint = update_email_draft(
                access_token=(
                    st.session_state.access_token
                ),
                complaint_id=complaint_id,
                subject=edited_subject,
                body=edited_body,
            )

        except APIClientError as exc:
            st.error(
                str(exc),
            )
            return

        st.session_state.current_complaint = (
            updated_complaint
        )

        st.success(
            "Email draft updated."
        )

        st.rerun()

    st.divider()

    if st.button(
        "Approve email",
    ):
        try:
            approved_complaint = (
                approve_email_draft(
                    access_token=(
                        st.session_state.access_token
                    ),
                    complaint_id=complaint_id,
                )
            )

        except APIClientError as exc:
            st.error(
                str(exc),
            )
            return

        st.session_state.current_complaint = (
            approved_complaint
        )

        st.rerun()


def show_approved_email(
        complaint: dict,
) -> None:
    """
    Display an approved complaint and allow the user to send it.
    """

    complaint_id = complaint["id"]

    st.subheader(
        "Approved email"
    )

    st.success(
        "The complaint email has been approved."
    )

    st.write(
        "**Subject:**"
    )

    st.write(
        complaint.get("email_subject", "")
    )

    st.write(
        "**Body:**"
    )

    st.text(
        complaint.get("email_body", "")
    )

    st.warning(
        "Sending will email the matched authority "
        "using your connected Gmail account."
    )

    if not st.button(
        "Send complaint email",
    ):
        return

    try:
        with st.spinner(
            "Sending complaint..."
        ):
            sent_complaint = send_complaint_email(
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

    st.session_state.current_complaint = (
        sent_complaint
    )

    st.rerun()


def show_sent_email(
        complaint: dict,
) -> None:
    """
    Show the final state after the complaint email has been sent.
    """

    st.success(
        "Complaint email sent successfully."
    )

    st.write(
        f"Complaint #{complaint['id']} has been sent."
    )


def show_email_draft_section(
        complaint: dict,
) -> None:
    """
    Main controller for the complaint email workflow.

    The UI shown depends on the current complaint state.
    """

    status = complaint["status"]

    email_subject = complaint.get(
        "email_subject"
    )

    email_body = complaint.get(
        "email_body"
    )

    # Complaint is complete but no draft exists yet.
    if (
        status == "awaiting_approval"
        and (
            not email_subject
            or not email_body
        )
    ):
        show_generate_draft_button(
            complaint,
        )
        return

    # Draft exists and is waiting for approval.
    if status == "awaiting_approval":
        show_draft_editor(
            complaint,
        )
        return

    # Approved but not sent.
    if status == "approved":
        show_approved_email(
            complaint,
        )
        return

    # Email already sent.
    if status == "sent":
        show_sent_email(
            complaint,
        )