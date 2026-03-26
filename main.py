"""
LaunchMind Multi-Agent System — Entry Point

Loads environment configuration, initializes the message bus,
and orchestrates the multi-agent pipeline starting with the CEO agent.
"""

import logging
import os
import sys

from dotenv import load_dotenv

from core.message_bus import MessageBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("launchmind")

# The startup idea to be processed by the agent system
STARTUP_IDEA = (
    "An AI-powered Python CLI tool that leverages natural language processing "
    "to automatically generate semantic test cases and structured docstrings "
    "for legacy codebases."
)


def main():
    """Initialize and run the LaunchMind multi-agent system."""
    # Load environment variables
    load_dotenv()

    # Validate critical env vars
    required_vars = ["OPENAI_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Initialize the shared message bus (SQLite-backed)
    bus = MessageBus()
    logger.info("Message bus initialized.")

    # TODO: Initialize all agents with the shared message bus
    # from agents.ceo_agent import CEOAgent
    # from agents.product_agent import ProductAgent
    # from agents.engineer_agent import EngineerAgent
    # from agents.marketing_agent import MarketingAgent
    # from agents.qa_agent import QAAgent
    #
    # ceo = CEOAgent(bus)
    # product = ProductAgent(bus)
    # engineer = EngineerAgent(bus)
    # marketing = MarketingAgent(bus)
    # qa = QAAgent(bus)

    # TODO: Start the pipeline
    # ceo.run(STARTUP_IDEA)

    logger.info("LaunchMind pipeline complete.")


if __name__ == "__main__":
    main()
