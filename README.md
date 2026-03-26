# LaunchMind — Multi-Agent Startup System

An autonomous multi-agent system that takes a startup idea and runs the full launch pipeline: product spec → landing page → marketing copy → QA review — with real integrations to GitHub, Slack, and SendGrid.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your API keys

# 4. Run the system
python main.py
```

## Architecture

```
main.py                  ← Entry point & orchestrator
├── core/
│   └── message_bus.py   ← SQLite-backed JSON message passing
├── agents/
│   ├── ceo_agent.py     ← Orchestrates tasks & feedback loop
│   ├── product_agent.py ← Generates product specs
│   ├── engineer_agent.py← Builds landing page & GitHub ops
│   ├── marketing_agent.py← Copy, email, Slack posts
│   └── qa_agent.py      ← Reviews & pass/fail verdicts
└── integrations/
    ├── github_integration.py
    ├── slack_integration.py
    └── email_integration.py
```

## Required API Keys

| Variable | Service |
|---|---|
| `OPENAI_API_KEY` | OpenAI LLM |
| `GITHUB_TOKEN` | GitHub API |
| `SLACK_BOT_TOKEN` | Slack Web API |
| `SENDGRID_API_KEY` | SendGrid Email |

See `.env.example` for the full list.
