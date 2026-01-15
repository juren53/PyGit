"""
Unit tests for the pull command.

Tests cover fetch + merge workflow, fast-forward merges, and CLI integration.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pygit.commands.pull import PullCommand, pull_command
from pygit.core.repository import Repository
from pygit.core.config import Config


class TestPullCommandCreation:
    """Tests for PullCommand instantiation."""

    def test_pull_command_creation(self):
        """Test that PullCommand can be created."""
        cmd = PullCommand()
        assert cmd is not None
        assert cmd.fetch_cmd is not None
        assert cmd.logger is not None

    def test_pull_command_with_token(self):
        """Test PullCommand with GitHub token."""
        cmd = PullCommand(github_token="test_token")
        assert cmd.fetch_cmd.github_api.token == "test_token"


class TestPullCurrentBranch:
    """Tests for current branch detection."""

    def test_get_current_branch_on_main(self):
        """Test getting current branch when on main."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Set HEAD to refs/heads/main
            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            cmd = PullCommand()
            branch = cmd._get_current_branch(repo)

            assert branch == "main"

    def test_get_current_branch_on_feature(self):
        """Test getting current branch on feature branch."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/feature/new-thing\n")

            cmd = PullCommand()
            branch = cmd._get_current_branch(repo)

            assert branch == "feature/new-thing"

    def test_get_current_branch_detached_head(self):
        """Test detecting detached HEAD state."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Set HEAD to a direct SHA (detached)
            head_file = repo.git_dir / "HEAD"
            head_file.write_text("a" * 40 + "\n")

            cmd = PullCommand()
            branch = cmd._get_current_branch(repo)

            assert branch is None


class TestPullTrackingBranch:
    """Tests for tracking branch detection."""

    def test_get_tracking_branch_configured(self):
        """Test getting tracking branch from config."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)

            # Configure branch tracking
            config.set_branch("main", "origin", "refs/heads/main")

            cmd = PullCommand()
            tracking = cmd._get_tracking_branch(config, "main", "origin")

            assert tracking == "main"

    def test_get_tracking_branch_not_configured(self):
        """Test default tracking branch when not configured."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)

            cmd = PullCommand()
            tracking = cmd._get_tracking_branch(config, "develop", "origin")

            # Should default to same name
            assert tracking == "develop"


class TestPullFastForward:
    """Tests for fast-forward detection."""

    def test_can_fast_forward_same_commit(self):
        """Test fast-forward when commits are the same."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PullCommand()
            # Same SHA should return True
            result = cmd._can_fast_forward(repo, "a" * 40, "a" * 40)

            assert result is True

    def test_can_fast_forward_no_local_object(self):
        """Test fast-forward when local object doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PullCommand()
            # Different SHAs with no objects
            result = cmd._can_fast_forward(repo, "a" * 40, "b" * 40)

            assert result is False


class TestPullNoRemote:
    """Tests for pull without remote configured."""

    def test_pull_no_remote_configured(self):
        """Test pull fails when remote is not configured."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Set HEAD to main
            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            cmd = PullCommand()
            success = cmd.pull(repo_path=tmp, remote="origin")

            assert success is False

    def test_pull_detached_head(self):
        """Test pull fails on detached HEAD."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            # Set detached HEAD
            head_file = repo.git_dir / "HEAD"
            head_file.write_text("a" * 40 + "\n")

            cmd = PullCommand()
            success = cmd.pull(repo_path=tmp)

            assert success is False


class TestPullRebase:
    """Tests for rebase option."""

    def test_pull_rebase_not_implemented(self):
        """Test that rebase option returns error."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PullCommand()
            success = cmd.pull(repo_path=tmp, rebase=True)

            assert success is False


class TestPullWithMocks:
    """Tests for pull with mocked fetch."""

    def test_pull_already_up_to_date(self):
        """Test pull when already up to date."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)

            # Configure remote
            config.set_remote("origin", "https://github.com/test/repo.git")

            # Set HEAD to main
            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            # Create local branch ref
            local_sha = "a" * 40
            branch_ref = repo.git_dir / "refs" / "heads" / "main"
            branch_ref.parent.mkdir(parents=True, exist_ok=True)
            branch_ref.write_text(f"{local_sha}\n")

            # Create remote ref with same SHA
            remote_ref = repo.git_dir / "refs" / "remotes" / "origin" / "main"
            remote_ref.parent.mkdir(parents=True, exist_ok=True)
            remote_ref.write_text(f"{local_sha}\n")

            cmd = PullCommand()

            # Mock fetch to succeed
            with patch.object(cmd.fetch_cmd, 'fetch') as mock_fetch:
                mock_fetch.return_value = True

                # Mock get_head to return local SHA
                with patch.object(repo, 'get_head') as mock_head:
                    mock_head.return_value = local_sha

                    success = cmd.pull(repo_path=tmp, remote="origin", branch="main")

                    assert success is True

    def test_pull_fetch_fails(self):
        """Test pull when fetch fails."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)
            config = Config(repo.git_dir)

            config.set_remote("origin", "https://github.com/test/repo.git")

            head_file = repo.git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            cmd = PullCommand()

            with patch.object(cmd.fetch_cmd, 'fetch') as mock_fetch:
                mock_fetch.return_value = False

                success = cmd.pull(repo_path=tmp, remote="origin", branch="main")

                assert success is False


class TestPullConvenienceFunction:
    """Tests for pull_command convenience function."""

    def test_pull_command_function(self):
        """Test the pull_command convenience function."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            with patch('pygit.commands.pull.PullCommand.pull') as mock_pull:
                mock_pull.return_value = False

                result = pull_command(repo_path=tmp)

                assert result is False
                mock_pull.assert_called_once()


class TestPullCLIIntegration:
    """Tests for pull CLI integration."""

    def test_cli_pull_parser(self):
        """Test that pull command is registered in CLI."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull"])
        assert args.command == "pull"
        assert args.remote == "origin"

    def test_cli_pull_with_remote(self):
        """Test parsing pull with remote argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "upstream"])
        assert args.command == "pull"
        assert args.remote == "upstream"

    def test_cli_pull_with_branch(self):
        """Test parsing pull with branch argument."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "origin", "develop"])
        assert args.command == "pull"
        assert args.remote == "origin"
        assert args.branch == "develop"

    def test_cli_pull_ff_only_flag(self):
        """Test parsing pull with --ff-only flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "--ff-only"])
        assert args.ff_only is True

    def test_cli_pull_no_ff_flag(self):
        """Test parsing pull with --no-ff flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "--no-ff"])
        assert args.no_ff is True

    def test_cli_pull_rebase_flag(self):
        """Test parsing pull with --rebase flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "--rebase"])
        assert args.rebase is True

    def test_cli_pull_rebase_short_flag(self):
        """Test parsing pull with -r flag."""
        from pygit.commands.main import PyGitCLI

        cli = PyGitCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["pull", "-r"])
        assert args.rebase is True


class TestPullUpdateHead:
    """Tests for HEAD and checkout updates."""

    def test_update_head_and_checkout_creates_branch_ref(self):
        """Test that update creates branch ref file."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository.init(tmp)

            cmd = PullCommand()

            # Mock _checkout_tree to avoid actual checkout
            with patch.object(cmd, '_checkout_tree') as mock_checkout:
                mock_checkout.return_value = True

                target_sha = "b" * 40
                success = cmd._update_head_and_checkout(repo, target_sha, "main")

                assert success is True

                # Check branch ref was created
                branch_ref = repo.git_dir / "refs" / "heads" / "main"
                assert branch_ref.exists()
                assert branch_ref.read_text().strip() == target_sha

                # Check HEAD points to branch
                head_content = (repo.git_dir / "HEAD").read_text().strip()
                assert head_content == "ref: refs/heads/main"
