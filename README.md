# LaunchMind — Multi-Agent Startup System

## Startup Idea

**PyTestGen** is an AI-powered Python CLI tool that leverages natural language processing to automatically generate semantic test cases and structured docstrings for legacy codebases. It targets development teams maintaining aging Python projects who need better test coverage and documentation without the manual overhead. Developers would pay for it because it dramatically reduces the time spent writing tests and docs for inherited code.

## Agent Architecture

```
                          ┌─────────────┐
                          │  CEO Agent  │ (Orchestrator)
                          │  LLM x3+   │
                          └──────┬──────┘
                   ┌─────────────┼─────────────┐
                   │             │             │
                   ▼             ▼             ▼
           ┌──────────┐  ┌───────────┐  ┌───────────┐
           │ Product  │  │ Engineer  │  │ Marketing │
           │  Agent   │  │  Agent    │  │  Agent    │
           │  LLM x1  │  │  LLM x3  │  │  LLM x1  │
           └──────────┘  └───────────┘  └───────────┘
                                │             │
                          ┌─────┘             │
                          ▼                   ▼
                   ┌──────────┐        ┌───────────┐
                   │  GitHub  │        │   Slack   │
                   │  API     │        │ + Email   │
                   └──────────┘        └───────────┘
                          │
                          ▼
                   ┌──────────┐
                   │ QA Agent │ (Reviews PR + Copy)
                   │  LLM x1  │
                   └──────────┘
```

**Communication Flow (via SQLite-backed Message Bus):**

1. **CEO** decomposes the startup idea into tasks (LLM call #1)
2. **CEO** sends task to **Product Agent** via message bus
3. **Product Agent** generates structured spec (LLM) and sends result + confirmation to CEO
4. **CEO** reviews the spec using LLM reasoning (LLM call #2) — rejects first draft with specific feedback
5. **Product Agent** revises spec based on feedback (feedback loop #1)
6. **CEO** approves revised spec, forwards to **Engineer** and **Marketing**
7. **Engineer** generates HTML landing page (LLM), creates GitHub issue, branch, commit, and PR
8. **Marketing** generates copy (LLM), sends email via SendGrid, posts to Slack
9. **CEO** sends all outputs to **QA Agent**
10. **QA Agent** reviews HTML + copy (LLM), posts PR review comments, sends pass/fail report
11. If QA fails, **CEO** sends revision requests to failing agents (feedback loop #2)
12. **CEO** posts final launch summary to Slack (LLM call #3)

All inter-agent messages are structured JSON with: `message_id`, `from_agent`, `to_agent`, `message_type`, `payload`, `timestamp`, `parent_message_id`.

## Setup Instructions

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) installed and running with a model (e.g., `phi4:14b`)
- GitHub Personal Access Token
- Slack Bot Token (workspace with `#launches` channel)
- SendGrid API Key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/HamzaMahmood1999/LaunchMind.git
cd LaunchMind

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Then edit .env with your actual API keys

# 5. Ensure Ollama is running with your model
ollama run phi4:14b

# 6. Run the system
python main.py
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | Yes | Ollama API endpoint (default: `http://localhost:11434/v1`) |
| `OLLAMA_MODEL` | Yes | Model name (e.g., `phi4:14b`) |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token with `repo` scope |
| `GITHUB_REPO_OWNER` | Yes | GitHub repository owner |
| `GITHUB_REPO_NAME` | Yes | GitHub repository name |
| `SLACK_BOT_TOKEN` | Yes | Slack Bot User OAuth Token (`xoxb-...`) |
| `SLACK_CHANNEL` | No | Slack channel (default: `#launches`) |
| `SENDGRID_API_KEY` | Yes | SendGrid API key for email sending |
| `SENDGRID_FROM_EMAIL` | Yes | Verified sender email address |
| `EMAIL_RECIPIENT` | Yes | Test email recipient |

## Platform Integrations

| Platform | Agent | Actions |
|---|---|---|
| **GitHub** | Engineer | Creates issue, creates feature branch, commits HTML landing page, opens pull request |
| **GitHub** | QA | Posts inline review comments on the pull request (at least 2) |
| **Slack** | Marketing | Posts product launch announcement with Block Kit formatting to `#launches` |
| **Slack** | CEO | Posts final pipeline summary to `#launches` |
| **SendGrid** | Marketing | Sends LLM-generated cold outreach email to test recipient |

## Evidence Links

- **GitHub PR by Engineer Agent:** https://github.com/HamzaMahmood1999/LaunchMind/pull/6
- **GitHub Issue by Engineer Agent:** https://github.com/HamzaMahmood1999/LaunchMind/issues/5

## Project Structure

```
LaunchMind/
├── main.py                      # Entry point — runs the full pipeline
├── core/
│   ├── message_bus.py           # SQLite-backed message bus (Pydantic-validated)
│   └── llm.py                   # Shared Ollama LLM helper with retry logic
├── agents/
│   ├── ceo_agent.py             # Orchestrator with feedback loops
│   ├── product_agent.py         # Product specification generator
│   ├── engineer_agent.py        # HTML generator + GitHub workflow
│   ├── marketing_agent.py       # Copy generator + email + Slack
│   └── qa_agent.py              # Reviewer + PR comments
├── integrations/
│   ├── github_integration.py    # GitHub REST API v3 wrapper
│   ├── slack_integration.py     # Slack Web API + Block Kit
│   └── email_integration.py     # SendGrid email sender
├── outputs/                     # Generated landing page HTML
├── requirements.txt
├── .env.example
└── .gitignore
```
