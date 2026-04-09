"""
GitHub Integration — LaunchMind

Handles all GitHub API interactions:
    - Creating branches
    - Committing files
    - Creating issues
    - Opening pull requests
    - Posting review comments

Uses the GITHUB_TOKEN environment variable for authentication.
All calls go through the GitHub REST API v3 via the `requests` library.
"""

import base64
import logging
import os

import requests

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubIntegration:
    """Manages GitHub repository operations via REST API."""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_REPO_OWNER")
        self.repo = os.getenv("GITHUB_REPO_NAME")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    @property
    def repo_url(self) -> str:
        return f"{GITHUB_API_BASE}/repos/{self.owner}/{self.repo}"

    def create_branch(self, branch_name: str, from_branch: str = "main") -> dict:
        """Create a new branch from an existing one."""
        # Get SHA of the source branch
        resp = requests.get(
            f"{self.repo_url}/git/ref/heads/{from_branch}",
            headers=self.headers,
        )
        if resp.status_code != 200:
            logger.error(f"Failed to get ref for {from_branch}: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        sha = resp.json()["object"]["sha"]

        # Create the new branch ref
        resp = requests.post(
            f"{self.repo_url}/git/refs",
            headers=self.headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to create branch {branch_name}: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        logger.info(f"Created branch: {branch_name}")
        return resp.json()

    def commit_file(
        self, branch: str, file_path: str, content: str, message: str
    ) -> dict:
        """Commit a single file to a branch (creates or updates)."""
        # Check if the file already exists — we need its SHA for an update
        resp = requests.get(
            f"{self.repo_url}/contents/{file_path}",
            headers=self.headers,
            params={"ref": branch},
        )
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
            "committer": {
                "name": "EngineerAgent",
                "email": "agent@launchmind.ai",
            },
        }
        if resp.status_code == 200:
            payload["sha"] = resp.json()["sha"]

        resp = requests.put(
            f"{self.repo_url}/contents/{file_path}",
            headers=self.headers,
            json=payload,
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to commit {file_path}: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        logger.info(f"Committed {file_path} to {branch}")
        return resp.json()

    def create_issue(self, title: str, body: str, labels: list = None) -> dict:
        """Create a GitHub issue."""
        resp = requests.post(
            f"{self.repo_url}/issues",
            headers=self.headers,
            json={"title": title, "body": body, "labels": labels or []},
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to create issue: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        data = resp.json()
        logger.info(f"Created issue #{data['number']}: {title}")
        return data

    def create_pull_request(
        self, title: str, body: str, head: str, base: str = "main"
    ) -> dict:
        """Open a pull request."""
        resp = requests.post(
            f"{self.repo_url}/pulls",
            headers=self.headers,
            json={"title": title, "body": body, "head": head, "base": base},
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to create PR: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        data = resp.json()
        logger.info(f"Opened PR #{data['number']}: {title}")
        return data

    def post_review_comment(
        self, pr_number: int, body: str, commit_id: str, path: str, line: int
    ) -> dict:
        """Post an inline review comment on a PR."""
        resp = requests.post(
            f"{self.repo_url}/pulls/{pr_number}/comments",
            headers=self.headers,
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
            },
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to post review comment: {resp.status_code} {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        logger.info(f"Posted review comment on PR #{pr_number}")
        return resp.json()
