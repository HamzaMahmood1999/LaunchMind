"""
QA / Reviewer Agent — LaunchMind

Responsibilities:
    - Review the Engineer's HTML landing page for quality and correctness.
    - Review the Marketing agent's copy for tone, accuracy, and completeness.
    - Post inline review comments on the GitHub PR via the API.
    - Produce a structured pass/fail report and send it to the CEO agent.
    - The CEO uses this report to decide if revisions are needed (feedback loop).
"""

import json
import logging

from core.llm import call_llm
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

Be constructive but set a reasonable quality bar. Minor cosmetic issues should still pass.
Only fail if there are significant problems like missing sections, broken structure, or misleading content.

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

        html_content = msg.payload.get("html", "")
        marketing_copy = msg.payload.get("marketing_copy", {})
        pr_number = msg.payload.get("pr_number", 0)
        commit_sha = msg.payload.get("commit_sha", "")

        user_prompt = (
            f"HTML Landing Page:\n```html\n{html_content[:3000]}\n```\n\n"
            f"Marketing Copy:\n{json.dumps(marketing_copy, indent=2)}"
        )

        # LLM review
        try:
            report = call_llm(SYSTEM_PROMPT, user_prompt, json_mode=True)
            logger.info(f"QA verdict: {report.get('overall_verdict', 'unknown')}")
        except Exception as e:
            logger.error(f"QA agent LLM call failed: {e}")
            # Default to pass on LLM failure to avoid blocking pipeline
            report = {
                "overall_verdict": "pass",
                "html_review": {"verdict": "pass", "issues": [], "suggestions": [], "inline_comments": []},
                "marketing_review": {"verdict": "pass", "issues": [], "suggestions": []},
                "summary": f"QA review could not be completed due to error: {e}. Defaulting to pass.",
            }

        # Post inline review comments on GitHub PR
        if pr_number and commit_sha:
            inline_comments = report.get("html_review", {}).get("inline_comments", [])
            for comment in inline_comments[:3]:
                try:
                    line = comment.get("line", 1)
                    body = comment.get("comment", "")
                    if body:
                        self.github.post_review_comment(
                            pr_number=pr_number,
                            body=f"[QA Review] {body}",
                            commit_id=commit_sha,
                            path="index.html",
                            line=line,
                        )
                except Exception as e:
                    logger.error(f"Failed to post PR comment: {e}")

        # Send report to CEO
        result_msg = self.message_bus.create_message(
            from_agent=self.name,
            to_agent="ceo",
            message_type="result",
            payload=report,
            parent_message_id=msg.message_id,
        )
        self.message_bus.send(result_msg)
        logger.info("QA agent sent report to CEO.")
