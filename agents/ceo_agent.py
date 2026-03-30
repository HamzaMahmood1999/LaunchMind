"""
CEO Agent — LaunchMind

The CEO Agent is the orchestrator of the entire LaunchMind system.

Responsibilities:
    - Receive the startup idea and decompose it into structured JSON tasks.
    - Dispatch tasks to the Product, Engineer, and Marketing agents.
    - Review outputs from sub-agents via the QA agent's pass/fail report.
    - If QA returns 'fail', reason about it and send revision requests.
    - Once all outputs pass QA, compile a final summary and post to Slack.
"""

import json
import logging

from core.llm import call_llm
from core.message_bus import MessageBus
from integrations.slack_integration import SlackIntegration

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """You are the CEO of a startup launch agency. Given a startup idea, decompose it into three structured tasks for your team members.

You MUST return valid JSON with these exact keys:
- product_task: string (detailed instructions for the product manager to create a product spec — mention personas, features, user stories)
- engineer_task: string (detailed instructions for the engineer to build an HTML landing page based on the product spec)
- marketing_task: string (detailed instructions for the marketing lead to create copy, email campaigns, and social media posts)

Be specific. Reference the startup idea in each task. Each task should be 2-3 sentences.

Return ONLY the JSON object, no markdown fences or extra text."""

REVIEW_PROMPT = """You are a demanding but fair CEO reviewing a product specification for a startup.

Evaluate whether the spec is:
1. Complete (has product name, value proposition, personas, features, user stories)
2. Specific (not generic — tied to the actual startup idea)
3. Actionable (an engineer and marketer could work from this)

You MUST return valid JSON with these exact keys:
- approved: boolean (true if the spec meets all three criteria, false otherwise)
- feedback: string (if not approved, explain specifically what needs improvement. If approved, say why it's good.)

Return ONLY the JSON object."""

MAX_PRODUCT_REVISIONS = 1
MAX_QA_RETRIES = 1


class CEOAgent:
    """Orchestrates the multi-agent startup pipeline."""

    def __init__(self, message_bus: MessageBus, product_agent, engineer_agent,
                 marketing_agent, qa_agent):
        self.name = "ceo"
        self.message_bus = message_bus
        self.product_agent = product_agent
        self.engineer_agent = engineer_agent
        self.marketing_agent = marketing_agent
        self.qa_agent = qa_agent
        self.slack = SlackIntegration()

    def run(self, startup_idea: str) -> None:
        """
        Execute the CEO agent's workflow.

        Args:
            startup_idea: The raw startup idea to process.
        """
        logger.info(f"CEO agent starting pipeline for idea: {startup_idea[:80]}...")

        # Step 1: Decompose idea into tasks
        logger.info("Step 1: Decomposing startup idea into tasks...")
        tasks = self._decompose_idea(startup_idea)
        if not tasks:
            logger.error("Failed to decompose idea. Aborting.")
            return
        logger.info("Tasks created for: product, engineer, marketing")

        # Step 2: Send task to Product Agent
        logger.info("Step 2: Dispatching task to Product agent...")
        task_msg = self.message_bus.create_message(
            from_agent="ceo",
            to_agent="product",
            message_type="task",
            payload={
                "startup_idea": startup_idea,
                "instructions": tasks["product_task"],
            },
        )
        self.message_bus.send(task_msg)
        self.product_agent.run()
        product_result = self._get_result_from("product")
        if not product_result or "error" in product_result.payload:
            logger.error("Product agent failed. Aborting.")
            return
        product_spec = product_result.payload

        # Step 3: CEO reviews product spec (feedback loop)
        logger.info("Step 3: Reviewing product spec...")
        for revision in range(MAX_PRODUCT_REVISIONS + 1):
            review = self._review_spec(product_spec)
            if review.get("approved", True):
                logger.info(f"Product spec approved: {review.get('feedback', '')}")
                break
            else:
                logger.info(f"Product spec rejected: {review.get('feedback', '')}")
                if revision < MAX_PRODUCT_REVISIONS:
                    logger.info("Sending revision request to Product agent...")
                    rev_msg = self.message_bus.create_message(
                        from_agent="ceo",
                        to_agent="product",
                        message_type="revision_request",
                        payload={
                            "feedback": review["feedback"],
                            "startup_idea": startup_idea,
                        },
                        parent_message_id=product_result.message_id,
                    )
                    self.message_bus.send(rev_msg)
                    self.product_agent.run()
                    product_result = self._get_result_from("product")
                    if not product_result or "error" in product_result.payload:
                        logger.error("Product revision failed. Continuing with current spec.")
                        break
                    product_spec = product_result.payload

        # TODO: Step 4 — dispatch to Engineer agent
        # TODO: Step 5 — dispatch to Marketing agent
        # TODO: Step 6 — dispatch to QA agent
        # TODO: Step 7 — QA feedback loop
        # TODO: Step 8 — post final summary to Slack
        pass

    def _decompose_idea(self, startup_idea: str) -> dict | None:
        """Use LLM to break the startup idea into structured tasks."""
        try:
            tasks = call_llm(DECOMPOSE_PROMPT, f"Startup idea: {startup_idea}", json_mode=True)
            logger.info(f"Decompose result keys: {list(tasks.keys()) if isinstance(tasks, dict) else type(tasks)}")

            if isinstance(tasks, dict) and "product_task" not in tasks:
                for key in tasks:
                    if isinstance(tasks[key], dict) and "product_task" in tasks[key]:
                        tasks = tasks[key]
                        break

            required = ["product_task", "engineer_task", "marketing_task"]
            missing = [k for k in required if k not in tasks]
            if missing:
                logger.warning(f"Missing keys in decomposition: {missing}. Filling defaults.")
                for k in missing:
                    tasks[k] = f"Complete your part of the startup: {startup_idea}"

            logger.info("Idea decomposed into tasks successfully.")
            return tasks
        except Exception as e:
            logger.error(f"Failed to decompose idea: {e}")
            return None

    def _review_spec(self, spec: dict) -> dict:
        """Use LLM to review a product spec and decide if it's acceptable."""
        try:
            return call_llm(REVIEW_PROMPT, f"Product spec:\n{json.dumps(spec, indent=2)}", json_mode=True)
        except Exception as e:
            logger.error(f"Failed to review spec: {e}")
            return {"approved": True, "feedback": "Review failed, defaulting to approved."}

    def _get_result_from(self, agent_name: str):
        """Read messages and find the latest result from a specific agent."""
        messages = self.message_bus.receive(self.name)
        for msg in reversed(messages):
            if msg.from_agent == agent_name:
                return msg
        return None
