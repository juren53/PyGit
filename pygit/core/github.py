"""
GitHub API operations module.

This module provides GitHub-specific functionality for interacting
with GitHub repositories via the GitHub API.
"""

import urllib.request
import urllib.error
import urllib.parse
import json
from typing import Optional, Tuple, List, Dict, Any
from ..utils.logging import get_logger


class GitHubAPI:
    """GitHub API client for repository operations."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.logger = get_logger()

    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make a GET request to the GitHub API."""
        try:
            req = urllib.request.Request(url)

            if self.token:
                req.add_header("Authorization", f"token {self.token}")

            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP Error {e.code} for {url}: {e.reason}")
            return None
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {e}")
            return None

    def parse_git_url(
        self, url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse Git URL and return API URL, owner, and repo."""
        url = url.strip()

        # Remove .git suffix if present
        if url.endswith(".git"):
            url = url[:-4]

        # Handle GitHub URLs
        if "github.com" in url:
            # Convert SSH to HTTPS
            if url.startswith("git@github.com:"):
                url = url.replace("git@github.com:", "https://github.com/")

            # Extract owner and repo
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                return api_url, owner, repo

        return None, None, None

    def get_repo_info(self, api_url: str) -> Optional[Dict[str, Any]]:
        """Get repository information from GitHub API."""
        return self._make_request(api_url)

    def get_default_branch(self, api_url: str) -> str:
        """Get the default branch of the repository."""
        repo_info = self.get_repo_info(api_url)
        if repo_info:
            return repo_info.get("default_branch", "main")

        self.logger.warning(f"Could not get repo info, defaulting to 'main'")
        return "main"

    def get_tree_recursive(
        self, owner: str, repo: str, branch: str
    ) -> List[Dict[str, Any]]:
        """Get the complete file tree recursively."""
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        tree_data = self._make_request(tree_url)

        if tree_data:
            return tree_data.get("tree", [])

        self.logger.error("Could not retrieve repository tree")
        return []

    def get_file_content(
        self, owner: str, repo: str, branch: str, path: str
    ) -> Optional[bytes]:
        """Get raw file content from GitHub."""
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{urllib.parse.quote(path)}"

        try:
            with urllib.request.urlopen(raw_url) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                self.logger.error(f"Error downloading {raw_url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {raw_url}: {e}")
            return None

    def get_branch_info(
        self, owner: str, repo: str, branch: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a branch."""
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        return self._make_request(branch_url)

    def list_branches(self, owner: str, repo: str) -> List[str]:
        """List all branches in the repository."""
        branches_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        branches_data = self._make_request(branches_url)

        if branches_data:
            return [branch["name"] for branch in branches_data]

        return []

    def get_commit_info(
        self, owner: str, repo: str, sha: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a commit."""
        commit_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        return self._make_request(commit_url)
