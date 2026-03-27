"""
QA / Reviewer Agent — LaunchMind

Responsibilities:
    - Review the Engineer's HTML landing page for quality and correctness.
    - Review the Marketing agent's copy for tone, accuracy, and completeness.
    - Post inline review comments on the GitHub PR via the API.
    - Produce a structured pass/fail report and send it to the CEO agent.
    - The CEO uses this report to decide if revisions are needed (feedback loop).
"""

import logging

from core.message_bus import MessageBus
from integrations.github_integration import GitHubIntegration

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior QA reviewer for a startup launch agency. You will review two artifacts:
1. An HTML landing page
2. Marketing copy (tagline, description, email, social posts)

Evaluate each on: correctness, completeness, professionalism, and consistency between the two.

You MUST return valid JSON with these exact keys:
- overall_verdict: string, either "pass" or "fail"
- html_review: object with keys:
    - verdict: "pass" or "fail"
    - issues: array of strings (specific problems found, empty if pass)
    - suggestions: array of strings (improvements, even if passing)
    - inline_comments: array of objects with keys: line (integer), comment (string) — at least 2 comments about specific parts of the HTML
- marketing_review: object with keys:
    - verdict: "pass" or "fail"
    - issues: array of strings (specific problems found, empty if pass)
    - suggestions: array of strings
- summary: string (1-2 sentence overall assessment)

Be constructive but set a reasonable quality bar. Only fail if there are significant problems.

Return ONLY the JSON object, no markdown fences or extra text."""


class QAAgent:
    """Reviews agent outputs and produces pass/fail verdicts."""

    def __init__(self, message_bus: MessageBus):
        self.name = "qa"
        self.message_bus = message_bus
        self.github = GitHubIntegration()

    def run(self) -> None:
        """
        Execute the QA agent's workflow.

        Reviews engineer and marketing outputs, posts PR comments,
        and sends a structured report to the CEO.
        """
        messages = self.message_bus.receive(self.name)
        if not messages:
            logger.warning("QA agent: no messages to process.")
            return

        msg = messages[-1]
        logger.info(f"QA agent received {msg.message_type.value} from {msg.from_agent}")

        # TODO: call LLM for review
        # TODO: post inline PR comments via GitHub API
        # TODO: send structured report to CEO
        pass
