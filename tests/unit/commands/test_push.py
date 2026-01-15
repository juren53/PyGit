"""
Unit tests for the push command.

Tests cover commit pushing, GitHub API integration, and CLI integration.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pygit.commands.push import PushCommand, push_command
from pygit.core.repository import Repository
from pygit.core.config import Config


class TestPushCommandCreation:
    """Tests for PushCommand instantiation."""

    def test_push_command_creation(self):
        """Test that PushCommand can be created."""
        cmd = PushCommand()
        assert cmd is not None
        assert cmd.github_api is not None
        assert cmd.logger is not None

    def test_push_command_with_token(self):
        """Test PushCommand with GitHub token."""
        cmd = PushCommand(github_token="test_token")
        assert cmd.github_api.token == "test_token"


class TestPushNoToken:
    """Tests for push without token."""

    def test_push_requires_token(self):
        """Test that push fails without token."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand()  # No token
            success = cmd.push(repo_path=tmp)

            assert success is False


class TestPushNoRemote:
    """Tests for push without remote configured."""

    def test_push_no_remote_configured(self):
        """Test push fails when remote not configured."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            success = cmd.push(repo_path=tmp, remote="origin")

            assert success is False


class TestPushCurrentBranch:
    """Tests for current branch detection."""

    def test_get_current_branch(self):
        """Test getting current branch."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            cmd = PushCommand(github_token="test_token")
            branch = cmd._get_current_branch(repo)

            assert branch == "main"

    def test_get_current_branch_detached(self):
        """Test detached HEAD returns None."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("a" * 40 + "\n")

            cmd = PushCommand(github_token="test_token")
            branch = cmd._get_current_branch(repo)

            assert branch is None

    def test_push_detached_head_fails(self):
        """Test push fails on detached HEAD."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("a" * 40 + "\n")

            cmd = PushCommand(github_token="test_token")

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                success = cmd.push(repo_path=tmp)

                assert success is False


class TestPushBranchSha:
    """Tests for branch SHA retrieval."""

    def test_get_branch_sha(self):
        """Test getting branch SHA."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            sha = "a" * 40
            branch_ref = repo.git_dir / "refs" / "heads" / "main"
            branch_ref.parent.mkdir(parents=True, exist_ok=True)
            branch_ref.write_text(f"{sha}\n")

            cmd = PushCommand(github_token="test_token")
            result = cmd._get_branch_sha(repo, "main")

            assert result == sha

    def test_get_branch_sha_nonexistent(self):
        """Test getting SHA of nonexistent branch."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            result = cmd._get_branch_sha(repo, "nonexistent")

            assert result is None


class TestPushAncestorCheck:
    """Tests for ancestor checking."""

    def test_is_ancestor_same_commit(self):
        """Test that commit is its own ancestor."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            result = cmd._is_ancestor(repo, "a" * 40, "a" * 40)

            assert result is True

    def test_is_ancestor_no_objects(self):
        """Test ancestor check with no objects."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            result = cmd._is_ancestor(repo, "a" * 40, "b" * 40)

            assert result is False


class TestPushCommitCollection:
    """Tests for commit collection."""

    def test_get_commits_to_push_empty(self):
        """Test empty commit list when up to date."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            # Same SHA means nothing to push
            result = cmd._get_commits_to_push(repo, "a" * 40, "a" * 40)

            assert result == []

    def test_get_commits_to_push_no_remote(self):
        """Test commit collection when remote has nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PushCommand(github_token="test_token")
            # No remote SHA means everything needs pushing
            result = cmd._get_commits_to_push(repo, "a" * 40, None)

            assert "a" * 40 in result


class TestPushWithMocks:
    """Tests for push with mocked GitHub API."""

    def test_push_up_to_date(self):
        """Test push when already up to date."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            sha = "a" * 40
            branch_ref = repo.git_dir / "refs" / "heads" / "main"
            branch_ref.parent.mkdir(parents=True, exist_ok=True)
            branch_ref.write_text(f"{sha}\n")

            cmd = PushCommand(github_token="test_token")

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'get_ref') as mock_ref:
                    # Remote has same SHA
                    mock_ref.return_value = sha

                    success = cmd.push(repo_path=tmp)

                    assert success is True

    def test_push_no_commits(self):
        """Test push when branch has no commits."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            # No branch ref file = no commits

            cmd = PushCommand(github_token="test_token")

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                success = cmd.push(repo_path=tmp)

                assert success is False


class TestPushDryRun:
    """Tests for dry-run mode."""

    def test_push_dry_run(self):
        """Test dry-run mode doesn't push."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)
            config.set_remote("origin", "https://github.com/test/repo.git")

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            sha = "a" * 40
            branch_ref = repo.git_dir / "refs" / "heads" / "main"
            branch_ref.parent.mkdir(parents=True, exist_ok=True)
            branch_ref.write_text(f"{sha}\n")

            cmd = PushCommand(github_token="test_token")

            with patch.object(cmd.github_api, 'parse_git_url') as mock_parse:
                mock_parse.return_value = (
                    "https://api.github.com/repos/test/repo",
                    "test",
                    "repo"
                )

                with patch.object(cmd.github_api, 'get_ref') as mock_ref:
                    mock_ref.return_value = None  # No remote commits

                    with patch.object(cmd, '_get_commits_to_push') as mock_commits:
                        mock_commits.return_value = [sha]

                        with patch.object(repo, 'get_object') as mock_obj:
                            mock_obj.return_value = {
                                "type": "commit",
                                "message": "Test commit"
                            }

                            success = cmd.push(repo_path=tmp, dry_run=True)

                            assert success is True


class TestPushConvenienceFunction:
    """Tests for push_command convenience function."""

    def test_push_command_function(self):
        """Test the push_command convenience function."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            with patch('pygit.commands.push.PushCommand.push') as mock_push:
                mock_push.return_value = False

                result = push_command(repo_path=tmp)

                assert result is False
                mock_push.assert_called_once()


class TestPushCLIIntegration:
    """Tests for push CLI integration."""

    def test_cli_push_parser(self):
        """Test that push command is registered in CLI."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push"])
        assert args.command == "push"
        assert args.remote == "origin"

    def test_cli_push_with_remote(self):
        """Test parsing push with remote argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "upstream"])
        assert args.command == "push"
        assert args.remote == "upstream"

    def test_cli_push_with_branch(self):
        """Test parsing push with branch argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "origin", "develop"])
        assert args.command == "push"
        assert args.remote == "origin"
        assert args.branch == "develop"

    def test_cli_push_force_flag(self):
        """Test parsing push with --force flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "--force"])
        assert args.force is True

    def test_cli_push_force_short_flag(self):
        """Test parsing push with -f flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "-f"])
        assert args.force is True

    def test_cli_push_set_upstream_flag(self):
        """Test parsing push with --set-upstream flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "--set-upstream"])
        assert args.set_upstream is True

    def test_cli_push_set_upstream_short_flag(self):
        """Test parsing push with -u flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "-u"])
        assert args.set_upstream is True

    def test_cli_push_dry_run_flag(self):
        """Test parsing push with --dry-run flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "--dry-run"])
        assert args.dry_run is True

    def test_cli_push_all_flag(self):
        """Test parsing push with --all flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "--all"])
        assert args.all is True

    def test_cli_push_token_flag(self):
        """Test parsing push with --token flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["push", "--token", "my_token"])
        assert args.token == "my_token"
