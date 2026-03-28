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

        # TODO: Step 3 — review product spec (feedback loop)
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

            # Handle nested response (some models wrap in an outer key)
            if isinstance(tasks, dict) and "product_task" not in tasks:
                for key in tasks:
                    if isinstance(tasks[key], dict) and "product_task" in tasks[key]:
                        tasks = tasks[key]
                        break

            # Validate required keys exist
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
