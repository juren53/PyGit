"""
Fetch command implementation.

This module provides the fetch functionality that downloads objects
and refs from a remote repository without merging.
"""

from pathlib import Path
from typing import Optional, Dict, List, Set, Any, Callable
from ..core.repository import Repository
from ..core.config import Config
from ..core.github import GitHubAPI
from ..core.objects import Blob, Tree, TreeEntry, Commit, Author
from ..utils.logging import get_logger


class FetchCommand:
    """Fetch command to download refs and objects from remote."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        self.github_api = GitHubAPI(github_token)
        self.logger = get_logger()
        self.progress_callback = progress_callback
        self._fetched_objects: Set[str] = set()

    def fetch(
        self,
        repo_path: str = ".",
        remote: str = "origin",
        branch: Optional[str] = None,
        all_branches: bool = False,
        prune: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """
        Fetch refs and objects from a remote repository.

        Args:
            repo_path: Path to the local repository
            remote: Name of the remote (default: origin)
            branch: Specific branch to fetch (optional)
            all_branches: Fetch all branches
            prune: Remove remote-tracking refs that no longer exist
            dry_run: Show what would be done without making changes

        Returns:
            True if fetch was successful, False otherwise
        """
        try:
            # Open the repository
            repo = Repository(repo_path)
            config = Config(repo.git_dir)

            # Get remote configuration
            remote_config = config.get_remote(remote)
            if not remote_config or "url" not in remote_config:
                self.logger.error(f"Remote '{remote}' not configured")
                return False

            remote_url = remote_config["url"]
            self.logger.info(f"Fetching from {remote} ({remote_url})")

            # Parse the URL to get owner/repo
            api_url, owner, repo_name = self.github_api.parse_git_url(remote_url)
            if not api_url:
                self.logger.error("Currently only GitHub repositories are supported")
                return False

            # Get list of branches to fetch
            if branch:
                branches_to_fetch = [branch]
            elif all_branches:
                branches_to_fetch = self.github_api.list_branches(owner, repo_name)
                if not branches_to_fetch:
                    self.logger.error("Could not retrieve branch list")
                    return False
            else:
                # Fetch the default branch or configured tracking branches
                default_branch = self.github_api.get_default_branch(api_url)
                branches_to_fetch = [default_branch]

            self.logger.info(f"Branches to fetch: {', '.join(branches_to_fetch)}")

            if dry_run:
                self.logger.info("Dry run - no changes will be made")
                for branch_name in branches_to_fetch:
                    branch_info = self.github_api.get_branch_info(owner, repo_name, branch_name)
                    if branch_info:
                        commit_sha = branch_info["commit"]["sha"]
                        self.logger.info(f"  {remote}/{branch_name} -> {commit_sha[:8]}")
                return True

            # Fetch each branch
            updated_refs = []
            for branch_name in branches_to_fetch:
                result = self._fetch_branch(
                    repo, owner, repo_name, remote, branch_name
                )
                if result:
                    updated_refs.append(result)

            # Handle pruning
            if prune:
                self._prune_refs(repo, remote, owner, repo_name)

            # Report results
            if updated_refs:
                self.logger.info(f"Fetched {len(updated_refs)} ref(s)")
                for ref_info in updated_refs:
                    old_sha = ref_info.get("old_sha", "0" * 40)[:8]
                    new_sha = ref_info["new_sha"][:8]
                    ref_name = ref_info["ref"]
                    if old_sha == "0" * 8:
                        self.logger.info(f"  * [new branch] {ref_name} -> {remote}/{ref_name}")
                    else:
                        self.logger.info(f"  {old_sha}..{new_sha} {ref_name} -> {remote}/{ref_name}")
            else:
                self.logger.info("Already up to date")

            return True

        except Exception as e:
            self.logger.error(f"Fetch failed: {e}")
            return False

    def _fetch_branch(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        remote: str,
        branch: str,
    ) -> Optional[Dict[str, str]]:
        """
        Fetch a single branch from the remote.

        Returns dict with ref info if updated, None if already up to date.
        """
        # Get branch info from remote
        branch_info = self.github_api.get_branch_info(owner, repo_name, branch)
        if not branch_info:
            self.logger.warning(f"Could not get info for branch '{branch}'")
            return None

        remote_commit_sha = branch_info["commit"]["sha"]

        # Check local ref
        ref_path = repo.git_dir / "refs" / "remotes" / remote / branch
        old_sha = None
        if ref_path.exists():
            old_sha = ref_path.read_text().strip()
            if old_sha == remote_commit_sha:
                # Already up to date
                return None

        # Fetch the commit and its tree
        self._fetch_commit_recursive(repo, owner, repo_name, branch, remote_commit_sha)

        # Update the remote tracking ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(f"{remote_commit_sha}\n")

        return {
            "ref": branch,
            "old_sha": old_sha or "0" * 40,
            "new_sha": remote_commit_sha,
        }

    def _fetch_commit_recursive(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        branch: str,
        commit_sha: str,
        depth: int = 0,
        max_depth: int = 100,
    ):
        """
        Recursively fetch a commit and all its objects.

        This fetches:
        - The commit object
        - The tree and all subtrees
        - All blob objects
        - Parent commits (up to max_depth)
        """
        if commit_sha in self._fetched_objects:
            return

        if depth >= max_depth:
            self.logger.warning(f"Max depth reached, stopping at commit {commit_sha[:8]}")
            return

        # Check if we already have this commit
        if self._object_exists(repo, commit_sha):
            self._fetched_objects.add(commit_sha)
            return

        # Get commit info from GitHub
        commit_info = self.github_api.get_commit_info(owner, repo_name, commit_sha)
        if not commit_info:
            self.logger.warning(f"Could not fetch commit {commit_sha[:8]}")
            return

        self._fetched_objects.add(commit_sha)

        # Fetch the tree for this commit
        tree_sha = commit_info["commit"]["tree"]["sha"]
        self._fetch_tree_recursive(repo, owner, repo_name, branch, tree_sha)

        # Create and store the commit object
        self._store_commit_from_api(repo, commit_info)

        # Fetch parent commits
        for parent in commit_info.get("parents", []):
            parent_sha = parent["sha"]
            if parent_sha not in self._fetched_objects:
                self._fetch_commit_recursive(
                    repo, owner, repo_name, branch, parent_sha, depth + 1, max_depth
                )

    def _fetch_tree_recursive(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        branch: str,
        tree_sha: str,
    ):
        """Fetch a tree and all its contents recursively."""
        if tree_sha in self._fetched_objects:
            return

        if self._object_exists(repo, tree_sha):
            self._fetched_objects.add(tree_sha)
            return

        # Get the full tree from GitHub
        tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{tree_sha}"
        tree_data = self.github_api._make_request(tree_url)

        if not tree_data:
            self.logger.warning(f"Could not fetch tree {tree_sha[:8]}")
            return

        self._fetched_objects.add(tree_sha)

        # Process tree entries
        entries = []
        for item in tree_data.get("tree", []):
            item_sha = item["sha"]
            item_mode = item["mode"]
            item_path = item["path"]
            item_type = item["type"]

            if item_type == "blob":
                # Fetch the blob if we don't have it
                if not self._object_exists(repo, item_sha):
                    content = self.github_api.get_file_content(
                        owner, repo_name, branch, item_path
                    )
                    if content is not None:
                        blob = Blob(content)
                        repo.store_object(blob)
                        self._fetched_objects.add(item_sha)

            elif item_type == "tree":
                # Recursively fetch subtrees
                self._fetch_tree_recursive(repo, owner, repo_name, branch, item_sha)

            # Add entry to tree
            entries.append(TreeEntry(int(item_mode, 8), item_path, item_sha))

        # Create and store the tree object
        tree = Tree(entries)
        repo.store_object(tree)

    def _store_commit_from_api(self, repo: Repository, commit_info: Dict[str, Any]):
        """Create and store a commit object from GitHub API data."""
        commit_data = commit_info["commit"]

        # Extract tree SHA
        tree_sha = commit_data["tree"]["sha"]

        # Extract parents
        parents = [p["sha"] for p in commit_info.get("parents", [])]

        # Extract author
        author_data = commit_data["author"]
        author = Author(
            name=author_data.get("name", "Unknown"),
            email=author_data.get("email", "unknown@unknown.com"),
        )

        # Extract committer
        committer_data = commit_data["committer"]
        committer = Author(
            name=committer_data.get("name", "Unknown"),
            email=committer_data.get("email", "unknown@unknown.com"),
        )

        # Extract message
        message = commit_data.get("message", "")

        # Create commit
        commit = Commit(
            tree_sha=tree_sha,
            parents=parents,
            author=author,
            committer=committer,
            message=message,
        )

        # Store commit
        repo.store_object(commit)

    def _object_exists(self, repo: Repository, sha: str) -> bool:
        """Check if an object exists in the repository."""
        object_path = repo.object_path(sha)
        return object_path.exists()

    def _prune_refs(
        self,
        repo: Repository,
        remote: str,
        owner: str,
        repo_name: str,
    ):
        """Remove remote-tracking refs that no longer exist on remote."""
        remote_refs_dir = repo.git_dir / "refs" / "remotes" / remote

        if not remote_refs_dir.exists():
            return

        # Get current remote branches
        remote_branches = set(self.github_api.list_branches(owner, repo_name))

        # Check local remote tracking refs
        for ref_file in remote_refs_dir.iterdir():
            if ref_file.is_file():
                branch_name = ref_file.name
                if branch_name not in remote_branches:
                    self.logger.info(f"Pruning {remote}/{branch_name}")
                    ref_file.unlink()

    def list_remote_refs(
        self,
        repo_path: str = ".",
        remote: str = "origin",
    ) -> Dict[str, str]:
        """
        List refs from a remote repository.

        Returns dict mapping ref names to their SHA1s.
        """
        try:
            repo = Repository(repo_path)
            config = Config(repo.git_dir)

            remote_config = config.get_remote(remote)
            if not remote_config or "url" not in remote_config:
                return {}

            remote_url = remote_config["url"]
            api_url, owner, repo_name = self.github_api.parse_git_url(remote_url)

            if not api_url:
                return {}

            # Get branches
            refs = {}
            branches = self.github_api.list_branches(owner, repo_name)
            for branch in branches:
                branch_info = self.github_api.get_branch_info(owner, repo_name, branch)
                if branch_info:
                    refs[f"refs/heads/{branch}"] = branch_info["commit"]["sha"]

            return refs

        except Exception as e:
            self.logger.error(f"Error listing remote refs: {e}")
            return {}


def fetch_command(
    repo_path: str = ".",
    remote: str = "origin",
    **kwargs,
) -> bool:
    """Convenience function for fetching from a remote."""
    command = FetchCommand()
    return command.fetch(repo_path, remote, **kwargs)
