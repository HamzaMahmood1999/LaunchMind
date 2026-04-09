"""
Email Integration — LaunchMind

Handles sending outreach emails via the SendGrid API.
Email subject and body are expected to be LLM-generated.

Uses the SENDGRID_API_KEY environment variable for authentication.
"""

import logging
import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=body_html,
            )
            if body_plain:
                message.plain_text_content = body_plain

            client = SendGridAPIClient(self.api_key)
            response = client.send(message)
            logger.info(f"Email sent to {to_email} (status={response.status_code})")
            return {
                "status_code": response.status_code,
                "success": response.status_code in (200, 201, 202),
            }
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"error": str(e), "success": False}
