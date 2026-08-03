"""
Low level email delivery service.

This module is intentionally separate from complaint workflow logic

Later, the implementation can use Gmail OAuth, SMTP,
or another provider
"""

from typing import Protocol

class EmailSender(Protocol):
    """
    Interface implemented by any email provider.

    Keeping an interface allows tests to use a fake 
    sender without generating real emails
    """

    def send_email(
            self, 
            *,
            recipient: str,
            subject: str,
            body: str,
    ) -> None:
        """
        Sends one plain text email.
        """
        ...



class ConsoleEmailSender:
    """
    This is temporary

    this prints the email instead of contacting a real provider
    """

    def send_email(
            self,
            *,
            recipient: str,
            subject: str,
            body:str,
    ) -> None:
        print("\n--- EMAIL DELIVERY PREVIEW ---")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print()
        print(body)
        print("--- END EMAIL ---\n")