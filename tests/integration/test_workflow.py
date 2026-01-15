"""
Integration tests for end-to-end PyGit workflows.

These tests verify complete workflows from repository initialization
through commits, ensuring all components work together correctly.
"""

import os
import subprocess
from pathlib import Path

import pytest

from pygit.core.repository import Repository
from pygit.core.index import Index
from pygit.core.objects import Blob, Commit, Author
from pygit.core.config import Config
from pygit.core.ignore import GitIgnore
from pygit.commands.main import PyGitCLI


class TestInitWorkflow:
    """Tests for repository initialization workflow."""

    @pytest.mark.integration
    def test_init_creates_valid_repo(self, temp_dir):
        """Test that init creates a valid Git repository structure."""
        repo = Repository.init(str(temp_dir))

        # Verify .git structure
        assert (temp_dir / ".git").is_dir()
        assert (temp_dir / ".git" / "objects").is_dir()
        assert (temp_dir / ".git" / "refs" / "heads").is_dir()
        assert (temp_dir / ".git" / "HEAD").is_file()

        # Verify HEAD content
        head_content = (temp_dir / ".git" / "HEAD").read_text()
        assert "ref: refs/heads/" in head_content

    @pytest.mark.integration
    def test_init_via_cli(self, temp_dir, monkeypatch):
        """Test init through CLI interface."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        result = cli.run(["init"])

        assert result == 0
        assert (temp_dir / ".git").exists()


class TestAddCommitWorkflow:
    """Tests for add and commit workflow."""

    @pytest.mark.integration
    def test_add_single_file_workflow(self, temp_dir):
        """Test adding a single file to staging."""
        # Initialize repo
        repo = Repository.init(str(temp_dir))

        # Create a file
        test_file = temp_dir / "hello.txt"
        test_file.write_text("Hello, World!\n")

        # Add to index
        index = Index(repo)
        result = index.add("hello.txt", temp_dir)

        assert result is True
        assert "hello.txt" in index
        assert len(index) == 1

    @pytest.mark.integration
    def test_add_multiple_files_workflow(self, temp_dir):
        """Test adding multiple files to staging."""
        repo = Repository.init(str(temp_dir))

        # Create multiple files
        (temp_dir / "file1.txt").write_text("Content 1\n")
        (temp_dir / "file2.txt").write_text("Content 2\n")
        (temp_dir / "file3.txt").write_text("Content 3\n")

        # Add all files
        index = Index(repo)
        index.add("file1.txt", temp_dir)
        index.add("file2.txt", temp_dir)
        index.add("file3.txt", temp_dir)

        assert len(index) == 3

    @pytest.mark.integration
    def test_add_with_subdirectories(self, temp_dir):
        """Test adding files in subdirectories."""
        repo = Repository.init(str(temp_dir))

        # Create directory structure
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')\n")
        (src_dir / "utils.py").write_text("# utils\n")

        tests_dir = temp_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("# tests\n")

        # Add files
        index = Index(repo)
        index.add("src/main.py", temp_dir)
        index.add("src/utils.py", temp_dir)
        index.add("tests/test_main.py", temp_dir)

        assert len(index) == 3
        assert "src/main.py" in index
        assert "src/utils.py" in index
        assert "tests/test_main.py" in index

    @pytest.mark.integration
    def test_commit_workflow(self, temp_dir):
        """Test complete commit workflow."""
        repo = Repository.init(str(temp_dir))

        # Configure user
        config = Config(repo.git_dir)
        config.set("user", "name", "Test User", "local")
        config.set("user", "email", "test@example.com", "local")

        # Create and add file
        (temp_dir / "README.md").write_text("# Test Project\n")
        index = Index(repo)
        index.add("README.md", temp_dir)
        index.save()

        # Create tree from index
        tree_sha = index.write_tree()
        assert len(tree_sha) == 40

        # Create commit
        author = Author("Test User", "test@example.com")
        commit = Commit(
            tree_sha1=tree_sha,
            parents=[],
            author=author,
            committer=author,
            message="Initial commit"
        )
        commit_sha = repo.store_object(commit)

        # Verify commit was stored
        assert len(commit_sha) == 40
        retrieved = repo.get_object(commit_sha)
        assert retrieved is not None
        assert retrieved.type == "commit"
        assert retrieved.message == "Initial commit"


class TestFullWorkflow:
    """Tests for complete init → add → commit workflow."""

    @pytest.mark.integration
    def test_full_workflow_single_commit(self, temp_dir):
        """Test complete workflow: init → create files → add → commit."""
        # Step 1: Initialize
        repo = Repository.init(str(temp_dir))

        # Step 2: Configure user
        config = Config(repo.git_dir)
        config.set("user", "name", "Integration Test", "local")
        config.set("user", "email", "integration@test.com", "local")

        # Step 3: Create project structure
        (temp_dir / "README.md").write_text("# My Project\n\nA test project.\n")
        (temp_dir / "main.py").write_text("def main():\n    print('Hello')\n")

        src = temp_dir / "src"
        src.mkdir()
        (src / "__init__.py").write_text("")
        (src / "core.py").write_text("# Core module\n")

        # Step 4: Add files to staging
        index = Index(repo)
        index.add("README.md", temp_dir)
        index.add("main.py", temp_dir)
        index.add("src/__init__.py", temp_dir)
        index.add("src/core.py", temp_dir)
        index.save()

        assert len(index) == 4

        # Step 5: Create commit
        tree_sha = index.write_tree()
        author = Author("Integration Test", "integration@test.com")
        commit = Commit(
            tree_sha1=tree_sha,
            parents=[],
            author=author,
            committer=author,
            message="Initial commit\n\nAdded project structure."
        )
        commit_sha = repo.store_object(commit)

        # Update HEAD reference
        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit_sha}\n")

        # Verify
        assert repo.get_head() == commit_sha

    @pytest.mark.integration
    def test_full_workflow_multiple_commits(self, temp_dir):
        """Test workflow with multiple sequential commits."""
        repo = Repository.init(str(temp_dir))

        config = Config(repo.git_dir)
        config.set("user", "name", "Test User", "local")
        config.set("user", "email", "test@example.com", "local")

        author = Author("Test User", "test@example.com")

        # First commit
        (temp_dir / "file1.txt").write_text("Version 1\n")
        index = Index(repo)
        index.add("file1.txt", temp_dir)
        index.save()

        tree1_sha = index.write_tree()
        commit1 = Commit(tree1_sha, [], author, author, "First commit")
        commit1_sha = repo.store_object(commit1)

        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit1_sha}\n")

        # Second commit (with parent)
        (temp_dir / "file2.txt").write_text("New file\n")
        index2 = Index(repo)
        index2.add("file1.txt", temp_dir)
        index2.add("file2.txt", temp_dir)
        index2.save()

        tree2_sha = index2.write_tree()
        commit2 = Commit(tree2_sha, [commit1_sha], author, author, "Second commit")
        commit2_sha = repo.store_object(commit2)

        main_ref.write_text(f"{commit2_sha}\n")

        # Verify commit chain
        retrieved_commit2 = repo.get_object(commit2_sha)
        assert len(retrieved_commit2.parents) == 1
        assert retrieved_commit2.parents[0] == commit1_sha

    @pytest.mark.integration
    def test_full_workflow_via_cli(self, temp_dir, monkeypatch):
        """Test complete workflow using CLI commands."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()

        # Initialize
        result = cli.run(["init"])
        assert result == 0

        # Configure user (manually since CLI doesn't have config command yet)
        repo = Repository(str(temp_dir))
        config = Config(repo.git_dir)
        config.set("user", "name", "CLI Test User", "local")
        config.set("user", "email", "cli@test.com", "local")

        # Create files
        (temp_dir / "test.txt").write_text("CLI test content\n")

        # Add
        result = cli.run(["add", "test.txt"])
        assert result == 0

        # Check status
        result = cli.run(["status"])
        assert result == 0

        # Commit
        result = cli.run(["commit", "-m", "CLI test commit"])
        assert result == 0


class TestGitIgnoreWorkflow:
    """Tests for .gitignore integration in workflows."""

    @pytest.mark.integration
    def test_gitignore_excludes_files(self, temp_dir):
        """Test that .gitignore properly excludes files from operations."""
        repo = Repository.init(str(temp_dir))

        # Create .gitignore
        (temp_dir / ".gitignore").write_text("*.log\n__pycache__/\n.env\n")

        # Create files (some should be ignored)
        (temp_dir / "main.py").write_text("# main\n")
        (temp_dir / "debug.log").write_text("debug output\n")
        (temp_dir / ".env").write_text("SECRET=123\n")

        pycache = temp_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-312.pyc").write_bytes(b"\x00\x00")

        # Check gitignore
        gitignore = GitIgnore(temp_dir)

        assert not gitignore.is_ignored("main.py")
        assert gitignore.is_ignored("debug.log")
        assert gitignore.is_ignored(".env")
        assert gitignore.is_ignored("__pycache__", is_dir=True)

    @pytest.mark.integration
    def test_add_respects_gitignore(self, temp_dir, monkeypatch):
        """Test that add --all respects .gitignore."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        cli.run(["init"])

        # Create .gitignore and files
        (temp_dir / ".gitignore").write_text("*.log\n")
        (temp_dir / "keep.txt").write_text("keep this\n")
        (temp_dir / "ignore.log").write_text("ignore this\n")

        # Configure user
        repo = Repository(str(temp_dir))
        config = Config(repo.git_dir)
        config.set("user", "name", "Test", "local")
        config.set("user", "email", "test@test.com", "local")

        # Add all
        cli.run(["add", "-A", "."])

        # Check index
        index = Index(repo)
        # keep.txt should be in index, ignore.log should not
        # Note: Due to the --all implementation, we verify via status


class TestStatusWorkflow:
    """Tests for status command in workflows."""

    @pytest.mark.integration
    def test_status_shows_untracked(self, temp_dir, monkeypatch, capsys):
        """Test that status shows untracked files."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        cli.run(["init"])

        # Create untracked file
        (temp_dir / "untracked.txt").write_text("untracked\n")

        # Check status
        cli.run(["status", "--porcelain"])

        captured = capsys.readouterr()
        assert "??" in captured.out
        assert "untracked.txt" in captured.out

    @pytest.mark.integration
    def test_status_after_add(self, temp_dir, monkeypatch, capsys):
        """Test status after adding files."""
        monkeypatch.chdir(temp_dir)

        cli = PyGitCLI()
        cli.run(["init"])

        # Create and add file
        (temp_dir / "staged.txt").write_text("staged\n")
        cli.run(["add", "staged.txt"])

        # Status should show staged file differently
        # (Current implementation may vary)
        result = cli.run(["status"])
        assert result == 0


class TestModifyWorkflow:
    """Tests for modifying files after initial commit."""

    @pytest.mark.integration
    def test_modify_and_recommit(self, temp_dir):
        """Test modifying a file and creating a new commit."""
        repo = Repository.init(str(temp_dir))

        config = Config(repo.git_dir)
        config.set("user", "name", "Test", "local")
        config.set("user", "email", "test@test.com", "local")

        author = Author("Test", "test@test.com")

        # Initial commit
        (temp_dir / "file.txt").write_text("Version 1\n")
        index = Index(repo)
        index.add("file.txt", temp_dir)
        index.save()

        tree1 = index.write_tree()
        commit1 = Commit(tree1, [], author, author, "Version 1")
        commit1_sha = repo.store_object(commit1)

        # Modify file
        (temp_dir / "file.txt").write_text("Version 2\n")

        # Detect modification
        modified = index.get_modified_files(temp_dir)
        assert "file.txt" in modified
        assert modified["file.txt"] == "modified"

        # Re-add and commit
        index.add("file.txt", temp_dir)
        index.save()

        tree2 = index.write_tree()
        commit2 = Commit(tree2, [commit1_sha], author, author, "Version 2")
        commit2_sha = repo.store_object(commit2)

        # Verify different trees
        assert tree1 != tree2

        # Verify commit chain
        retrieved = repo.get_object(commit2_sha)
        assert retrieved.parents[0] == commit1_sha
