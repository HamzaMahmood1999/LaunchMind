# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LaunchMind is an autonomous multi-agent system that takes a startup idea and runs a full launch pipeline: product spec, landing page, marketing copy, and QA review, with real integrations to GitHub, Slack, and SendGrid. The project is early-stage — agent implementations are scaffolded with TODOs but not yet functional.

## Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then fill in API keys

# Run
python main.py
```

There are no tests, linter, or build system configured yet.

## Architecture

**Entry point:** `main.py` — loads env vars, initializes the MessageBus, and will eventually instantiate and run all agents starting with the CEO agent.

**Message Bus (`core/message_bus.py`):** The central communication layer. SQLite-backed, thread-safe message store with a strict 7-field JSON protocol enforced by Pydantic (`AgentMessage` model). Message types: `task`, `result`, `revision_request`, `confirmation`. Agents communicate exclusively through this bus — they never call each other directly.

**Agent pipeline (`agents/`):** Five agents forming a directed pipeline with a feedback loop:
1. **CEO** — orchestrator. Decomposes the startup idea into tasks, dispatches to other agents, reviews QA reports, triggers revisions if needed.
2. **Product** — generates structured product specs (value prop, personas, features, user stories) via LLM.
3. **Engineer** — generates HTML landing page from the product spec, manages GitHub workflow (issues, branches, PRs). Outputs go to `outputs/`.
4. **Marketing** — generates marketing copy (tagline, description, email, social posts), sends email via SendGrid, posts to Slack.
5. **QA** — reviews engineer and marketing outputs, posts PR review comments, sends pass/fail report back to CEO (closing the feedback loop).

**Integrations (`integrations/`):** Thin wrappers around external APIs:
- `GitHubIntegration` — REST API v3 via `requests` (branches, commits, issues, PRs, review comments)
- `SlackIntegration` — Web API via `requests` with Block Kit formatting
- `EmailIntegration` — SendGrid API

All integrations read credentials from environment variables (see `.env.example`).

## Key Dependencies

- `crewai` — multi-agent orchestration framework
- `openai` — LLM provider
- `pydantic` — message schema validation
- `requests` — HTTP for GitHub/Slack APIs
- `sendgrid` — email delivery
- `python-dotenv` — env var loading

## Environment Variables

Only `OPENAI_API_KEY` is required to start the system. GitHub, Slack, and SendGrid keys are needed for their respective integrations. See `.env.example` for the full list.
