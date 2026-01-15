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

    def _post_request(
        self, url: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Make a POST request to the GitHub API."""
        if not self.token:
            self.logger.error("GitHub token required for write operations")
            return None

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=json_data,
                method="POST"
            )
            req.add_header("Authorization", f"token {self.token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/vnd.github.v3+json")

            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            self.logger.error(f"HTTP Error {e.code} for POST {url}: {e.reason}")
            if error_body:
                self.logger.error(f"Response: {error_body}")
            return None
        except Exception as e:
            self.logger.error(f"Error making POST request to {url}: {e}")
            return None

    def _patch_request(
        self, url: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Make a PATCH request to the GitHub API."""
        if not self.token:
            self.logger.error("GitHub token required for write operations")
            return None

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=json_data,
                method="PATCH"
            )
            req.add_header("Authorization", f"token {self.token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/vnd.github.v3+json")

            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            self.logger.error(f"HTTP Error {e.code} for PATCH {url}: {e.reason}")
            if error_body:
                self.logger.error(f"Response: {error_body}")
            return None
        except Exception as e:
            self.logger.error(f"Error making PATCH request to {url}: {e}")
            return None

    # ========== Git Data API Methods for Push ==========

    def create_blob(
        self, owner: str, repo: str, content: bytes, encoding: str = "base64"
    ) -> Optional[str]:
        """
        Create a blob object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            content: File content as bytes
            encoding: "utf-8" for text, "base64" for binary

        Returns:
            SHA of created blob, or None on error
        """
        import base64

        url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs"

        if encoding == "base64":
            content_str = base64.b64encode(content).decode("ascii")
        else:
            content_str = content.decode("utf-8")

        data = {
            "content": content_str,
            "encoding": encoding
        }

        result = self._post_request(url, data)
        if result:
            return result.get("sha")
        return None

    def create_tree(
        self,
        owner: str,
        repo: str,
        tree_items: List[Dict[str, str]],
        base_tree: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a tree object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            tree_items: List of tree entries, each with mode, path, type, sha
            base_tree: SHA of base tree (for incremental updates)

        Returns:
            SHA of created tree, or None on error
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees"

        data = {"tree": tree_items}
        if base_tree:
            data["base_tree"] = base_tree

        result = self._post_request(url, data)
        if result:
            return result.get("sha")
        return None

    def create_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parent_shas: List[str],
        author: Optional[Dict[str, str]] = None,
        committer: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Create a commit object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            message: Commit message
            tree_sha: SHA of the tree for this commit
            parent_shas: List of parent commit SHAs
            author: Author info dict with name, email, date
            committer: Committer info dict with name, email, date

        Returns:
            SHA of created commit, or None on error
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/commits"

        data = {
            "message": message,
            "tree": tree_sha,
            "parents": parent_shas
        }

        if author:
            data["author"] = author
        if committer:
            data["committer"] = committer

        result = self._post_request(url, data)
        if result:
            return result.get("sha")
        return None

    def update_ref(
        self,
        owner: str,
        repo: str,
        ref: str,
        sha: str,
        force: bool = False
    ) -> bool:
        """
        Update a reference (branch) to point to a new commit.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., "heads/main")
            sha: New commit SHA
            force: Force update even if not fast-forward

        Returns:
            True if successful, False otherwise
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/{ref}"

        data = {
            "sha": sha,
            "force": force
        }

        result = self._patch_request(url, data)
        return result is not None

    def create_ref(
        self,
        owner: str,
        repo: str,
        ref: str,
        sha: str
    ) -> bool:
        """
        Create a new reference (branch).

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Full reference name (e.g., "refs/heads/new-branch")
            sha: Commit SHA to point to

        Returns:
            True if successful, False otherwise
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"

        data = {
            "ref": ref,
            "sha": sha
        }

        result = self._post_request(url, data)
        return result is not None

    def get_ref(
        self, owner: str, repo: str, ref: str
    ) -> Optional[str]:
        """
        Get the SHA that a reference points to.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., "heads/main")

        Returns:
            SHA of the commit, or None if not found
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/{ref}"
        result = self._make_request(url)
        if result and "object" in result:
            return result["object"].get("sha")
        return None
