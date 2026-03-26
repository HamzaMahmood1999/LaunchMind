"""
Email Integration — LaunchMind

Handles sending outreach emails via the SendGrid API.
Email subject and body are expected to be LLM-generated.

Uses the SENDGRID_API_KEY environment variable for authentication.
"""

import logging
import os

logger = logging.getLogger(__name__)


class EmailIntegration:
    """Sends emails via SendGrid API."""

    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL")
        self.default_recipient = os.getenv("EMAIL_RECIPIENT")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_plain: str = None,
    ) -> dict:
        """
        Send an email via SendGrid.

        Args:
            to_email: Recipient email address.
            subject: Email subject line (LLM-generated).
            body_html: HTML email body (LLM-generated).
            body_plain: Optional plain-text fallback.

        Returns:
            SendGrid API response info.
        """
        # TODO: Use sendgrid.SendGridAPIClient to send mail
        raise NotImplementedError
