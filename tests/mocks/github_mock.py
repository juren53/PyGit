"""
GitHub API Mock Infrastructure

This module provides mock implementations of the GitHub API
for testing clone, fetch, and other remote operations without
making actual network requests.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


class GitHubMockResponses:
    """Pre-built mock responses for common GitHub API endpoints."""

    @staticmethod
    def repo_info(
        owner: str = "testuser",
        repo: str = "test-repo",
        default_branch: str = "main",
        private: bool = False,
    ) -> Dict[str, Any]:
        """Generate mock repository info response."""
        return {
            "id": 123456789,
            "node_id": "MDEwOlJlcG9zaXRvcnkxMjM0NTY3ODk=",
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "private": private,
            "owner": {
                "login": owner,
                "id": 12345,
                "type": "User",
            },
            "html_url": f"https://github.com/{owner}/{repo}",
            "description": "A test repository for PyGit",
            "fork": False,
            "url": f"https://api.github.com/repos/{owner}/{repo}",
            "clone_url": f"https://github.com/{owner}/{repo}.git",
            "ssh_url": f"git@github.com:{owner}/{repo}.git",
            "default_branch": default_branch,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
            "pushed_at": "2024-01-15T12:00:00Z",
            "size": 1024,
            "stargazers_count": 10,
            "watchers_count": 10,
            "language": "Python",
            "forks_count": 2,
            "open_issues_count": 1,
        }

    @staticmethod
    def tree_recursive(
        files: Optional[List[Dict[str, str]]] = None,
        sha: str = "abc123def456",
    ) -> Dict[str, Any]:
        """Generate mock tree recursive response.

        Args:
            files: List of dicts with 'path', 'type', and optionally 'mode' keys
            sha: Tree SHA to use
        """
        if files is None:
            files = [
                {"path": "README.md", "type": "blob"},
                {"path": "setup.py", "type": "blob"},
                {"path": "src", "type": "tree"},
                {"path": "src/__init__.py", "type": "blob"},
                {"path": "src/main.py", "type": "blob"},
            ]

        tree = []
        for i, f in enumerate(files):
            entry = {
                "path": f["path"],
                "mode": f.get("mode", "100644" if f["type"] == "blob" else "040000"),
                "type": f["type"],
                "sha": f.get("sha", f"sha{i:040d}"),
                "size": f.get("size", 100) if f["type"] == "blob" else None,
                "url": f"https://api.github.com/repos/test/test/git/blobs/sha{i:040d}",
            }
            if entry["size"] is None:
                del entry["size"]
            tree.append(entry)

        return {
            "sha": sha,
            "url": f"https://api.github.com/repos/test/test/git/trees/{sha}",
            "tree": tree,
            "truncated": False,
        }

    @staticmethod
    def branch_info(
        name: str = "main",
        commit_sha: str = "abc123def456789",
        protected: bool = False,
    ) -> Dict[str, Any]:
        """Generate mock branch info response."""
        return {
            "name": name,
            "commit": {
                "sha": commit_sha,
                "node_id": "MDY6Q29tbWl0MTIzNDU2Nzg5",
                "url": f"https://api.github.com/repos/test/test/commits/{commit_sha}",
            },
            "protected": protected,
            "protection": {
                "enabled": protected,
                "required_status_checks": {
                    "enforcement_level": "off",
                    "contexts": [],
                },
            },
        }

    @staticmethod
    def branches_list(
        branches: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate mock branches list response."""
        if branches is None:
            branches = ["main", "develop", "feature/test"]

        return [
            {
                "name": name,
                "commit": {
                    "sha": f"sha_{name.replace('/', '_')}",
                    "url": f"https://api.github.com/repos/test/test/commits/sha_{name}",
                },
                "protected": name == "main",
            }
            for name in branches
        ]

    @staticmethod
    def commit_info(
        sha: str = "abc123def456",
        message: str = "Test commit",
        author_name: str = "Test User",
        author_email: str = "test@example.com",
        parents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate mock commit info response."""
        if parents is None:
            parents = []

        return {
            "sha": sha,
            "node_id": "MDY6Q29tbWl0MTIzNDU2Nzg5",
            "url": f"https://api.github.com/repos/test/test/commits/{sha}",
            "html_url": f"https://github.com/test/test/commit/{sha}",
            "commit": {
                "author": {
                    "name": author_name,
                    "email": author_email,
                    "date": "2024-01-15T12:00:00Z",
                },
                "committer": {
                    "name": author_name,
                    "email": author_email,
                    "date": "2024-01-15T12:00:00Z",
                },
                "message": message,
                "tree": {
                    "sha": f"tree_{sha}",
                    "url": f"https://api.github.com/repos/test/test/git/trees/tree_{sha}",
                },
            },
            "author": {
                "login": author_name.lower().replace(" ", ""),
                "id": 12345,
                "type": "User",
            },
            "committer": {
                "login": author_name.lower().replace(" ", ""),
                "id": 12345,
                "type": "User",
            },
            "parents": [
                {"sha": p, "url": f"https://api.github.com/repos/test/test/commits/{p}"}
                for p in parents
            ],
        }

    @staticmethod
    def file_content(content: bytes = b"Hello, World!\n") -> bytes:
        """Return raw file content (not JSON)."""
        return content


class MockGitHubAPI:
    """Mock implementation of GitHubAPI for testing.

    This class provides a drop-in replacement for GitHubAPI that
    returns configurable mock responses instead of making network requests.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.responses: Dict[str, Any] = {}
        self.file_contents: Dict[str, bytes] = {}
        self.call_history: List[Dict[str, Any]] = []
        self._setup_default_responses()

    def _setup_default_responses(self) -> None:
        """Set up default mock responses."""
        self.responses = {
            "repo_info": GitHubMockResponses.repo_info(),
            "tree": GitHubMockResponses.tree_recursive(),
            "branch_info": GitHubMockResponses.branch_info(),
            "branches": GitHubMockResponses.branches_list(),
            "commit": GitHubMockResponses.commit_info(),
        }
        self.file_contents = {
            "README.md": b"# Test Repository\n\nThis is a test.\n",
            "setup.py": b"from setuptools import setup\nsetup(name='test')\n",
            "src/__init__.py": b"",
            "src/main.py": b"print('Hello, World!')\n",
        }

    def _record_call(self, method: str, **kwargs) -> None:
        """Record an API call for verification."""
        self.call_history.append({"method": method, "kwargs": kwargs})

    def set_response(self, key: str, response: Any) -> None:
        """Set a custom response for a specific endpoint."""
        self.responses[key] = response

    def set_file_content(self, path: str, content: bytes) -> None:
        """Set content for a specific file path."""
        self.file_contents[path] = content

    def parse_git_url(self, url: str):
        """Mock parse_git_url - returns fixed test values."""
        self._record_call("parse_git_url", url=url)
        return (
            "https://api.github.com/repos/testuser/test-repo",
            "testuser",
            "test-repo",
        )

    def get_repo_info(self, api_url: str) -> Optional[Dict[str, Any]]:
        """Mock get_repo_info."""
        self._record_call("get_repo_info", api_url=api_url)
        return self.responses.get("repo_info")

    def get_default_branch(self, api_url: str) -> str:
        """Mock get_default_branch."""
        self._record_call("get_default_branch", api_url=api_url)
        repo_info = self.responses.get("repo_info", {})
        return repo_info.get("default_branch", "main")

    def get_tree_recursive(
        self, owner: str, repo: str, branch: str
    ) -> List[Dict[str, Any]]:
        """Mock get_tree_recursive."""
        self._record_call(
            "get_tree_recursive", owner=owner, repo=repo, branch=branch
        )
        tree_data = self.responses.get("tree", {})
        return tree_data.get("tree", [])

    def get_file_content(
        self, owner: str, repo: str, branch: str, path: str
    ) -> Optional[bytes]:
        """Mock get_file_content."""
        self._record_call(
            "get_file_content", owner=owner, repo=repo, branch=branch, path=path
        )
        return self.file_contents.get(path)

    def get_branch_info(
        self, owner: str, repo: str, branch: str
    ) -> Optional[Dict[str, Any]]:
        """Mock get_branch_info."""
        self._record_call(
            "get_branch_info", owner=owner, repo=repo, branch=branch
        )
        return self.responses.get("branch_info")

    def list_branches(self, owner: str, repo: str) -> List[str]:
        """Mock list_branches."""
        self._record_call("list_branches", owner=owner, repo=repo)
        branches = self.responses.get("branches", [])
        return [b["name"] for b in branches]

    def get_commit_info(
        self, owner: str, repo: str, sha: str
    ) -> Optional[Dict[str, Any]]:
        """Mock get_commit_info."""
        self._record_call("get_commit_info", owner=owner, repo=repo, sha=sha)
        return self.responses.get("commit")

    def assert_called(self, method: str, **expected_kwargs) -> None:
        """Assert that a method was called with specific arguments."""
        for call in self.call_history:
            if call["method"] == method:
                if not expected_kwargs:
                    return  # Method was called, no specific args required
                if all(
                    call["kwargs"].get(k) == v for k, v in expected_kwargs.items()
                ):
                    return
        raise AssertionError(
            f"Expected call to {method} with {expected_kwargs} not found. "
            f"Calls: {self.call_history}"
        )

    def assert_not_called(self, method: str) -> None:
        """Assert that a method was never called."""
        for call in self.call_history:
            if call["method"] == method:
                raise AssertionError(
                    f"Expected {method} to not be called, but it was. "
                    f"Calls: {self.call_history}"
                )

    def reset_call_history(self) -> None:
        """Clear the call history."""
        self.call_history.clear()


@contextmanager
def mock_github_api(mock_api: Optional[MockGitHubAPI] = None):
    """Context manager to patch GitHubAPI with a mock.

    Usage:
        with mock_github_api() as mock:
            mock.set_file_content("test.txt", b"content")
            # ... test code that uses GitHubAPI ...
            mock.assert_called("get_file_content", path="test.txt")
    """
    if mock_api is None:
        mock_api = MockGitHubAPI()

    with patch("pygit.core.github.GitHubAPI", return_value=mock_api):
        yield mock_api
