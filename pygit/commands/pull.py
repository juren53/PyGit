"""
Pull command implementation.

This module provides the pull functionality that fetches from a remote
and merges changes into the current branch.
"""

from pathlib import Path
from typing import Optional, Dict, List, Set, Any
from ..core.repository import Repository
from ..core.config import Config
from ..core.index import Index
from ..core.objects import Blob, Tree, Commit
from ..utils.logging import get_logger
from .fetch import FetchCommand


class PullCommand:
    """Pull command to fetch and merge from remote."""

    def __init__(self, github_token: Optional[str] = None):
        self.fetch_cmd = FetchCommand(github_token)
        self.logger = get_logger()

    def pull(
        self,
        repo_path: str = ".",
        remote: str = "origin",
        branch: Optional[str] = None,
        ff_only: bool = False,
        no_ff: bool = False,
        rebase: bool = False,
    ) -> bool:
        """
        Pull changes from a remote repository.

        Args:
            repo_path: Path to the local repository
            remote: Name of the remote (default: origin)
            branch: Remote branch to pull (default: tracking branch)
            ff_only: Only allow fast-forward merges
            no_ff: Create a merge commit even for fast-forward
            rebase: Rebase instead of merge (not yet implemented)

        Returns:
            True if pull was successful, False otherwise
        """
        if rebase:
            self.logger.error("Rebase is not yet implemented")
            return False

        try:
            # Open the repository
            repo = Repository(repo_path)
            config = Config(repo.git_dir)

            # Get current branch
            current_branch = self._get_current_branch(repo)
            if not current_branch:
                self.logger.error("Not on any branch (detached HEAD)")
                return False

            self.logger.info(f"Pulling into branch '{current_branch}'")

            # Determine remote branch to pull from
            if branch is None:
                branch = self._get_tracking_branch(config, current_branch, remote)
                if not branch:
                    self.logger.error(
                        f"No tracking branch configured for '{current_branch}'. "
                        f"Specify a branch: pygit pull {remote} <branch>"
                    )
                    return False

            self.logger.info(f"Fetching {remote}/{branch}")

            # Step 1: Fetch from remote
            fetch_success = self.fetch_cmd.fetch(
                repo_path=repo_path,
                remote=remote,
                branch=branch,
            )

            if not fetch_success:
                self.logger.error("Fetch failed")
                return False

            # Step 2: Get the remote ref
            remote_ref_path = repo.git_dir / "refs" / "remotes" / remote / branch
            if not remote_ref_path.exists():
                self.logger.error(f"Remote ref {remote}/{branch} not found")
                return False

            remote_sha = remote_ref_path.read_text().strip()

            # Step 3: Get current HEAD
            local_sha = repo.get_head()

            if local_sha == remote_sha:
                self.logger.info("Already up to date")
                return True

            # Step 4: Determine merge strategy
            if local_sha is None:
                # No local commits yet - just update HEAD
                self.logger.info("Setting HEAD to remote branch")
                return self._update_head_and_checkout(repo, remote_sha, current_branch)

            # Check if fast-forward is possible
            can_ff = self._can_fast_forward(repo, local_sha, remote_sha)

            if can_ff:
                if no_ff:
                    # Create merge commit even though ff is possible
                    return self._create_merge_commit(
                        repo, config, local_sha, remote_sha,
                        current_branch, remote, branch
                    )
                else:
                    # Fast-forward merge
                    self.logger.info(f"Fast-forward merge {local_sha[:8]}..{remote_sha[:8]}")
                    return self._fast_forward_merge(repo, remote_sha, current_branch)
            else:
                if ff_only:
                    self.logger.error(
                        "Cannot fast-forward. Use 'pygit pull' without --ff-only "
                        "or resolve divergent branches manually."
                    )
                    return False

                # Need a real merge
                self.logger.warning(
                    "Branches have diverged. Full merge not yet implemented. "
                    "Consider using 'git merge' or rebasing manually."
                )
                return False

        except Exception as e:
            self.logger.error(f"Pull failed: {e}")
            return False

    def _get_current_branch(self, repo: Repository) -> Optional[str]:
        """Get the name of the current branch."""
        head_file = repo.git_dir / "HEAD"
        if not head_file.exists():
            return None

        head_content = head_file.read_text().strip()

        # Check if HEAD is a symbolic ref
        if head_content.startswith("ref: refs/heads/"):
            return head_content[16:]  # Remove "ref: refs/heads/"
        elif head_content.startswith("ref: "):
            # Other ref format
            ref = head_content[5:]
            if ref.startswith("refs/heads/"):
                return ref[11:]
            return None

        # Detached HEAD (direct SHA)
        return None

    def _get_tracking_branch(
        self, config: Config, local_branch: str, default_remote: str
    ) -> Optional[str]:
        """Get the tracking branch for a local branch."""
        branch_config = config.get_branch(local_branch)

        if branch_config:
            remote = branch_config.get("remote", default_remote)
            merge = branch_config.get("merge", "")

            if merge.startswith("refs/heads/"):
                return merge[11:]  # Remove refs/heads/
            elif merge:
                return merge

        # Default to same name as local branch
        return local_branch

    def _can_fast_forward(
        self, repo: Repository, local_sha: str, remote_sha: str
    ) -> bool:
        """
        Check if we can fast-forward from local to remote.

        Fast-forward is possible if local_sha is an ancestor of remote_sha.
        """
        # Walk back from remote to find local
        visited = set()
        to_check = [remote_sha]

        while to_check:
            sha = to_check.pop(0)

            if sha in visited:
                continue
            visited.add(sha)

            if sha == local_sha:
                return True

            # Get parent commits
            try:
                obj = repo.get_object(sha)
                if obj and obj.get("type") == "commit":
                    parents = obj.get("parents", [])
                    to_check.extend(parents)
            except Exception:
                pass

            # Limit search depth to avoid infinite loops
            if len(visited) > 1000:
                break

        return False

    def _fast_forward_merge(
        self, repo: Repository, target_sha: str, branch: str
    ) -> bool:
        """Perform a fast-forward merge."""
        return self._update_head_and_checkout(repo, target_sha, branch)

    def _update_head_and_checkout(
        self, repo: Repository, target_sha: str, branch: str
    ) -> bool:
        """Update HEAD and checkout files from target commit."""
        try:
            # Update the branch ref
            branch_ref_path = repo.git_dir / "refs" / "heads" / branch
            branch_ref_path.parent.mkdir(parents=True, exist_ok=True)
            branch_ref_path.write_text(f"{target_sha}\n")

            # Update HEAD to point to branch
            head_file = repo.git_dir / "HEAD"
            head_file.write_text(f"ref: refs/heads/{branch}\n")

            # Checkout the tree
            success = self._checkout_tree(repo, target_sha)

            if success:
                self.logger.info(f"Updated to {target_sha[:8]}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to update HEAD: {e}")
            return False

    def _checkout_tree(self, repo: Repository, commit_sha: str) -> bool:
        """
        Checkout the tree from a commit to the working directory.

        This updates the working directory to match the commit's tree.
        """
        try:
            # Get the commit
            commit_obj = repo.get_object(commit_sha)
            if not commit_obj or commit_obj.get("type") != "commit":
                self.logger.error(f"Invalid commit: {commit_sha}")
                return False

            tree_sha = commit_obj.get("tree")
            if not tree_sha:
                self.logger.error("Commit has no tree")
                return False

            # Get files from tree
            files = self._get_tree_files(repo, tree_sha, "")

            # Update working directory
            for file_path, blob_sha in files.items():
                self._checkout_file(repo, file_path, blob_sha)

            # Update index
            index = Index(repo)
            index.clear()
            for file_path, blob_sha in files.items():
                full_path = repo.path / file_path
                if full_path.exists():
                    index.add(file_path, repo.path)
            index.save()

            self.logger.info(f"Checked out {len(files)} files")
            return True

        except Exception as e:
            self.logger.error(f"Checkout failed: {e}")
            return False

    def _get_tree_files(
        self, repo: Repository, tree_sha: str, prefix: str
    ) -> Dict[str, str]:
        """Recursively get all files from a tree."""
        files = {}

        tree_obj = repo.get_object(tree_sha)
        if not tree_obj or tree_obj.get("type") != "tree":
            return files

        for entry in tree_obj.get("entries", []):
            entry_name = entry.get("name", "")
            entry_sha = entry.get("sha1", "")
            entry_mode = entry.get("mode", "")

            if prefix:
                full_path = f"{prefix}/{entry_name}"
            else:
                full_path = entry_name

            # Check if it's a directory (tree) or file (blob)
            if entry_mode.startswith("40"):  # Directory
                # Recursively get files from subtree
                subfiles = self._get_tree_files(repo, entry_sha, full_path)
                files.update(subfiles)
            else:  # File
                files[full_path] = entry_sha

        return files

    def _checkout_file(
        self, repo: Repository, file_path: str, blob_sha: str
    ) -> bool:
        """Checkout a single file from the object store."""
        try:
            blob_obj = repo.get_object(blob_sha)
            if not blob_obj or blob_obj.get("type") != "blob":
                return False

            content = blob_obj.get("data", b"")

            full_path = repo.path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)

            return True

        except Exception as e:
            self.logger.warning(f"Failed to checkout {file_path}: {e}")
            return False

    def _create_merge_commit(
        self,
        repo: Repository,
        config: Config,
        local_sha: str,
        remote_sha: str,
        local_branch: str,
        remote_name: str,
        remote_branch: str,
    ) -> bool:
        """Create a merge commit (for --no-ff merges)."""
        self.logger.error("Merge commits (--no-ff) not yet implemented")
        return False


def pull_command(
    repo_path: str = ".",
    remote: str = "origin",
    **kwargs,
) -> bool:
    """Convenience function for pulling from a remote."""
    command = PullCommand()
    return command.pull(repo_path, remote, **kwargs)
