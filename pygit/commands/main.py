"""
Main CLI entry point for PyGit.

This module provides the command-line interface that routes commands
to their respective implementations, mirroring Git's CLI structure.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
import pygit
from .clone import CloneCommand
from ..core.repository import Repository
from ..utils.logging import get_logger, configure_logging


class PyGitCLI:
    """Main CLI interface for PyGit."""

    def __init__(self):
        self.logger = None
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for the CLI."""
        configure_logging(level="INFO", format_type="git")
        self.logger = get_logger()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            prog="pygit", description="PyGit - A pure Python Git implementation"
        )

        parser.add_argument(
            "--version", action="version", version=f"PyGit v{pygit.__version__}"
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose output"
        )
        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress non-error output"
        )

        # Create subparsers for commands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Clone command
        self._add_clone_parser(subparsers)

        # Init command
        self._add_init_parser(subparsers)

        # Add command
        self._add_add_parser(subparsers)

        # Status command
        self._add_status_parser(subparsers)

        # Commit command
        self._add_commit_parser(subparsers)

        return parser

    def _add_clone_parser(self, subparsers):
        """Add clone command parser."""
        clone_parser = subparsers.add_parser("clone", help="Clone a repository")
        clone_parser.add_argument("repository", help="Repository URL to clone")
        clone_parser.add_argument(
            "directory", nargs="?", help="Destination directory (optional)"
        )
        clone_parser.add_argument(
            "--branch", "-b", help="Branch to clone (default: default branch)"
        )
        clone_parser.add_argument(
            "--depth", type=int, help="Create a shallow clone of given depth"
        )
        clone_parser.add_argument(
            "--bare", action="store_true", help="Create a bare repository"
        )

    def _add_init_parser(self, subparsers):
        """Add init command parser."""
        init_parser = subparsers.add_parser("init", help="Initialize a repository")
        init_parser.add_argument(
            "directory", nargs="?", help="Directory to initialize (default: current)"
        )
        init_parser.add_argument(
            "--bare", action="store_true", help="Create a bare repository"
        )

    def _add_add_parser(self, subparsers):
        """Add add command parser."""
        add_parser = subparsers.add_parser("add", help="Add files to staging area")
        add_parser.add_argument("files", nargs="+", help="Files to add to staging area")
        add_parser.add_argument(
            "--all", "-A", action="store_true", help="Add all changes"
        )

    def _add_status_parser(self, subparsers):
        """Add status command parser."""
        status_parser = subparsers.add_parser("status", help="Show working tree status")
        status_parser.add_argument(
            "--porcelain", action="store_true", help="Output in porcelain format"
        )
        status_parser.add_argument(
            "--short", action="store_true", help="Output in short format"
        )

    def _add_commit_parser(self, subparsers):
        """Add commit command parser."""
        commit_parser = subparsers.add_parser(
            "commit", help="Record changes to repository"
        )
        commit_parser.add_argument(
            "--message", "-m", required=True, help="Commit message"
        )
        commit_parser.add_argument("--author", help="Override author for commit")

    def run(self, args: List[str] = None) -> int:
        """Run the CLI with given arguments."""
        if args is None:
            args = sys.argv[1:]

        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        # Adjust logging based on verbosity
        if parsed_args.verbose:
            self.logger.set_level("DEBUG")
        elif parsed_args.quiet:
            self.logger.set_level("ERROR")

        # Route to command handlers
        if not parsed_args.command:
            parser.print_help()
            return 1

        try:
            handler = getattr(self, f"_handle_{parsed_args.command}")
            return handler(parsed_args)
        except AttributeError:
            self.logger.error(f"Unknown command: {parsed_args.command}")
            return 1
        except Exception as e:
            self.logger.error(f"Error executing {parsed_args.command}: {e}")
            return 1

    def _handle_clone(self, args) -> int:
        """Handle clone command."""
        self.logger.info(f"Cloning {args.repository}")

        clone_cmd = CloneCommand()

        kwargs = {
            "branch": args.branch,
            "bare": args.bare,
        }

        # Handle shallow clone if depth is specified
        if args.depth:
            kwargs["shallow"] = True
            kwargs["depth"] = args.depth

        success = clone_cmd.clone(args.repository, args.directory, **kwargs)

        if success:
            self.logger.info("Clone completed successfully")
            return 0
        else:
            self.logger.error("Clone failed")
            return 1

    def _handle_init(self, args) -> int:
        """Handle init command."""
        directory = args.directory or "."

        try:
            repo = Repository.init(directory)
            self.logger.info(f"Initialized empty Git repository in {repo.git_dir}")
            return 0
        except Exception as e:
            self.logger.error(f"Failed to initialize repository: {e}")
            return 1

    def _handle_add(self, args) -> int:
        """Handle add command."""
        try:
            repo = Repository()
            from ..core.index import Index
            from ..core.ignore import GitIgnore

            index = Index(repo)
            ignore_manager = GitIgnore(repo.path)

            if args.all:
                # Add all changes (respecting .gitignore)
                added_files = 0
                for file_path in repo.path.rglob("*"):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(repo.path))

                        # Skip ignored files
                        if ignore_manager.is_ignored(rel_path, False):
                            continue

                        if index.add(rel_path):
                            added_files += 1

                self.logger.info(f"Added {added_files} files to staging area")
            else:
                # Add specified files
                for file_path in args.files:
                    path_obj = Path(file_path)

                    # Handle relative paths
                    if not path_obj.is_absolute():
                        path_obj = repo.path / path_obj

                    rel_path = str(path_obj.relative_to(repo.path))

                    # Check if file is ignored
                    if ignore_manager.is_ignored(rel_path, False):
                        self.logger.warning(f"Ignoring ignored file: {file_path}")
                        continue

                    if index.add(rel_path):
                        self.logger.info(f"Added {file_path} to staging area")
                    else:
                        self.logger.error(f"Failed to add {file_path}")
                        return 1

            index.save()
            return 0

        except Exception as e:
            self.logger.error(f"Failed to add files: {e}")
            return 1

            index.save()
            return 0

        except Exception as e:
            self.logger.error(f"Failed to add files: {e}")
            return 1

    def _handle_status(self, args) -> int:
        """Handle status command."""
        try:
            repo = Repository()
            from ..core.index import Index
            from ..core.ignore import GitIgnore

            index = Index(repo)
            ignore_manager = GitIgnore(repo.path)

            modified_files = index.get_modified_files()

            # Get untracked files
            all_files = []
            for file_path in repo.path.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(repo.path))
                    # Skip git directory and ignored files
                    if rel_path.startswith(".git") or ignore_manager.is_ignored(
                        rel_path, False
                    ):
                        continue
                    all_files.append(rel_path)

            tracked_files = set(index.entries.keys())
            untracked_files = [f for f in all_files if f not in tracked_files]

            has_changes = modified_files or untracked_files

            if not has_changes and not args.porcelain and not args.short:
                self.logger.info("Working tree clean")
                return 0

            if args.porcelain:
                for path, status in modified_files.items():
                    status_char = "M" if status == "modified" else "D"
                    print(f"{status_char} {path}")
                for path in untracked_files:
                    print(f"?? {path}")
            elif args.short:
                for path, status in modified_files.items():
                    status_word = "modified:" if status == "modified" else "deleted:"
                    print(f" {status_word} {path}")
                for path in untracked_files:
                    print(f" untracked: {path}")
            else:
                if modified_files:
                    print("Changes not staged for commit:")
                    for path, status in modified_files.items():
                        status_word = "modified" if status == "modified" else "deleted"
                        print(f"\t{status_word}: {path}")
                    print()

                if untracked_files:
                    print("Untracked files:")
                    for path in sorted(untracked_files):
                        print(f"\t{path}")
                    print()

                if not has_changes:
                    print("No changes to commit")

            return 0

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return 1

    def _handle_commit(self, args) -> int:
        """Handle commit command."""
        try:
            repo = Repository()
            from ..core.index import Index
            from ..core.objects import Commit, Author
            from ..core.config import Config

            index = Index(repo)

            if len(index) == 0:
                self.logger.error("No changes added to commit")
                return 1

            # Create tree from index
            tree_sha1 = index.write_tree()

            # Get commit info
            config = Config(repo.git_dir)
            user_info = config.get_user_info()

            if not user_info["name"] or not user_info["email"]:
                self.logger.error("Please configure user.name and user.email")
                return 1

            # Parse author override if provided
            author = Author(user_info["name"], user_info["email"])
            if args.author:
                # Parse author format: "Name <email>"
                if "<" in args.author and ">" in args.author:
                    name = args.author[: args.author.index("<")].strip()
                    email = args.author[
                        args.author.index("<") + 1 : args.author.index(">")
                    ].strip()
                    author = Author(name, email)
                else:
                    author.name = args.author

            # Get parent commit
            head_sha1 = repo.get_head()
            parents = [head_sha1] if head_sha1 else []

            # Create commit
            commit = Commit(
                tree_sha1=tree_sha1,
                parents=parents,
                author=author,
                committer=author,
                message=args.message,
            )

            # Store commit
            commit_sha1 = repo.store_object(commit)

            # Update HEAD
            repo.set_head(commit_sha1)

            self.logger.info(f"Committed {commit_sha1}")
            return 0

        except Exception as e:
            self.logger.error(f"Failed to create commit: {e}")
            return 1


def main() -> int:
    """Main entry point for the CLI."""
    cli = PyGitCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
