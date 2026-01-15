"""
Unit tests for the fetch command.

Tests cover remote ref fetching, object downloading, and CLI integration.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pygit.commands.fetch import FetchCommand, fetch_command
from pygit.core.repository import Repository
from pygit.core.config import Config


class TestFetchCommandCreation:
    """Tests for FetchCommand instantiation."""

    def test_fetch_command_creation(self):
        """Test that FetchCommand can be created."""
        cmd = FetchCommand()
        assert cmd is not None
        assert cmd.github_api is not None
        assert cmd.logger is not None

    def test_fetch_command_with_token(self):
        """Test FetchCommand with GitHub token."""
        cmd = FetchCommand(github_token="test_token")
        assert cmd.github_api.token == "test_token"

    def test_fetch_command_with_progress_callback(self):
        """Test FetchCommand with progress callback."""
        callback = Mock()
        cmd = FetchCommand(progress_callback=callback)
        assert cmd.progress_callback == callback


class TestFetchRemoteConfig:
    """Tests for remote configuration handling."""

    def test_fetch_no_remote_configured(self):
        """Test fetch fails when remote is not configured."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            cmd = FetchCommand()

            success = cmd.fetch(repo_path=tmp, remote="origin")

            assert success is False

    def test_fetch_with_remote_configured(self):
        """Test fetch with properly configured remote."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)

            # Configure remote
            config.set_remote("origin", "https://github.com/test/repo.git")

            cmd = FetchCommand()

            # Mock the GitHub API calls
            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'get_default_branch') as mock_branch:
                    mock_branch.return_value = "main"

                    with patch.object(cmd.github_api, 'get_branch_info') as mock_info:
                        mock_info.return_value = {
                            "name": "main",
                            "commit": {"sha": "abc123" * 7}
                        }

                        with patch.object(cmd, '_fetch_branch') as mock_fetch:
                            mock_fetch.return_value = None  # Already up to date

                            success = cmd.fetch(repo_path=tmp, remote="origin")

                            assert success is True
                            mock_parse.assert_called_once()


class TestFetchBranch:
    """Tests for branch fetching logic."""

    def test_fetch_specific_branch(self):
        """Test fetching a specific branch."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            cmd = FetchCommand()

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd, '_fetch_branch') as mock_fetch:
                    mock_fetch.return_value = {
                        "ref": "develop",
                        "old_sha": "0" * 40,
                        "new_sha": "abc123" * 7,
                    }

                    success = cmd.fetch(
                        repo_path=tmp,
                        remote="origin",
                        branch="develop"
                    )

                    assert success is True
                    mock_fetch.assert_called_once()

    def test_fetch_all_branches(self):
        """Test fetching all branches."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            cmd = FetchCommand()

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'list_branches') as mock_list:
                    mock_list.return_value = ["main", "develop", "feature"]

                    with patch.object(cmd, '_fetch_branch') as mock_fetch:
                        mock_fetch.return_value = None

                        success = cmd.fetch(
                            repo_path=tmp,
                            remote="origin",
                            all_branches=True
                        )

                        assert success is True
                        assert mock_fetch.call_count == 3


class TestFetchDryRun:
    """Tests for dry-run functionality."""

    def test_fetch_dry_run_no_changes(self):
        """Test dry-run mode doesn't make changes."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            cmd = FetchCommand()

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'get_default_branch') as mock_branch:
                    mock_branch.return_value = "main"

                    with patch.object(cmd.github_api, 'get_branch_info') as mock_info:
                        mock_info.return_value = {
                            "name": "main",
                            "commit": {"sha": "abc123" * 7}
                        }

                        success = cmd.fetch(
                            repo_path=tmp,
                            remote="origin",
                            dry_run=True
                        )

                        assert success is True

                        # Verify no refs were created
                        refs_dir = repo.git_dir / "refs" / "remotes" / "origin"
                        assert not refs_dir.exists()


class TestFetchObjectExists:
    """Tests for object existence checking."""

    def test_object_exists_true(self):
        """Test _object_exists returns True for existing object."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Create a fake object file (valid 40-char SHA)
            sha = "a" * 40
            object_dir = repo.git_dir / "objects" / sha[:2]
            object_dir.mkdir(parents=True)
            (object_dir / sha[2:]).write_bytes(b"fake object")

            cmd = FetchCommand()
            assert cmd._object_exists(repo, sha) is True

    def test_object_exists_false(self):
        """Test _object_exists returns False for missing object."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = FetchCommand()
            # Valid 40-char SHA that doesn't exist
            assert cmd._object_exists(repo, "b" * 40) is False


class TestFetchPrune:
    """Tests for prune functionality."""

    def test_prune_removes_stale_refs(self):
        """Test that prune removes refs not on remote."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            # Create stale remote ref
            refs_dir = repo.git_dir / "refs" / "remotes" / "origin"
            refs_dir.mkdir(parents=True)
            (refs_dir / "stale-branch").write_text("abc123" * 7 + "\n")
            (refs_dir / "main").write_text("def456" * 7 + "\n")

            cmd = FetchCommand()

            # Mock to return only main branch
            with patch.object(cmd.github_api, 'list_branches') as mock_list:
                mock_list.return_value = ["main"]

                cmd._prune_refs(repo, "origin", "test", "repo")

                # stale-branch should be removed
                assert not (refs_dir / "stale-branch").exists()
                # main should still exist
                assert (refs_dir / "main").exists()


class TestListRemoteRefs:
    """Tests for listing remote refs."""

    def test_list_remote_refs(self):
        """Test listing refs from remote."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            cmd = FetchCommand()

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'list_branches') as mock_list:
                    mock_list.return_value = ["main", "develop"]

                    with patch.object(cmd.github_api, 'get_branch_info') as mock_info:
                        mock_info.side_effect = [
                            {"commit": {"sha": "aaa" + "0" * 37}},
                            {"commit": {"sha": "bbb" + "0" * 37}},
                        ]

                        refs = cmd.list_remote_refs(repo_path=tmp, remote="origin")

                        assert "refs/heads/main" in refs
                        assert "refs/heads/develop" in refs

    def test_list_remote_refs_no_remote(self):
        """Test listing refs when remote not configured."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = FetchCommand()
            refs = cmd.list_remote_refs(repo_path=tmp, remote="origin")

            assert refs == {}


class TestFetchConvenienceFunction:
    """Tests for fetch_command convenience function."""

    def test_fetch_command_function(self):
        """Test the fetch_command convenience function."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Without remote configured, should fail
            with patch('pygit.commands.fetch.FetchCommand.fetch') as mock_fetch:
                mock_fetch.return_value = False

                result = fetch_command(repo_path=tmp)

                assert result is False
                mock_fetch.assert_called_once()


class TestFetchCLIIntegration:
    """Tests for fetch CLI integration."""

    def test_cli_fetch_parser(self):
        """Test that fetch command is registered in CLI."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        # Try parsing fetch command
        args = parser.parse_args(["fetch"])
        assert args.command == "fetch"
        assert args.remote == "origin"

    def test_cli_fetch_with_remote(self):
        """Test parsing fetch with remote argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["fetch", "upstream"])
        assert args.command == "fetch"
        assert args.remote == "upstream"

    def test_cli_fetch_with_branch(self):
        """Test parsing fetch with branch argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["fetch", "origin", "develop"])
        assert args.command == "fetch"
        assert args.remote == "origin"
        assert args.branch == "develop"

    def test_cli_fetch_all_flag(self):
        """Test parsing fetch with --all flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["fetch", "--all"])
        assert args.all is True

    def test_cli_fetch_prune_flag(self):
        """Test parsing fetch with --prune flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["fetch", "--prune"])
        assert args.prune is True

    def test_cli_fetch_dry_run_flag(self):
        """Test parsing fetch with --dry-run flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["fetch", "--dry-run"])
        assert args.dry_run is True
