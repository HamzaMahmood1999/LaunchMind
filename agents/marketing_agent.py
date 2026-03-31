"""
Marketing Agent — LaunchMind

Responsibilities:
    - Generate LLM-powered marketing copy:
        * Tagline
        * Product description
        * Cold outreach email (subject + body)
        * Social media posts
    - Send a real cold email via SendGrid API.
    - Post a formatted message to Slack using Block Kit.
"""

import json
import logging

from core.llm import call_llm
from core.message_bus import MessageBus
from integrations.email_integration import EmailIntegration
from integrations.slack_integration import SlackIntegration

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior marketing strategist. Given a product specification, generate marketing materials.

You MUST return valid JSON with these exact keys:
- tagline: string (under 10 words, punchy and memorable)
- description: string (2-3 sentences for a landing page)
- email_subject: string (compelling cold outreach email subject)
- email_body_html: string (HTML formatted cold outreach email body with greeting, value pitch, and call to action)
- social_posts: object with keys:
    - twitter: string (under 280 characters, include hashtags)
    - linkedin: string (professional tone, 2-3 sentences)
    - instagram: string (casual tone with emojis)

Return ONLY the JSON object, no markdown fences or extra text."""


class MarketingAgent:
    """Generates marketing materials and handles outreach."""

    def __init__(self, message_bus: MessageBus):
        self.name = "marketing"
        self.message_bus = message_bus
        self.slack = SlackIntegration()
        self.email = EmailIntegration()

    def run(self) -> None:
        """
        Execute the Marketing agent's workflow.

        Generates copy, sends email, and posts to Slack.
        """
        messages = self.message_bus.receive(self.name)
        if not messages:
            logger.warning("Marketing agent: no messages to process.")
            return

        msg = messages[-1]
        logger.info(f"Marketing agent received {msg.message_type.value} from {msg.from_agent}")

        spec = msg.payload.get("spec", msg.payload)
        pr_url = msg.payload.get("pr_url", "")

        # Build prompt based on message type
        if msg.message_type.value == "revision_request":
            feedback = msg.payload.get("feedback", {})
            issues = feedback.get("issues", []) if isinstance(feedback, dict) else [str(feedback)]
            user_prompt = (
                f"The previous marketing copy was rejected by QA. Issues found:\n"
                + "\n".join(f"- {i}" for i in issues)
                + f"\n\nProduct spec: {json.dumps(spec, indent=2)}\n\n"
                "Please generate improved marketing materials addressing all issues."
            )
        else:
            instructions = msg.payload.get("instructions", "")
            user_prompt = (
                f"Product specification:\n{json.dumps(spec, indent=2)}\n\n"
                f"Additional instructions: {instructions}\n"
                f"GitHub PR URL for reference: {pr_url}"
            )

        # Generate marketing copy
        try:
            copy = call_llm(SYSTEM_PROMPT, user_prompt, json_mode=True)
            logger.info(f"Marketing agent generated copy. Tagline: {copy.get('tagline', '')}")
        except Exception as e:
            logger.error(f"Marketing agent LLM call failed: {e}")
            error_msg = self.message_bus.create_message(
                from_agent=self.name,
                to_agent="ceo",
                message_type="result",
                payload={"error": str(e)},
                parent_message_id=msg.message_id,
            )
            self.message_bus.send(error_msg)
            return

        # Send cold outreach email via SendGrid
        try:
            recipient = self.email.default_recipient or "test@example.com"
            email_result = self.email.send_email(
                to_email=recipient,
                subject=copy.get("email_subject", "Check out our new product!"),
                body_html=copy.get("email_body_html", "<p>Hello!</p>"),
            )
            logger.info(f"Email send result: {email_result}")
        except Exception as e:
            logger.error(f"Email send failed: {e}")

        # Post to Slack with Block Kit
        try:
            product_name = spec.get("product_name", "LaunchMind Product")
            blocks = self.slack.build_launch_blocks(
                product_name=product_name,
                tagline=copy.get("tagline", ""),
                description=copy.get("description", ""),
                pr_url=pr_url,
            )
            slack_result = self.slack.post_message(
                text=f"New Launch: {product_name} - {copy.get('tagline', '')}",
                blocks=blocks,
            )
            logger.info(f"Slack post result: {slack_result.get('ok')}")
        except Exception as e:
            logger.error(f"Slack post failed: {e}")

        # Send results back to CEO
        result_msg = self.message_bus.create_message(
            from_agent=self.name,
            to_agent="ceo",
            message_type="result",
            payload=copy,
            parent_message_id=msg.message_id,
        )
        self.message_bus.send(result_msg)
        logger.info("Marketing agent sent copy to CEO.")
