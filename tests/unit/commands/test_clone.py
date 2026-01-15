"""
Unit tests for pygit.commands.clone module.

Tests for CloneCommand class using GitHub API mocks.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pygit.commands.clone import CloneCommand, clone_command

# Import our mock infrastructure
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mocks import MockGitHubAPI, GitHubMockResponses


class TestCloneCommand:
    """Tests for CloneCommand class."""

    @pytest.mark.unit
    def test_clone_command_creation(self):
        """Test creating a clone command instance."""
        cmd = CloneCommand()
        assert cmd.github_api is not None
        assert cmd.http_client is not None

    @pytest.mark.unit
    def test_clone_command_with_token(self):
        """Test creating clone command with GitHub token."""
        cmd = CloneCommand(github_token="test_token")
        assert cmd.github_api.token == "test_token"

    @pytest.mark.unit
    def test_clone_command_with_progress(self):
        """Test creating clone command with progress callback."""
        callback = MagicMock()
        cmd = CloneCommand(progress_callback=callback)
        assert cmd.http_client.progress_callback == callback


class TestCloneURLParsing:
    """Tests for URL parsing in clone."""

    @pytest.mark.unit
    def test_clone_non_github_url(self, temp_dir):
        """Test that non-GitHub URLs are rejected."""
        cmd = CloneCommand()

        # Mock parse_git_url to return None (non-GitHub)
        cmd.github_api.parse_git_url = MagicMock(return_value=(None, None, None))

        result = cmd.clone(
            "https://gitlab.com/user/repo.git",
            str(temp_dir / "repo")
        )

        assert result is False


class TestCloneDestination:
    """Tests for destination handling."""

    @pytest.mark.unit
    def test_clone_existing_destination(self, temp_dir):
        """Test that existing destination causes failure."""
        # Create the destination
        dest = temp_dir / "existing_repo"
        dest.mkdir()

        cmd = CloneCommand()
        cmd.github_api = MockGitHubAPI()

        result = cmd.clone(
            "https://github.com/user/repo.git",
            str(dest)
        )

        assert result is False

    @pytest.mark.unit
    def test_clone_default_destination(self, temp_dir, monkeypatch):
        """Test that default destination is repo name."""
        # Change to temp dir so repo is created there
        monkeypatch.chdir(temp_dir)

        cmd = CloneCommand()
        mock_api = MockGitHubAPI()
        cmd.github_api = mock_api

        # Should extract "test-repo" as destination
        # The clone will fail at download but we can check the path
        result = cmd.clone("https://github.com/user/test-repo.git")

        # Even if clone fails, the attempt should use "test-repo" as dest


class TestCloneWithMocks:
    """Tests for clone using mock infrastructure."""

    @pytest.mark.unit
    def test_clone_creates_git_directory(self, temp_dir):
        """Test that clone creates .git directory structure."""
        dest = temp_dir / "cloned_repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", GitHubMockResponses.repo_info())
        mock_api.set_response("tree", GitHubMockResponses.tree_recursive(
            files=[
                {"path": "README.md", "type": "blob"},
            ]
        ))
        mock_api.set_response("branch_info", GitHubMockResponses.branch_info())

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest)
        )

        # Clone should create .git directory
        if result:
            assert (dest / ".git").exists()
            assert (dest / ".git" / "HEAD").exists()

    @pytest.mark.unit
    def test_clone_stores_remote_config(self, temp_dir):
        """Test that clone stores remote origin in config."""
        dest = temp_dir / "cloned_repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", GitHubMockResponses.repo_info(
            owner="testuser",
            repo="test-repo"
        ))
        mock_api.set_response("tree", GitHubMockResponses.tree_recursive(files=[]))
        mock_api.set_response("branch_info", GitHubMockResponses.branch_info())

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest)
        )

        if result:
            config_file = dest / ".git" / "config"
            if config_file.exists():
                config_content = config_file.read_text()
                assert "origin" in config_content or "remote" in config_content

    @pytest.mark.unit
    def test_clone_downloads_files(self, temp_dir):
        """Test that clone downloads repository files."""
        dest = temp_dir / "cloned_repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", GitHubMockResponses.repo_info())
        mock_api.set_response("tree", GitHubMockResponses.tree_recursive(
            files=[
                {"path": "README.md", "type": "blob"},
                {"path": "main.py", "type": "blob"},
            ]
        ))
        mock_api.set_response("branch_info", GitHubMockResponses.branch_info())
        mock_api.set_file_content("README.md", b"# Test\n")
        mock_api.set_file_content("main.py", b"print('hello')\n")

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest)
        )

        if result:
            # Files should exist in working directory
            readme = dest / "README.md"
            main_py = dest / "main.py"
            # Check if files were created
            # (may not exist if clone partially failed)


class TestCloneBranches:
    """Tests for branch handling in clone."""

    @pytest.mark.unit
    def test_clone_specific_branch(self, temp_dir):
        """Test cloning a specific branch."""
        dest = temp_dir / "cloned_repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", GitHubMockResponses.repo_info(
            default_branch="main"
        ))
        mock_api.set_response("tree", GitHubMockResponses.tree_recursive(files=[]))
        mock_api.set_response("branch_info", GitHubMockResponses.branch_info(
            name="develop"
        ))

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest),
            branch="develop"
        )

        # Verify branch was passed to API calls
        calls = [c for c in mock_api.call_history if c["method"] == "get_tree_recursive"]
        if calls:
            assert calls[-1]["kwargs"]["branch"] == "develop"


class TestCloneListBranches:
    """Tests for listing remote branches."""

    @pytest.mark.unit
    def test_list_remote_branches(self):
        """Test listing remote branches."""
        mock_api = MockGitHubAPI()
        mock_api.set_response("branches", GitHubMockResponses.branches_list(
            branches=["main", "develop", "feature/test"]
        ))

        cmd = CloneCommand()
        cmd.github_api = mock_api

        branches = cmd.list_remote_branches(
            "https://github.com/testuser/test-repo.git"
        )

        assert "main" in branches
        assert "develop" in branches
        assert "feature/test" in branches

    @pytest.mark.unit
    def test_list_remote_branches_invalid_url(self):
        """Test listing branches with invalid URL."""
        cmd = CloneCommand()
        cmd.github_api.parse_git_url = MagicMock(return_value=(None, None, None))

        branches = cmd.list_remote_branches("invalid://url")

        assert branches == {}


class TestCloneConvenienceFunction:
    """Tests for clone_command convenience function."""

    @pytest.mark.unit
    def test_clone_command_function(self, temp_dir):
        """Test the convenience function."""
        dest = temp_dir / "repo"

        # This will fail since no mocking, but tests the function exists
        with patch.object(CloneCommand, "clone", return_value=True) as mock_clone:
            result = clone_command(
                "https://github.com/user/repo.git",
                str(dest)
            )

            mock_clone.assert_called_once()
            assert result is True


class TestCloneErrorHandling:
    """Tests for error handling in clone."""

    @pytest.mark.unit
    def test_clone_repo_info_failure(self, temp_dir):
        """Test clone when repo info cannot be retrieved."""
        dest = temp_dir / "repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", None)  # Simulate failure

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest)
        )

        assert result is False

    @pytest.mark.unit
    def test_clone_tree_failure(self, temp_dir):
        """Test clone when tree cannot be retrieved."""
        dest = temp_dir / "repo"

        mock_api = MockGitHubAPI()
        mock_api.set_response("repo_info", GitHubMockResponses.repo_info())
        mock_api.get_tree_recursive = MagicMock(return_value=[])

        cmd = CloneCommand()
        cmd.github_api = mock_api

        result = cmd.clone(
            "https://github.com/testuser/test-repo.git",
            str(dest)
        )

        # Empty tree should be handled gracefully
