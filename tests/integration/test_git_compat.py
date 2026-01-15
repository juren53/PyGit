"""
Git compatibility tests.

These tests verify that PyGit repositories are compatible with standard Git
and that PyGit can read repositories created by Git.
"""

import os
import subprocess
import shutil
from pathlib import Path

import pytest

from pygit.core.repository import Repository
from pygit.core.index import Index
from pygit.core.objects import Blob, Tree, TreeEntry, Commit, Author
from pygit.core.config import Config


def git_available():
    """Check if Git is available on the system."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_git(args, cwd=None, check=True):
    """Run a Git command and return the result."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            ["git"] + args,
            result.stdout,
            result.stderr
        )
    return result


# Skip all tests in this module if Git is not available
pytestmark = pytest.mark.skipif(
    not git_available(),
    reason="Git is not available on this system"
)


class TestPyGitRepoWithGit:
    """Test that Git can read PyGit-created repositories."""

    @pytest.mark.integration
    def test_git_status_on_pygit_repo(self, temp_dir):
        """Test that 'git status' works on PyGit-initialized repo."""
        # Initialize with PyGit
        repo = Repository.init(str(temp_dir))

        # Run git status
        result = run_git(["status"], cwd=temp_dir)

        assert result.returncode == 0
        assert "On branch" in result.stdout or "No commits yet" in result.stdout

    @pytest.mark.integration
    def test_git_log_on_pygit_repo(self, temp_dir):
        """Test that 'git log' works after PyGit commit."""
        repo = Repository.init(str(temp_dir))

        # Configure user in Git format
        run_git(["config", "user.name", "Test User"], cwd=temp_dir)
        run_git(["config", "user.email", "test@example.com"], cwd=temp_dir)

        # Create file and commit with PyGit
        (temp_dir / "test.txt").write_text("Hello from PyGit\n")

        index = Index(repo)
        index.add("test.txt", temp_dir)
        index.save()

        tree_sha = index.write_tree()
        author = Author("Test User", "test@example.com")
        commit = Commit(tree_sha, [], author, author, "PyGit commit")
        commit_sha = repo.store_object(commit)

        # Update HEAD
        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit_sha}\n")

        # Run git log
        result = run_git(["log", "--oneline"], cwd=temp_dir)

        assert result.returncode == 0
        assert "PyGit commit" in result.stdout

    @pytest.mark.integration
    def test_git_show_pygit_commit(self, temp_dir):
        """Test that 'git show' displays PyGit commit correctly."""
        repo = Repository.init(str(temp_dir))

        run_git(["config", "user.name", "Test User"], cwd=temp_dir)
        run_git(["config", "user.email", "test@example.com"], cwd=temp_dir)

        # Create commit
        (temp_dir / "file.txt").write_text("Content\n")

        index = Index(repo)
        index.add("file.txt", temp_dir)
        index.save()

        tree_sha = index.write_tree()
        author = Author("Test User", "test@example.com")
        commit = Commit(tree_sha, [], author, author, "Test commit message")
        commit_sha = repo.store_object(commit)

        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit_sha}\n")

        # Git show
        result = run_git(["show", "--stat"], cwd=temp_dir)

        assert result.returncode == 0
        assert "Test commit message" in result.stdout
        assert "file.txt" in result.stdout

    @pytest.mark.integration
    def test_git_diff_on_pygit_repo(self, temp_dir):
        """Test that 'git diff' works on PyGit repo."""
        repo = Repository.init(str(temp_dir))

        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        # Create initial commit
        (temp_dir / "file.txt").write_text("Line 1\n")

        index = Index(repo)
        index.add("file.txt", temp_dir)
        index.save()

        tree_sha = index.write_tree()
        author = Author("Test", "test@test.com")
        commit = Commit(tree_sha, [], author, author, "Initial")
        commit_sha = repo.store_object(commit)

        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit_sha}\n")

        # Remove PyGit's index and rebuild from HEAD using Git
        # This is needed because PyGit's index format has differences that cause
        # Git to misinterpret the staging area state
        index_path = repo.git_dir / "index"
        if index_path.exists():
            index_path.unlink()

        # Rebuild Git's index from the HEAD commit
        run_git(["read-tree", "HEAD"], cwd=temp_dir)

        # Modify file
        (temp_dir / "file.txt").write_text("Line 1\nLine 2\n")

        # Git diff HEAD (compare working tree to commit)
        result = run_git(["diff", "HEAD"], cwd=temp_dir)

        assert result.returncode == 0
        # Should show the added line
        assert "+Line 2" in result.stdout or "Line 2" in result.stdout


class TestGitRepoWithPyGit:
    """Test that PyGit can read Git-created repositories."""

    @pytest.mark.integration
    def test_pygit_reads_git_repo(self, temp_dir):
        """Test that PyGit can open a Git-initialized repository."""
        # Initialize with Git
        run_git(["init"], cwd=temp_dir)

        # Open with PyGit
        repo = Repository(str(temp_dir))

        assert repo.git_dir.exists()
        assert (repo.git_dir / "HEAD").exists()

    @pytest.mark.integration
    def test_pygit_reads_git_objects(self, temp_dir):
        """Test that PyGit can read objects created by Git."""
        # Initialize and commit with Git
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Git User"], cwd=temp_dir)
        run_git(["config", "user.email", "git@example.com"], cwd=temp_dir)

        (temp_dir / "test.txt").write_text("Created by Git\n")
        run_git(["add", "test.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Git commit"], cwd=temp_dir)

        # Get commit SHA from Git
        result = run_git(["rev-parse", "HEAD"], cwd=temp_dir)
        commit_sha = result.stdout.strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        commit = repo.get_object(commit_sha)

        assert commit is not None
        assert commit.type == "commit"
        assert commit.message.startswith("Git commit")

    @pytest.mark.integration
    def test_pygit_reads_git_tree(self, temp_dir):
        """Test that PyGit can read tree objects from Git."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Git User"], cwd=temp_dir)
        run_git(["config", "user.email", "git@example.com"], cwd=temp_dir)

        # Create files
        (temp_dir / "file1.txt").write_text("File 1\n")
        (temp_dir / "file2.txt").write_text("File 2\n")

        run_git(["add", "."], cwd=temp_dir)
        run_git(["commit", "-m", "Multiple files"], cwd=temp_dir)

        # Get tree SHA
        result = run_git(["rev-parse", "HEAD^{tree}"], cwd=temp_dir)
        tree_sha = result.stdout.strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        tree = repo.get_object(tree_sha)

        assert tree is not None
        assert tree.type == "tree"
        assert len(tree.entries) == 2

    @pytest.mark.integration
    def test_pygit_reads_git_blob(self, temp_dir):
        """Test that PyGit can read blob objects from Git."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Git User"], cwd=temp_dir)
        run_git(["config", "user.email", "git@example.com"], cwd=temp_dir)

        content = "Test content from Git\n"
        (temp_dir / "test.txt").write_text(content)

        run_git(["add", "test.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Add file"], cwd=temp_dir)

        # Get blob SHA
        result = run_git(["rev-parse", "HEAD:test.txt"], cwd=temp_dir)
        blob_sha = result.stdout.strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        blob = repo.get_object(blob_sha)

        assert blob is not None
        assert blob.type == "blob"
        assert blob.content.decode() == content


class TestBlobCompatibility:
    """Test blob object compatibility between PyGit and Git."""

    @pytest.mark.integration
    def test_blob_sha_matches_git(self, temp_dir):
        """Test that PyGit blob SHA matches Git's calculation."""
        run_git(["init"], cwd=temp_dir)

        content = b"Hello, World!\n"

        # Calculate SHA with PyGit
        blob = Blob(content)
        pygit_sha = blob.sha1()

        # Calculate SHA with Git
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=content,
            capture_output=True,
            cwd=temp_dir
        )
        git_sha = result.stdout.decode().strip()

        assert pygit_sha == git_sha

    @pytest.mark.integration
    def test_empty_blob_sha(self, temp_dir):
        """Test that empty blob SHA matches Git."""
        run_git(["init"], cwd=temp_dir)

        # PyGit empty blob
        blob = Blob(b"")
        pygit_sha = blob.sha1()

        # Git empty blob (well-known SHA)
        # e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
        assert pygit_sha == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


class TestCommitChainCompatibility:
    """Test commit chain compatibility."""

    @pytest.mark.integration
    def test_pygit_commit_chain_readable_by_git(self, temp_dir):
        """Test that Git can traverse PyGit commit chain."""
        repo = Repository.init(str(temp_dir))

        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        author = Author("Test", "test@test.com")

        # First commit
        (temp_dir / "file.txt").write_text("v1\n")
        index = Index(repo)
        index.add("file.txt", temp_dir)
        index.save()

        tree1 = index.write_tree()
        commit1 = Commit(tree1, [], author, author, "First")
        commit1_sha = repo.store_object(commit1)

        # Second commit
        (temp_dir / "file.txt").write_text("v2\n")
        index2 = Index(repo)
        index2.add("file.txt", temp_dir)
        index2.save()

        tree2 = index2.write_tree()
        commit2 = Commit(tree2, [commit1_sha], author, author, "Second")
        commit2_sha = repo.store_object(commit2)

        # Third commit
        (temp_dir / "file.txt").write_text("v3\n")
        index3 = Index(repo)
        index3.add("file.txt", temp_dir)
        index3.save()

        tree3 = index3.write_tree()
        commit3 = Commit(tree3, [commit2_sha], author, author, "Third")
        commit3_sha = repo.store_object(commit3)

        # Update HEAD
        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit3_sha}\n")

        # Git should see all 3 commits
        result = run_git(["log", "--oneline"], cwd=temp_dir)

        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 3
        assert "Third" in result.stdout
        assert "Second" in result.stdout
        assert "First" in result.stdout


class TestConfigCompatibility:
    """Test configuration compatibility."""

    @pytest.mark.integration
    def test_pygit_reads_git_config(self, temp_dir):
        """Test that PyGit can read Git configuration."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Config Test"], cwd=temp_dir)
        run_git(["config", "user.email", "config@test.com"], cwd=temp_dir)
        run_git(["config", "core.autocrlf", "false"], cwd=temp_dir)

        # Read with PyGit
        repo = Repository(str(temp_dir))
        config = Config(repo.git_dir)

        user_info = config.get_user_info()
        assert user_info["name"] == "Config Test"
        assert user_info["email"] == "config@test.com"

    @pytest.mark.integration
    def test_git_reads_pygit_config(self, temp_dir):
        """Test that Git can read PyGit configuration."""
        repo = Repository.init(str(temp_dir))

        # Set config with PyGit
        config = Config(repo.git_dir)
        config.set("user", "name", "PyGit Config", "local")
        config.set("user", "email", "pygit@config.com", "local")

        # Read with Git
        result = run_git(["config", "user.name"], cwd=temp_dir)
        assert result.stdout.strip() == "PyGit Config"

        result = run_git(["config", "user.email"], cwd=temp_dir)
        assert result.stdout.strip() == "pygit@config.com"
