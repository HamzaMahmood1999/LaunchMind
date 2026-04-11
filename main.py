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
from agents.ceo_agent import CEOAgent
from agents.product_agent import ProductAgent
from agents.engineer_agent import EngineerAgent
from agents.marketing_agent import MarketingAgent
from agents.qa_agent import QAAgent

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

    # Validate that required env vars are set before proceeding
    required_vars = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Create outputs directory
    os.makedirs("outputs", exist_ok=True)

    # Initialize the shared message bus (backed by SQLite)
    bus = MessageBus()
    logger.info("Message bus initialized.")

    # Create all agents with the shared bus instance
    product = ProductAgent(bus)
    engineer = EngineerAgent(bus)
    marketing = MarketingAgent(bus)
    qa = QAAgent(bus)
    ceo = CEOAgent(bus, product, engineer, marketing, qa)

    # Start the pipeline
    try:
        logger.info(f"Starting LaunchMind pipeline with idea: {STARTUP_IDEA[:80]}...")
        ceo.run(STARTUP_IDEA)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
    finally:
        # Print the full message history for debugging / audit
        history = bus.get_history()
        print(f"\n{'#'*60}")
        print(f"  FULL MESSAGE HISTORY ({len(history)} messages)")
        print(f"{'#'*60}")
        for i, msg in enumerate(history, 1):
            print(f"  {i}. [{msg.message_type.value.upper():>18}] {msg.from_agent:>10} -> {msg.to_agent:<10} | keys: {list(msg.payload.keys())}")
        print(f"{'#'*60}\n")
        bus.close()

    logger.info("LaunchMind pipeline complete.")


if __name__ == "__main__":
    main()
