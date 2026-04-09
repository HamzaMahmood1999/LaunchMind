"""
Slack Integration — LaunchMind

Handles posting messages to Slack channels using the Slack Web API.
Messages are formatted using Slack Block Kit for rich presentation.

Uses the SLACK_BOT_TOKEN environment variable for authentication.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


class SlackIntegration:
    """Posts messages to Slack channels via the Web API."""

    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.channel = os.getenv("SLACK_CHANNEL", "#launches")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def post_message(self, text: str, blocks: list = None) -> dict:
        """
        Post a message to the configured Slack channel.

        Args:
            text: Fallback plain-text message.
            blocks: Optional Slack Block Kit blocks for rich formatting.

        Returns:
            Slack API response as dict.
        """
        payload = {"channel": self.channel, "text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            resp = requests.post(
                f"{SLACK_API_BASE}/chat.postMessage",
                headers=self.headers,
                json=payload,
            )
            data = resp.json()
            if data.get("ok"):
                logger.info(f"Posted message to {self.channel}")
            else:
                logger.error(f"Slack API error: {data.get('error')}")
            return data
        except Exception as e:
            logger.error(f"Failed to post to Slack: {e}")
            return {"ok": False, "error": str(e)}

    def build_launch_blocks(
        self,
        product_name: str,
        tagline: str,
        description: str,
        pr_url: str = None,
    ) -> list:
        """
        Build Slack Block Kit blocks for a product launch announcement.

        Returns:
            List of Block Kit block dicts.
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"New Launch: {product_name}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{tagline}*\n\n{description}",
                },
            },
            {"type": "divider"},
        ]
        if pr_url:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
                        {"type": "mrkdwn", "text": "*Status:* Ready for review"},
                    ],
                }
            )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Posted by LaunchMind AI"}
                ],
            }
        )
        return blocks
