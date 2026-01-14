"""
Clone command implementation.

This module provides the enhanced clone functionality that creates
a proper Git repository with full repository state and metadata.
"""

import os
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from ..core.repository import Repository
from ..core.index import Index
from ..core.github import GitHubAPI
from ..core.objects import Tree, TreeEntry, Blob
from ..utils.logging import get_logger
from ..utils.http import HTTPClient


class CloneCommand:
    """Enhanced clone command with full repository state support."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        self.github_api = GitHubAPI(github_token)
        self.http_client = HTTPClient(progress_callback)
        self.logger = get_logger()

    def clone(
        self,
        url: str,
        destination: Optional[str] = None,
        branch: Optional[str] = None,
        shallow: bool = False,
        bare: bool = False,
    ) -> bool:
        """Clone a repository with enhanced functionality."""

        # Parse the URL
        api_url, owner, repo = self.github_api.parse_git_url(url)

        if not api_url:
            self.logger.error("Currently only GitHub repositories are supported")
            return False

        # Set destination directory
        if destination is None:
            destination = repo

        dest_path = Path(destination).resolve()

        # Check if destination exists
        if dest_path.exists():
            self.logger.error(f"Destination '{dest_path}' already exists")
            return False

        self.logger.operation(
            "clone_start", {"url": url, "destination": str(dest_path)}
        )

        # Get repository information
        repo_info = self.github_api.get_repo_info(api_url)
        if not repo_info:
            self.logger.error("Could not retrieve repository information")
            return False

        # Determine branch to clone
        if branch is None:
            branch = self.github_api.get_default_branch(api_url)

        self.logger.info(f"Cloning {owner}/{repo} branch '{branch}' into {dest_path}")

        # Create repository structure
        if bare:
            repo_obj = Repository.init(str(dest_path))
            repo_obj.git_dir = dest_path  # For bare repos, .git is the repo itself
        else:
            repo_obj = Repository.init(str(dest_path))

        try:
            # Download and process repository contents
            success = self._download_repository_contents(
                owner, repo, branch, dest_path, repo_obj, bare
            )

            if not success:
                self.logger.error("Failed to download repository contents")
                return False

            # Set up HEAD and default branch
            self._setup_branches(repo_obj, owner, repo, branch, bare)

            # Store repository metadata
            self._store_repository_metadata(repo_obj, repo_info, url, bare)

            self.logger.operation(
                "clone_complete",
                {
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                    "files": len(self._count_downloaded_files(owner, repo, branch)),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Error during clone: {e}")
            return False

    def _download_repository_contents(
        self,
        owner: str,
        repo: str,
        branch: str,
        dest_path: Path,
        repo_obj: Repository,
        bare: bool,
    ) -> bool:
        """Download and store repository contents."""

        # Get the complete file tree
        tree = self.github_api.get_tree_recursive(owner, repo, branch)

        if not tree:
            self.logger.error("Could not retrieve repository tree")
            return False

        # Process tree items
        files = [item for item in tree if item["type"] == "blob"]
        directories = [item for item in tree if item["type"] == "tree"]

        self.logger.progress(f"Processing repository", 0, len(tree))

        # Create directories (for non-bare repos)
        if not bare:
            for item in directories:
                dir_path = dest_path / item["path"]
                dir_path.mkdir(parents=True, exist_ok=True)

        # Download and store files as Git objects
        index = Index(repo_obj) if not bare else None

        for i, item in enumerate(files):
            if item["type"] == "blob":
                # Download file content
                content = self.github_api.get_file_content(
                    owner, repo, branch, item["path"]
                )

                if content is None:
                    self.logger.warning(f"Could not download file: {item['path']}")
                    continue

                # Create and store blob object
                blob = Blob(content)
                blob_sha1 = repo_obj.store_object(blob)

                # Add to index for non-bare repos
                if index and not bare:
                    # Write file to working directory
                    file_path = dest_path / item["path"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)

                    # Add to index
                    index.add(item["path"], dest_path)

                # Progress update
                if i % 50 == 0 or i == len(files) - 1:
                    self.logger.progress(f"Downloading files", i + 1, len(files))

        # Save index for non-bare repos
        if index and not bare:
            index.save()

        return True

    def _setup_branches(
        self, repo_obj: Repository, owner: str, repo: str, branch: str, bare: bool
    ):
        """Set up branch references and HEAD."""

        # Get branch information to get the commit SHA1
        branch_info = self.github_api.get_branch_info(owner, repo, branch)

        if branch_info and "commit" in branch_info:
            commit_sha1 = branch_info["commit"]["sha"]

            # Create branch reference
            if not bare:
                branch_ref_path = repo_obj.git_dir / "refs" / "heads" / branch
            else:
                branch_ref_path = repo_obj.git_dir / "refs" / "heads" / branch

            branch_ref_path.parent.mkdir(parents=True, exist_ok=True)
            branch_ref_path.write_text(f"{commit_sha1}\n")

            # Set HEAD to point to the branch
            if not bare:
                repo_obj.set_head(f"refs/heads/{branch}")
            else:
                # For bare repos, HEAD can point directly to a branch
                head_file = repo_obj.git_dir / "HEAD"
                head_file.write_text(f"ref: refs/heads/{branch}\n")

    def _store_repository_metadata(
        self,
        repo_obj: Repository,
        repo_info: Dict[str, Any],
        original_url: str,
        bare: bool,
    ):
        """Store repository metadata in config."""

        from ..core.config import Config

        config = Config(repo_obj.git_dir)

        # Set core repository info
        config.set("core", "repositoryformatversion", "0", "local")
        config.set("core", "filemode", "true", "local")
        config.set("core", "bare", str(bare).lower(), "local")
        config.set("core", "logallrefupdates", "true", "local")

        # Set remote origin
        clone_url = repo_info.get("clone_url", original_url)
        config.set_remote(
            "origin", clone_url, "+refs/heads/*:refs/remotes/origin/*", "local"
        )

        # Set up default branch tracking
        default_branch = repo_info.get("default_branch", "main")
        config.set_branch(
            default_branch, "origin", f"refs/heads/{default_branch}", "local"
        )

        # Store repository description
        if "description" in repo_info:
            (repo_obj.git_dir / "description").write_text(
                repo_info["description"] + "\n"
            )

    def _count_downloaded_files(self, owner: str, repo: str, branch: str) -> int:
        """Count the number of files that will be downloaded."""
        tree = self.github_api.get_tree_recursive(owner, repo, branch)
        return len([item for item in tree if item["type"] == "blob"])

    def list_remote_branches(self, url: str) -> Dict[str, str]:
        """List available branches in a remote repository."""
        api_url, owner, repo = self.github_api.parse_git_url(url)

        if not api_url:
            return {}

        branches = self.github_api.list_branches(owner, repo)
        return {branch: f"refs/heads/{branch}" for branch in branches}


def clone_command(url: str, destination: Optional[str] = None, **kwargs) -> bool:
    """Convenience function for cloning a repository."""
    command = CloneCommand()
    return command.clone(url, destination, **kwargs)
