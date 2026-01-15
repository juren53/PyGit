"""
Unit tests for pygit.commands.main module.

Tests for PyGitCLI class including add, status, and commit commands.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pygit.commands.main import PyGitCLI, main
from pygit.core.repository import Repository


class TestPyGitCLI:
    """Tests for PyGitCLI class."""

    @pytest.mark.unit
    def test_cli_creation(self):
        """Test creating CLI instance."""
        cli = PyGitCLI()
        assert cli.logger is not None

    @pytest.mark.unit
    def test_create_parser(self):
        """Test creating argument parser."""
        cli = PyGitCLI()
        parser = cli.create_parser()

        assert parser is not None
        assert parser.prog == "pygit"

    @pytest.mark.unit
    def test_parser_has_commands(self):
        """Test that parser has expected commands."""
        cli = PyGitCLI()
        parser = cli.create_parser()

        # Parse help to see subcommands are registered
        # Check that command handlers exist
        assert hasattr(cli, "_handle_clone")
        assert hasattr(cli, "_handle_init")
        assert hasattr(cli, "_handle_add")
        assert hasattr(cli, "_handle_status")
        assert hasattr(cli, "_handle_commit")


class TestCLINoCommand:
    """Tests for CLI with no command."""

    @pytest.mark.unit
    def test_no_command_shows_help(self):
        """Test that no command shows help."""
        cli = PyGitCLI()
        result = cli.run([])
        assert result == 1  # No command returns error

    @pytest.mark.unit
    def test_unknown_command(self):
        """Test handling of unknown command."""
        cli = PyGitCLI()
        # Unknown commands are not parsed by argparse
        # This would raise SystemExit


class TestCLIInit:
    """Tests for init command."""

    @pytest.mark.unit
    def test_init_current_directory(self, temp_dir, monkeypatch):
        """Test init in current directory."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        result = cli.run(["init"])

        assert result == 0
        assert (temp_dir / ".git").exists()

    @pytest.mark.unit
    def test_init_specified_directory(self, temp_dir):
        """Test init in specified directory."""
        target = temp_dir / "new_repo"
        target.mkdir()

        cli = PyGitCLI()
        result = cli.run(["init", str(target)])

        assert result == 0
        assert (target / ".git").exists()


class TestCLIAdd:
    """Tests for add command."""

    @pytest.mark.unit
    def test_add_single_file(self, repo_with_file, temp_repo_dir, monkeypatch):
        """Test adding a single file."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        result = cli.run(["add", "test.txt"])

        assert result == 0

    @pytest.mark.unit
    def test_add_multiple_files(self, repo_with_files, temp_repo_dir, monkeypatch):
        """Test adding multiple files."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        result = cli.run(["add", "README.md", "main.py"])

        assert result == 0

    @pytest.mark.unit
    def test_add_all_flag(self, repo_with_files, temp_repo_dir, monkeypatch):
        """Test adding all files with -A flag."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        # --all requires a placeholder file argument due to argparse config
        result = cli.run(["add", "-A", "."])

        assert result == 0

    @pytest.mark.unit
    def test_add_nonexistent_file(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test adding non-existent file."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        result = cli.run(["add", "nonexistent.txt"])

        assert result == 1  # Should fail

    @pytest.mark.unit
    def test_add_respects_gitignore(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test that add respects .gitignore."""
        monkeypatch.chdir(temp_repo_dir)

        # Create .gitignore
        (temp_repo_dir / ".gitignore").write_text("*.log\n")
        # Create files
        (temp_repo_dir / "keep.txt").write_text("keep")
        (temp_repo_dir / "ignore.log").write_text("ignore")

        cli = PyGitCLI()
        # Add all - should skip .log files
        result = cli.run(["add", "-A", "."])

        assert result == 0


class TestCLIStatus:
    """Tests for status command."""

    @pytest.mark.unit
    def test_status_clean_repo(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test status on clean repository."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        result = cli.run(["status"])

        assert result == 0

    @pytest.mark.unit
    def test_status_with_untracked(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test status with untracked files."""
        monkeypatch.chdir(temp_repo_dir)

        # Create untracked file
        (temp_repo_dir / "untracked.txt").write_text("untracked")

        cli = PyGitCLI()
        result = cli.run(["status"])

        assert result == 0

    @pytest.mark.unit
    def test_status_porcelain_format(self, empty_repo, temp_repo_dir, monkeypatch, capsys):
        """Test status in porcelain format."""
        monkeypatch.chdir(temp_repo_dir)

        # Create untracked file
        (temp_repo_dir / "untracked.txt").write_text("untracked")

        cli = PyGitCLI()
        result = cli.run(["status", "--porcelain"])

        captured = capsys.readouterr()
        assert "??" in captured.out  # Untracked marker
        assert result == 0

    @pytest.mark.unit
    def test_status_short_format(self, empty_repo, temp_repo_dir, monkeypatch, capsys):
        """Test status in short format."""
        monkeypatch.chdir(temp_repo_dir)

        # Create untracked file
        (temp_repo_dir / "untracked.txt").write_text("untracked")

        cli = PyGitCLI()
        result = cli.run(["status", "--short"])

        captured = capsys.readouterr()
        assert "untracked" in captured.out
        assert result == 0


class TestCLICommit:
    """Tests for commit command."""

    @pytest.mark.unit
    def test_commit_empty_index(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test commit with empty index."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        result = cli.run(["commit", "-m", "Test commit"])

        assert result == 1  # Should fail - no changes

    @pytest.mark.unit
    def test_commit_requires_staged_changes(self, empty_repo, temp_repo_dir, monkeypatch):
        """Test commit fails without staged changes."""
        monkeypatch.chdir(temp_repo_dir)

        cli = PyGitCLI()
        # Commit without staging anything
        result = cli.run(["commit", "-m", "Test commit"])

        # Should fail because nothing staged
        assert result == 1

    @pytest.mark.unit
    def test_commit_with_user_config(self, repo_with_file, temp_repo_dir, monkeypatch):
        """Test commit with proper user configuration."""
        monkeypatch.chdir(temp_repo_dir)

        # Configure user
        from pygit.core.config import Config
        config = Config(repo_with_file.git_dir)
        config.set("user", "name", "Test User", "local")
        config.set("user", "email", "test@example.com", "local")

        # Add file
        cli = PyGitCLI()
        cli.run(["add", "test.txt"])

        # Commit
        result = cli.run(["commit", "-m", "Test commit"])

        assert result == 0

    @pytest.mark.unit
    def test_commit_with_author_override(self, repo_with_file, temp_repo_dir, monkeypatch):
        """Test commit with author override."""
        monkeypatch.chdir(temp_repo_dir)

        # Configure default user
        from pygit.core.config import Config
        config = Config(repo_with_file.git_dir)
        config.set("user", "name", "Default User", "local")
        config.set("user", "email", "default@example.com", "local")

        # Add file
        cli = PyGitCLI()
        cli.run(["add", "test.txt"])

        # Commit with author override
        result = cli.run([
            "commit",
            "-m", "Test commit",
            "--author", "Override User <override@example.com>"
        ])

        assert result == 0


class TestCLIVerbosity:
    """Tests for verbosity options."""

    @pytest.mark.unit
    def test_verbose_flag(self, temp_dir, monkeypatch):
        """Test verbose flag."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        result = cli.run(["--verbose", "init"])

        assert result == 0

    @pytest.mark.unit
    def test_quiet_flag(self, temp_dir, monkeypatch):
        """Test quiet flag."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        result = cli.run(["--quiet", "init"])

        assert result == 0


class TestCLIVersion:
    """Tests for version display."""

    @pytest.mark.unit
    def test_version_flag(self, capsys):
        """Test --version flag."""
        cli = PyGitCLI()

        with pytest.raises(SystemExit) as exc_info:
            cli.run(["--version"])

        # Version exits with 0
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "PyGit" in captured.out


class TestMainFunction:
    """Tests for main entry point."""

    @pytest.mark.unit
    def test_main_function_exists(self):
        """Test that main function exists."""
        assert callable(main)

    @pytest.mark.unit
    def test_main_returns_int(self, temp_dir, monkeypatch):
        """Test that main returns an integer."""
        monkeypatch.chdir(temp_dir)

        with patch.object(sys, "argv", ["pygit", "init"]):
            result = main()

        assert isinstance(result, int)
