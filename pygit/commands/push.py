"""
Push command implementation.

This module provides the push functionality that uploads local commits
to a remote repository via the GitHub API.
"""

from pathlib import Path
from typing import Optional, Dict, List, Set, Any
from ..core.repository import Repository
from ..core.config import Config
from ..core.github import GitHubAPI
from ..utils.logging import get_logger


class PushCommand:
    """Push command to upload commits to remote."""

    def __init__(self, github_token: Optional[str] = None):
        self.github_api = GitHubAPI(github_token)
        self.logger = get_logger()
        self._pushed_objects: Set[str] = set()

    def push(
        self,
        repo_path: str = ".",
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        set_upstream: bool = False,
        dry_run: bool = False,
        all_branches: bool = False,
    ) -> bool:
        """
        Push commits to a remote repository.

        Args:
            repo_path: Path to the local repository
            remote: Name of the remote (default: origin)
            branch: Branch to push (default: current branch)
            force: Force push even if not fast-forward
            set_upstream: Set upstream tracking for the branch
            dry_run: Show what would be pushed without pushing
            all_branches: Push all branches

        Returns:
            True if push was successful, False otherwise
        """
        if not self.github_api.token:
            self.logger.error(
                "GitHub token required for push. "
                "Set GITHUB_TOKEN environment variable or use --token option."
            )
            return False

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

            # Parse the URL to get owner/repo
            api_url, owner, repo_name = self.github_api.parse_git_url(remote_url)
            if not api_url:
                self.logger.error("Currently only GitHub repositories are supported")
                return False

            # Determine branch to push
            if branch is None:
                branch = self._get_current_branch(repo)
                if not branch:
                    self.logger.error("Not on any branch (detached HEAD)")
                    return False

            self.logger.info(f"Pushing to {remote}/{branch}")

            # Get local commit SHA
            local_sha = self._get_branch_sha(repo, branch)
            if not local_sha:
                self.logger.error(f"Branch '{branch}' has no commits")
                return False

            # Get remote commit SHA
            remote_sha = self.github_api.get_ref(owner, repo_name, f"heads/{branch}")

            if remote_sha == local_sha:
                self.logger.info("Everything up-to-date")
                return True

            # Check if this is a fast-forward push
            if remote_sha and not force:
                if not self._is_ancestor(repo, remote_sha, local_sha):
                    self.logger.error(
                        "Updates were rejected because the remote contains work "
                        "that you do not have locally. Use --force to override."
                    )
                    return False

            # Collect commits to push
            commits_to_push = self._get_commits_to_push(repo, local_sha, remote_sha)

            if not commits_to_push:
                self.logger.info("Everything up-to-date")
                return True

            self.logger.info(f"Pushing {len(commits_to_push)} commit(s)")

            if dry_run:
                self.logger.info("Dry run - would push:")
                for commit_sha in commits_to_push:
                    commit_obj = repo.get_object(commit_sha)
                    if commit_obj:
                        msg = commit_obj.get("message", "").split("\n")[0][:50]
                        self.logger.info(f"  {commit_sha[:8]} {msg}")
                return True

            # Push commits in order (oldest first)
            for i, commit_sha in enumerate(reversed(commits_to_push)):
                self.logger.progress(f"Pushing commits", i + 1, len(commits_to_push))

                success = self._push_commit(
                    repo, owner, repo_name, commit_sha, remote_sha
                )
                if not success:
                    self.logger.error(f"Failed to push commit {commit_sha[:8]}")
                    return False

                # Update remote_sha for next commit's parent
                remote_sha = commit_sha

            # Update the remote ref
            if remote_sha:
                # Update existing ref
                success = self.github_api.update_ref(
                    owner, repo_name, f"heads/{branch}", local_sha, force
                )
            else:
                # Create new ref
                success = self.github_api.create_ref(
                    owner, repo_name, f"refs/heads/{branch}", local_sha
                )

            if not success:
                self.logger.error("Failed to update remote ref")
                return False

            # Update local remote tracking ref
            remote_ref_path = repo.git_dir / "refs" / "remotes" / remote / branch
            remote_ref_path.parent.mkdir(parents=True, exist_ok=True)
            remote_ref_path.write_text(f"{local_sha}\n")

            # Set upstream if requested
            if set_upstream:
                config.set_branch(branch, remote, f"refs/heads/{branch}")

            self.logger.info(f"Pushed to {remote}/{branch}")
            self.logger.info(f"  {(remote_sha or '0'*40)[:8]}..{local_sha[:8]}")

            return True

        except Exception as e:
            self.logger.error(f"Push failed: {e}")
            return False

    def _get_current_branch(self, repo: Repository) -> Optional[str]:
        """Get the name of the current branch."""
        head_file = repo.git_dir / "HEAD"
        if not head_file.exists():
            return None

        head_content = head_file.read_text().strip()

        if head_content.startswith("ref: refs/heads/"):
            return head_content[16:]

        return None

    def _get_branch_sha(self, repo: Repository, branch: str) -> Optional[str]:
        """Get the SHA of a branch."""
        branch_ref = repo.git_dir / "refs" / "heads" / branch
        if branch_ref.exists():
            return branch_ref.read_text().strip()
        return None

    def _is_ancestor(
        self, repo: Repository, ancestor_sha: str, descendant_sha: str
    ) -> bool:
        """Check if ancestor_sha is an ancestor of descendant_sha."""
        visited = set()
        to_check = [descendant_sha]

        while to_check:
            sha = to_check.pop(0)

            if sha in visited:
                continue
            visited.add(sha)

            if sha == ancestor_sha:
                return True

            try:
                obj = repo.get_object(sha)
                if obj and obj.get("type") == "commit":
                    parents = obj.get("parents", [])
                    to_check.extend(parents)
            except Exception:
                pass

            if len(visited) > 1000:
                break

        return False

    def _get_commits_to_push(
        self, repo: Repository, local_sha: str, remote_sha: Optional[str]
    ) -> List[str]:
        """Get list of commits that need to be pushed."""
        commits = []
        visited = set()

        if remote_sha:
            # Find all commits reachable from remote
            remote_commits = self._get_all_ancestors(repo, remote_sha)
        else:
            remote_commits = set()

        # Walk from local, collecting commits not in remote
        to_check = [local_sha]

        while to_check:
            sha = to_check.pop(0)

            if sha in visited or sha in remote_commits:
                continue
            visited.add(sha)

            commits.append(sha)

            try:
                obj = repo.get_object(sha)
                if obj and obj.get("type") == "commit":
                    parents = obj.get("parents", [])
                    to_check.extend(parents)
            except Exception:
                pass

        return commits

    def _get_all_ancestors(self, repo: Repository, sha: str) -> Set[str]:
        """Get all ancestor commits of a SHA."""
        ancestors = set()
        to_check = [sha]

        while to_check:
            current = to_check.pop(0)

            if current in ancestors:
                continue
            ancestors.add(current)

            try:
                obj = repo.get_object(current)
                if obj and obj.get("type") == "commit":
                    parents = obj.get("parents", [])
                    to_check.extend(parents)
            except Exception:
                pass

            if len(ancestors) > 10000:
                break

        return ancestors

    def _push_commit(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        commit_sha: str,
        remote_parent_sha: Optional[str],
    ) -> bool:
        """Push a single commit to GitHub."""
        try:
            # Get commit object
            commit_obj = repo.get_object(commit_sha)
            if not commit_obj or commit_obj.get("type") != "commit":
                self.logger.error(f"Invalid commit: {commit_sha}")
                return False

            tree_sha = commit_obj.get("tree")
            message = commit_obj.get("message", "")
            author_info = commit_obj.get("author", {})
            committer_info = commit_obj.get("committer", {})
            local_parents = commit_obj.get("parents", [])

            # Push the tree (and all blobs)
            remote_tree_sha = self._push_tree(repo, owner, repo_name, tree_sha)
            if not remote_tree_sha:
                self.logger.error("Failed to push tree")
                return False

            # Determine parent for remote commit
            if local_parents and remote_parent_sha:
                remote_parents = [remote_parent_sha]
            elif local_parents:
                # First commit being pushed - try to use the local parent
                # This assumes the parent already exists on remote
                remote_parents = local_parents
            else:
                remote_parents = []

            # Create commit on GitHub
            author = None
            if author_info:
                author = {
                    "name": author_info.get("name", "Unknown"),
                    "email": author_info.get("email", "unknown@unknown.com"),
                }

            committer = None
            if committer_info:
                committer = {
                    "name": committer_info.get("name", "Unknown"),
                    "email": committer_info.get("email", "unknown@unknown.com"),
                }

            remote_commit_sha = self.github_api.create_commit(
                owner, repo_name, message, remote_tree_sha,
                remote_parents, author, committer
            )

            if not remote_commit_sha:
                self.logger.error("Failed to create commit on GitHub")
                return False

            self._pushed_objects.add(commit_sha)
            return True

        except Exception as e:
            self.logger.error(f"Error pushing commit: {e}")
            return False

    def _push_tree(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        tree_sha: str,
    ) -> Optional[str]:
        """Push a tree and all its contents to GitHub."""
        if tree_sha in self._pushed_objects:
            return tree_sha

        try:
            tree_obj = repo.get_object(tree_sha)
            if not tree_obj or tree_obj.get("type") != "tree":
                return None

            tree_items = []

            for entry in tree_obj.get("entries", []):
                entry_name = entry.get("name", "")
                entry_sha = entry.get("sha1", "")
                entry_mode = entry.get("mode", "100644")

                # Normalize mode to string
                if isinstance(entry_mode, int):
                    entry_mode = format(entry_mode, "o")
                entry_mode = entry_mode.lstrip("0") or "100644"

                if entry_mode.startswith("40"):  # Directory
                    # Recursively push subtree
                    remote_sha = self._push_tree(repo, owner, repo_name, entry_sha)
                    if not remote_sha:
                        return None
                    tree_items.append({
                        "path": entry_name,
                        "mode": entry_mode,
                        "type": "tree",
                        "sha": remote_sha
                    })
                else:  # Blob
                    # Push blob
                    remote_sha = self._push_blob(repo, owner, repo_name, entry_sha)
                    if not remote_sha:
                        return None
                    tree_items.append({
                        "path": entry_name,
                        "mode": entry_mode,
                        "type": "blob",
                        "sha": remote_sha
                    })

            # Create tree on GitHub
            remote_tree_sha = self.github_api.create_tree(
                owner, repo_name, tree_items
            )

            if remote_tree_sha:
                self._pushed_objects.add(tree_sha)

            return remote_tree_sha

        except Exception as e:
            self.logger.error(f"Error pushing tree: {e}")
            return None

    def _push_blob(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        blob_sha: str,
    ) -> Optional[str]:
        """Push a blob to GitHub."""
        if blob_sha in self._pushed_objects:
            return blob_sha

        try:
            blob_obj = repo.get_object(blob_sha)
            if not blob_obj or blob_obj.get("type") != "blob":
                return None

            content = blob_obj.get("data", b"")

            # Create blob on GitHub
            remote_sha = self.github_api.create_blob(
                owner, repo_name, content, "base64"
            )

            if remote_sha:
                self._pushed_objects.add(blob_sha)

            return remote_sha

        except Exception as e:
            self.logger.error(f"Error pushing blob: {e}")
            return None


def push_command(
    repo_path: str = ".",
    remote: str = "origin",
    **kwargs,
) -> bool:
    """Convenience function for pushing to a remote."""
    command = PushCommand()
    return command.push(repo_path, remote, **kwargs)
