"""
Product Agent — LaunchMind

Responsibilities:
    - Receive a product task from the CEO agent.
    - Use an LLM to generate a structured product specification including:
        * Value proposition
        * User personas
        * Ranked feature list
        * User stories (in standard format)
    - Return the structured spec to the CEO via the message bus.
"""

import logging

from core.message_bus import MessageBus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior product manager at a startup agency. Given a startup idea, produce a structured product specification.

You MUST return valid JSON with these exact keys:
- product_name: string (short product name)
- value_proposition: string (one clear sentence describing what the product does and for whom)
- personas: array of objects, each with keys: name (string), role (string), pain_point (string). Include 2-3 personas.
- features: array of objects, each with keys: name (string), description (string), priority (integer 1-5 where 1 is highest). Include 5 features.
- user_stories: array of 3 strings, each in the format "As a [user], I want to [action] so that [benefit]"

Return ONLY the JSON object, no markdown fences or extra text."""


class ProductAgent:
    """Generates product specifications from CEO tasks."""

    def __init__(self, message_bus: MessageBus):
        self.name = "product"
        self.message_bus = message_bus

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

        msg = messages[-1]
        logger.info(f"Product agent received {msg.message_type.value} from {msg.from_agent}")

        # TODO: call LLM to generate spec
        # TODO: send result back to CEO
        pass
