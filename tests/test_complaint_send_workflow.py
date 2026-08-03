from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.constants.complaint import ComplaintStatus
from app.services.complaint_send_workflow import (
    send_approved_complaint_email,
)


class FakeEmailSender:
    """
    Test sender that records the email instead of delivering it.
    """

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []

    def send_email(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.sent_emails.append(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
            }
        )


class FailingEmailSender:
    """
    Simulates an email provider failure.
    """

    def send_email(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        raise RuntimeError("Email provider is unavailable.")


def build_approved_complaint():
    """
    Build a lightweight complaint-like object for unit tests.

    A real database row is unnecessary because this test focuses only
    on complaint sending business logic.
    """

    return SimpleNamespace(
        id=101,
        status=ComplaintStatus.APPROVED,
        authority=SimpleNamespace(
            email="road.jabalpur@example.com",
        ),
        email_subject="Request for road repair",
        email_body=(
            "Dear Sir/Madam,\n\n"
            "Please repair the damaged road in Vijay Nagar, "
            "Jabalpur.\n\n"
            "Sincerely,\nTest User"
        ),
    )


def test_approved_complaint_email_is_sent(
    monkeypatch,
) -> None:
    """
    An approved complaint with complete email data should be sent.

    The status must change to SENT only after delivery succeeds.
    """

    db = MagicMock()
    complaint = build_approved_complaint()
    sender = FakeEmailSender()

    monkeypatch.setattr(
        "app.services.complaint_send_workflow.get_user_complaint",
        lambda db, complaint_id, user_id: complaint,
    )

    result = send_approved_complaint_email(
        db=db,
        complaint_id=complaint.id,
        user_id=5,
        email_sender=sender,
    )

    assert len(sender.sent_emails) == 1

    sent_email = sender.sent_emails[0]

    assert sent_email["recipient"] == (
        "road.jabalpur@example.com"
    )
    assert sent_email["subject"] == (
        "Request for road repair"
    )
    assert sent_email["body"] == complaint.email_body

    assert result is complaint
    assert complaint.status == ComplaintStatus.SENT

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(complaint)


def test_unapproved_complaint_cannot_be_sent(
    monkeypatch,
) -> None:
    """
    A complaint awaiting approval must not be sent.
    """

    db = MagicMock()
    complaint = build_approved_complaint()
    complaint.status = ComplaintStatus.AWAITING_APPROVAL

    sender = FakeEmailSender()

    monkeypatch.setattr(
        "app.services.complaint_send_workflow.get_user_complaint",
        lambda db, complaint_id, user_id: complaint,
    )

    with pytest.raises(
        ValueError,
        match=(
            "The complaint email must be approved "
            "before it can be sent"
        ),
    ):
        send_approved_complaint_email(
            db=db,
            complaint_id=complaint.id,
            user_id=5,
            email_sender=sender,
        )

    assert sender.sent_emails == []
    assert complaint.status == ComplaintStatus.AWAITING_APPROVAL

    db.commit.assert_not_called()


def test_complaint_without_authority_cannot_be_sent(
    monkeypatch,
) -> None:
    """
    An approved complaint still requires an assigned authority.
    """

    db = MagicMock()
    complaint = build_approved_complaint()
    complaint.authority = None

    sender = FakeEmailSender()

    monkeypatch.setattr(
        "app.services.complaint_send_workflow.get_user_complaint",
        lambda db, complaint_id, user_id: complaint,
    )

    with pytest.raises(
        ValueError,
        match="No authority is assigned",
    ):
        send_approved_complaint_email(
            db=db,
            complaint_id=complaint.id,
            user_id=5,
            email_sender=sender,
        )

    assert sender.sent_emails == []
    assert complaint.status == ComplaintStatus.APPROVED

    db.commit.assert_not_called()


def test_provider_failure_keeps_complaint_approved(
    monkeypatch,
) -> None:
    """
    If delivery fails, the complaint must not be marked as SENT.
    """

    db = MagicMock()
    complaint = build_approved_complaint()
    sender = FailingEmailSender()

    monkeypatch.setattr(
        "app.services.complaint_send_workflow.get_user_complaint",
        lambda db, complaint_id, user_id: complaint,
    )

    with pytest.raises(
        RuntimeError,
        match="Email provider is unavailable",
    ):
        send_approved_complaint_email(
            db=db,
            complaint_id=complaint.id,
            user_id=5,
            email_sender=sender,
        )

    # Delivery failed, so the status must remain APPROVED.
    assert complaint.status == ComplaintStatus.APPROVED

    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_missing_complaint_cannot_be_sent(
    monkeypatch,
) -> None:
    """
    A missing or non-owned complaint should be rejected.
    """

    db = MagicMock()
    sender = FakeEmailSender()

    monkeypatch.setattr(
        "app.services.complaint_send_workflow.get_user_complaint",
        lambda db, complaint_id, user_id: None,
    )

    with pytest.raises(
        ValueError,
        match="Complaint not found",
    ):
        send_approved_complaint_email(
            db=db,
            complaint_id=999,
            user_id=5,
            email_sender=sender,
        )

    assert sender.sent_emails == []
    db.commit.assert_not_called()