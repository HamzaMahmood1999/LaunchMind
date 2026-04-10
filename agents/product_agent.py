"""
Product Agent — LaunchMind

Responsibilities:
    - Receive a product task from the CEO agent via the message bus.
    - Use an LLM to generate a structured product specification including:
        * Value proposition
        * User personas
        * Ranked feature list
        * User stories (in standard format)
    - Handle revision requests from the CEO with targeted feedback.
    - Return the structured spec and a confirmation to the CEO via the message bus.
"""

import logging

from core.llm import call_llm
from core.message_bus import MessageBus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior product manager at a startup agency. Given a startup idea, produce a structured product specification.

You MUST return valid JSON with these exact keys:
- product_name: string (short product name)
- value_proposition: string (one clear sentence describing what the product does and for whom)
- personas: array of objects, each with keys: name (string), role (string), pain_point (string). Include 2-3 personas.
- features: array of objects, each with keys: name (string), description (string), priority (integer 1-5 where 1 is highest). Include 5 features.
- user_stories: array of 3 strings, each in the format "As a [user], I want to [action] so that [benefit]"

Return ONLY the JSON object, no markdown fences or extra text."""


# ---------------------------------------------------------------------------
# Product Agent
# ---------------------------------------------------------------------------

class ProductAgent:
    """Generates product specifications from CEO tasks."""

    def __init__(self, message_bus: MessageBus):
        self.name = "product"
        self.message_bus = message_bus

    # ------------------------------------------------------------------
    # Main workflow
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Execute the Product agent's workflow.

        Polls the message bus for tasks from the CEO, generates
        a product spec via LLM, and sends the result back.
        """
        messages = self.message_bus.receive(self.name)
        if not messages:
            logger.warning("Product agent: no messages to process.")
            return

        # Always process the most recent message
        msg = messages[-1]
        logger.info(f"Product agent received {msg.message_type.value} from {msg.from_agent}")

        # Build the user prompt depending on whether this is a new task or revision
        user_prompt = self._build_prompt(msg)

        # Call the LLM to generate the product specification
        try:
            spec = call_llm(SYSTEM_PROMPT, user_prompt, json_mode=True)
            logger.info(f"Product agent generated spec for: {spec.get('product_name', 'unknown')}")
        except Exception as e:
            logger.error(f"Product agent LLM call failed: {e}")
            self._send_error(msg, str(e))
            return

        # Send the spec result back to the CEO
        result_msg = self.message_bus.create_message(
            from_agent=self.name,
            to_agent="ceo",
            message_type="result",
            payload=spec,
            parent_message_id=msg.message_id,
        )
        self.message_bus.send(result_msg)

        # Send a confirmation so the CEO knows the spec is ready for review
        confirmation_msg = self.message_bus.create_message(
            from_agent=self.name,
            to_agent="ceo",
            message_type="confirmation",
            payload={
                "status": "spec_ready",
                "product_name": spec.get("product_name", "unknown"),
                "message": f"Product specification for '{spec.get('product_name', 'unknown')}' is ready for review.",
            },
            parent_message_id=msg.message_id,
        )
        self.message_bus.send(confirmation_msg)
        logger.info("Product agent sent spec and confirmation to CEO.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, msg) -> str:
        """Build the user prompt based on the incoming message type."""
        if msg.message_type.value == "revision_request":
            feedback = msg.payload.get("feedback", "")
            idea = msg.payload.get("startup_idea", "")
            return (
                f"The previous product spec was rejected. Feedback: {feedback}\n\n"
                f"Original startup idea: {idea}\n\n"
                "Please generate an improved product specification addressing the feedback."
            )

        idea = msg.payload.get("startup_idea", "")
        instructions = msg.payload.get("instructions", "")
        return f"Startup idea: {idea}\n\nAdditional instructions: {instructions}"

    def _send_error(self, original_msg, error_text: str) -> None:
        """Send an error result back to the CEO when the LLM call fails."""
        error_msg = self.message_bus.create_message(
            from_agent=self.name,
            to_agent="ceo",
            message_type="result",
            payload={"error": error_text},
            parent_message_id=original_msg.message_id,
        )
        self.message_bus.send(error_msg)
