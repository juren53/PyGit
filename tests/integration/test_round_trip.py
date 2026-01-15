"""
Round-trip tests for PyGit.

These tests verify that data written by PyGit can be read back correctly,
and that PyGit can read data written by Git (and vice versa).
"""

import os
import subprocess
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


class TestBlobRoundTrip:
    """Round-trip tests for blob objects."""

    @pytest.mark.integration
    def test_pygit_blob_readable_by_git(self, temp_dir):
        """Test that blobs created by PyGit can be read by Git."""
        repo = Repository.init(str(temp_dir))

        # Create blob with PyGit
        content = b"Hello from PyGit!\n"
        blob = Blob(content)
        blob_sha = repo.store_object(blob)

        # Read with Git
        result = run_git(["cat-file", "-p", blob_sha], cwd=temp_dir)

        assert result.returncode == 0
        assert result.stdout == content.decode()

    @pytest.mark.integration
    def test_git_blob_readable_by_pygit(self, temp_dir):
        """Test that blobs created by Git can be read by PyGit."""
        run_git(["init"], cwd=temp_dir)

        # Create blob with Git
        content = "Hello from Git!\n"
        result = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            input=content.encode(),
            capture_output=True,
            cwd=temp_dir
        )
        git_sha = result.stdout.decode().strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        blob = repo.get_object(git_sha)

        assert blob is not None
        assert blob.type == "blob"
        assert blob.content.decode() == content

    @pytest.mark.integration
    def test_blob_sha_consistency(self, temp_dir):
        """Test that PyGit and Git calculate the same SHA for identical content."""
        run_git(["init"], cwd=temp_dir)

        content = b"Test content for SHA verification\n"

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
    def test_binary_blob_round_trip(self, temp_dir):
        """Test round-trip for binary content."""
        repo = Repository.init(str(temp_dir))

        # Binary content with various byte values
        content = bytes(range(256))
        blob = Blob(content)
        blob_sha = repo.store_object(blob)

        # Verify Git can read it
        result = run_git(["cat-file", "-t", blob_sha], cwd=temp_dir)
        assert result.stdout.strip() == "blob"

        # Read back with PyGit
        retrieved = repo.get_object(blob_sha)
        assert retrieved.content == content


class TestTreeRoundTrip:
    """Round-trip tests for tree objects."""

    @pytest.mark.integration
    def test_pygit_tree_readable_by_git(self, temp_dir):
        """Test that trees created by PyGit can be read by Git."""
        repo = Repository.init(str(temp_dir))

        # Create blob first
        blob = Blob(b"File content\n")
        blob_sha = repo.store_object(blob)

        # Create tree with PyGit
        entry = TreeEntry(0o100644, "test.txt", blob_sha)
        tree = Tree([entry])
        tree_sha = repo.store_object(tree)

        # Read with Git
        result = run_git(["ls-tree", tree_sha], cwd=temp_dir)

        assert result.returncode == 0
        assert "test.txt" in result.stdout
        assert blob_sha in result.stdout

    @pytest.mark.integration
    def test_git_tree_readable_by_pygit(self, temp_dir):
        """Test that trees created by Git can be read by PyGit."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        # Create file and commit to get a tree
        (temp_dir / "file.txt").write_text("Content\n")
        run_git(["add", "file.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Initial"], cwd=temp_dir)

        # Get tree SHA from Git
        result = run_git(["rev-parse", "HEAD^{tree}"], cwd=temp_dir)
        tree_sha = result.stdout.strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        tree = repo.get_object(tree_sha)

        assert tree is not None
        assert tree.type == "tree"
        assert len(tree.entries) == 1
        assert tree.entries[0].name == "file.txt"

    @pytest.mark.integration
    def test_nested_tree_round_trip(self, temp_dir):
        """Test round-trip for nested tree structures."""
        repo = Repository.init(str(temp_dir))
        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        # Create directory structure
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')\n")
        (src_dir / "utils.py").write_text("# utils\n")
        (temp_dir / "README.md").write_text("# Project\n")

        # Add and commit with PyGit
        index = Index(repo)
        index.add("src/main.py", temp_dir)
        index.add("src/utils.py", temp_dir)
        index.add("README.md", temp_dir)
        index.save()

        tree_sha = index.write_tree()

        # Verify with Git
        result = run_git(["ls-tree", "-r", tree_sha], cwd=temp_dir)

        assert result.returncode == 0
        assert "src/main.py" in result.stdout
        assert "src/utils.py" in result.stdout
        assert "README.md" in result.stdout


class TestCommitRoundTrip:
    """Round-trip tests for commit objects."""

    @pytest.mark.integration
    def test_pygit_commit_readable_by_git(self, temp_dir):
        """Test that commits created by PyGit can be read by Git."""
        repo = Repository.init(str(temp_dir))
        run_git(["config", "user.name", "PyGit Test"], cwd=temp_dir)
        run_git(["config", "user.email", "pygit@test.com"], cwd=temp_dir)

        # Create file and commit
        (temp_dir / "test.txt").write_text("Test content\n")
        index = Index(repo)
        index.add("test.txt", temp_dir)
        index.save()

        tree_sha = index.write_tree()
        author = Author("PyGit Test", "pygit@test.com")
        commit = Commit(tree_sha, [], author, author, "PyGit test commit")
        commit_sha = repo.store_object(commit)

        # Update HEAD
        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit_sha}\n")

        # Read with Git
        result = run_git(["log", "-1", "--format=%s"], cwd=temp_dir)

        assert result.returncode == 0
        assert "PyGit test commit" in result.stdout

    @pytest.mark.integration
    def test_git_commit_readable_by_pygit(self, temp_dir):
        """Test that commits created by Git can be read by PyGit."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Git Test"], cwd=temp_dir)
        run_git(["config", "user.email", "git@test.com"], cwd=temp_dir)

        # Create commit with Git
        (temp_dir / "file.txt").write_text("Git content\n")
        run_git(["add", "file.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Git test commit"], cwd=temp_dir)

        # Get commit SHA
        result = run_git(["rev-parse", "HEAD"], cwd=temp_dir)
        commit_sha = result.stdout.strip()

        # Read with PyGit
        repo = Repository(str(temp_dir))
        commit = repo.get_object(commit_sha)

        assert commit is not None
        assert commit.type == "commit"
        assert commit.message.startswith("Git test commit")
        assert commit.author.name == "Git Test"
        assert commit.author.email == "git@test.com"

    @pytest.mark.integration
    def test_commit_chain_round_trip(self, temp_dir):
        """Test round-trip for commit chains."""
        repo = Repository.init(str(temp_dir))
        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        author = Author("Test", "test@test.com")
        commits = []

        # Create 3 commits
        for i in range(3):
            (temp_dir / "file.txt").write_text(f"Version {i+1}\n")

            index = Index(repo)
            index.add("file.txt", temp_dir)
            index.save()

            tree_sha = index.write_tree()
            parents = [commits[-1]] if commits else []
            commit = Commit(tree_sha, parents, author, author, f"Commit {i+1}")
            commit_sha = repo.store_object(commit)
            commits.append(commit_sha)

        # Update HEAD
        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commits[-1]}\n")

        # Verify with Git
        result = run_git(["rev-list", "--count", "HEAD"], cwd=temp_dir)
        assert result.stdout.strip() == "3"

        # Read commits back with PyGit
        for i, sha in enumerate(reversed(commits)):
            commit = repo.get_object(sha)
            assert commit.message == f"Commit {3-i}"


class TestIndexRoundTrip:
    """Round-trip tests for index operations."""

    @pytest.mark.integration
    def test_pygit_index_visible_to_git_status(self, temp_dir):
        """Test that files added with PyGit show in git status."""
        repo = Repository.init(str(temp_dir))

        # Create and add file with PyGit
        (temp_dir / "staged.txt").write_text("Staged content\n")
        index = Index(repo)
        index.add("staged.txt", temp_dir)
        index.save()

        # Check with git status
        result = run_git(["status", "--porcelain"], cwd=temp_dir)

        assert result.returncode == 0
        # Should show as added to index
        assert "staged.txt" in result.stdout

    @pytest.mark.integration
    def test_git_index_readable_by_pygit(self, temp_dir):
        """Test that PyGit can read Git's index."""
        run_git(["init"], cwd=temp_dir)

        # Add files with Git
        (temp_dir / "file1.txt").write_text("Content 1\n")
        (temp_dir / "file2.txt").write_text("Content 2\n")
        run_git(["add", "file1.txt", "file2.txt"], cwd=temp_dir)

        # Read with PyGit
        repo = Repository(str(temp_dir))
        index = Index(repo)

        # PyGit should see the staged files
        assert "file1.txt" in index or len(index) == 2


class TestConfigRoundTrip:
    """Round-trip tests for configuration."""

    @pytest.mark.integration
    def test_pygit_config_readable_by_git(self, temp_dir):
        """Test that config written by PyGit can be read by Git."""
        repo = Repository.init(str(temp_dir))

        # Set config with PyGit
        config = Config(repo.git_dir)
        config.set("user", "name", "PyGit User", "local")
        config.set("user", "email", "pygit@example.com", "local")
        config.set("core", "filemode", "false", "local")

        # Read with Git
        result = run_git(["config", "user.name"], cwd=temp_dir)
        assert result.stdout.strip() == "PyGit User"

        result = run_git(["config", "user.email"], cwd=temp_dir)
        assert result.stdout.strip() == "pygit@example.com"

        result = run_git(["config", "core.filemode"], cwd=temp_dir)
        assert result.stdout.strip() == "false"

    @pytest.mark.integration
    def test_git_config_readable_by_pygit(self, temp_dir):
        """Test that config written by Git can be read by PyGit."""
        run_git(["init"], cwd=temp_dir)

        # Set config with Git
        run_git(["config", "user.name", "Git User"], cwd=temp_dir)
        run_git(["config", "user.email", "git@example.com"], cwd=temp_dir)
        run_git(["config", "custom.setting", "value"], cwd=temp_dir)

        # Read with PyGit
        repo = Repository(str(temp_dir))
        config = Config(repo.git_dir)

        user_info = config.get_user_info()
        assert user_info["name"] == "Git User"
        assert user_info["email"] == "git@example.com"

        custom = config.get("custom", "setting")
        assert custom == "value"


class TestMixedWorkflow:
    """Tests for mixed PyGit/Git workflows."""

    @pytest.mark.integration
    def test_pygit_commit_then_git_commit(self, temp_dir):
        """Test creating commits alternating between PyGit and Git."""
        repo = Repository.init(str(temp_dir))
        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        # First commit with PyGit
        (temp_dir / "file1.txt").write_text("PyGit v1\n")
        index = Index(repo)
        index.add("file1.txt", temp_dir)
        index.save()

        tree_sha = index.write_tree()
        author = Author("Test", "test@test.com")
        commit1 = Commit(tree_sha, [], author, author, "PyGit commit 1")
        commit1_sha = repo.store_object(commit1)

        main_ref = repo.git_dir / "refs" / "heads" / "main"
        main_ref.write_text(f"{commit1_sha}\n")

        # Second commit with Git
        (temp_dir / "file2.txt").write_text("Git v2\n")
        run_git(["add", "file2.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Git commit 2"], cwd=temp_dir)

        # Third commit with PyGit
        result = run_git(["rev-parse", "HEAD"], cwd=temp_dir)
        commit2_sha = result.stdout.strip()

        (temp_dir / "file3.txt").write_text("PyGit v3\n")
        index2 = Index(repo)
        index2.add("file1.txt", temp_dir)
        index2.add("file2.txt", temp_dir)
        index2.add("file3.txt", temp_dir)
        index2.save()

        tree3_sha = index2.write_tree()
        commit3 = Commit(tree3_sha, [commit2_sha], author, author, "PyGit commit 3")
        commit3_sha = repo.store_object(commit3)

        main_ref.write_text(f"{commit3_sha}\n")

        # Verify full history with Git
        result = run_git(["log", "--oneline"], cwd=temp_dir)
        lines = result.stdout.strip().split("\n")

        assert len(lines) == 3
        assert "PyGit commit 3" in result.stdout
        assert "Git commit 2" in result.stdout
        assert "PyGit commit 1" in result.stdout

    @pytest.mark.integration
    def test_git_branch_pygit_merge_base(self, temp_dir):
        """Test that PyGit can work with Git branches."""
        run_git(["init"], cwd=temp_dir)
        run_git(["config", "user.name", "Test"], cwd=temp_dir)
        run_git(["config", "user.email", "test@test.com"], cwd=temp_dir)

        # Create initial commit with Git
        (temp_dir / "main.txt").write_text("Main file\n")
        run_git(["add", "main.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Initial"], cwd=temp_dir)

        # Get main commit SHA
        result = run_git(["rev-parse", "HEAD"], cwd=temp_dir)
        main_sha = result.stdout.strip()

        # PyGit should be able to read this commit
        repo = Repository(str(temp_dir))
        commit = repo.get_object(main_sha)

        assert commit is not None
        assert commit.message.startswith("Initial")
