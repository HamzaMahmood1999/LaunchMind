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

logger = logging.getLogger(__name__)


class QAAgent:
    """Reviews agent outputs and produces pass/fail verdicts."""

    def __init__(self, message_bus: MessageBus):
        self.name = "qa"
        self.message_bus = message_bus

    def run(self) -> None:
        """
        Execute the QA agent's workflow.

        Reviews engineer and marketing outputs, posts PR comments,
        and sends a structured report to the CEO.
        """
        # TODO: 1. Receive engineer HTML and marketing copy from message bus
        # TODO: 2. Use LLM to evaluate quality of each artifact
        # TODO: 3. Post inline review comments on GitHub PR
        # TODO: 4. Compile structured pass/fail report
        # TODO: 5. Send report to CEO via message bus
        raise NotImplementedError("QA agent pipeline not yet implemented.")
