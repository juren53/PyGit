"""
Unit tests for pygit.core.repository module.

Tests for Repository class including initialization, object storage,
and Git directory structure.
"""

import os
import zlib
from pathlib import Path

import pytest

from pygit.core.repository import Repository
from pygit.core.objects import Blob, Tree, TreeEntry, Commit, Tag, Author


class TestRepositoryInit:
    """Tests for repository initialization."""

    @pytest.mark.unit
    def test_init_creates_git_directory(self, temp_dir):
        """Test that init creates .git directory."""
        repo = Repository.init(str(temp_dir))
        assert repo.git_dir.exists()
        assert repo.git_dir.name == ".git"

    @pytest.mark.unit
    def test_init_creates_required_directories(self, temp_dir):
        """Test that init creates all required subdirectories."""
        repo = Repository.init(str(temp_dir))

        required_dirs = [
            "objects",
            "objects/pack",
            "objects/info",
            "refs",
            "refs/heads",
            "refs/tags",
            "logs",
            "hooks",
            "info",
        ]

        for dir_name in required_dirs:
            dir_path = repo.git_dir / dir_name
            assert dir_path.exists(), f"Missing directory: {dir_name}"
            assert dir_path.is_dir(), f"Not a directory: {dir_name}"

    @pytest.mark.unit
    def test_init_creates_head_file(self, temp_dir):
        """Test that init creates HEAD file."""
        repo = Repository.init(str(temp_dir))
        head_file = repo.git_dir / "HEAD"

        assert head_file.exists()
        content = head_file.read_text()
        assert content == "ref: refs/heads/main\n"

    @pytest.mark.unit
    def test_init_creates_config_file(self, temp_dir):
        """Test that init creates config file."""
        repo = Repository.init(str(temp_dir))
        config_file = repo.git_dir / "config"

        assert config_file.exists()
        content = config_file.read_text()
        assert "[core]" in content
        assert "repositoryformatversion" in content

    @pytest.mark.unit
    def test_init_creates_description_file(self, temp_dir):
        """Test that init creates description file."""
        repo = Repository.init(str(temp_dir))
        desc_file = repo.git_dir / "description"

        assert desc_file.exists()

    @pytest.mark.unit
    def test_init_does_not_create_index(self, temp_dir):
        """Test that init does NOT create index file.

        Index file is created on demand when files are added.
        Creating an empty index breaks Git compatibility.
        """
        repo = Repository.init(str(temp_dir))
        index_file = repo.git_dir / "index"

        # Index should NOT exist after init (Git doesn't expect empty index)
        assert not index_file.exists()

    @pytest.mark.unit
    def test_open_existing_repository(self, temp_dir):
        """Test opening an existing repository."""
        # First create a repo
        Repository.init(str(temp_dir))

        # Then open it
        repo = Repository(str(temp_dir))
        assert repo.git_dir.exists()

    @pytest.mark.unit
    def test_open_nonexistent_repository_raises(self, temp_dir):
        """Test that opening non-existent repo raises error."""
        with pytest.raises(ValueError) as exc_info:
            Repository(str(temp_dir / "nonexistent"))

        assert "Not a git repository" in str(exc_info.value)

    @pytest.mark.unit
    def test_repository_path_resolution(self, temp_dir):
        """Test that repository path is resolved to absolute."""
        repo = Repository.init(str(temp_dir))
        assert repo.path.is_absolute()


class TestRepositoryProperties:
    """Tests for repository properties."""

    @pytest.mark.unit
    def test_is_bare_false(self, empty_repo):
        """Test is_bare for normal repository."""
        assert empty_repo.is_bare is False

    @pytest.mark.unit
    def test_str_representation(self, empty_repo):
        """Test string representation."""
        repo_str = str(empty_repo)
        assert "Repository" in repo_str
        assert "normal" in repo_str


class TestRepositoryObjectStorage:
    """Tests for object storage and retrieval."""

    @pytest.mark.unit
    def test_object_path_calculation(self, empty_repo):
        """Test object path calculation from SHA1."""
        sha1 = "abc123def456789012345678901234567890abcd"
        obj_path = empty_repo.object_path(sha1)

        assert obj_path.parent.name == "ab"  # First 2 chars
        assert obj_path.name == "c123def456789012345678901234567890abcd"

    @pytest.mark.unit
    def test_object_path_invalid_sha1(self, empty_repo):
        """Test object path with invalid SHA1."""
        with pytest.raises(ValueError) as exc_info:
            empty_repo.object_path("invalid")

        assert "Invalid SHA-1" in str(exc_info.value)

    @pytest.mark.unit
    def test_store_blob_object(self, empty_repo, sample_blob):
        """Test storing a blob object."""
        sha1 = empty_repo.store_object(sample_blob)

        assert len(sha1) == 40
        obj_path = empty_repo.object_path(sha1)
        assert obj_path.exists()

    @pytest.mark.unit
    def test_store_object_idempotent(self, empty_repo, sample_blob):
        """Test that storing same object twice returns same SHA1."""
        sha1_first = empty_repo.store_object(sample_blob)
        sha1_second = empty_repo.store_object(sample_blob)

        assert sha1_first == sha1_second

    @pytest.mark.unit
    def test_store_tree_object(self, empty_repo, sample_tree):
        """Test storing a tree object."""
        sha1 = empty_repo.store_object(sample_tree)

        assert len(sha1) == 40
        obj_path = empty_repo.object_path(sha1)
        assert obj_path.exists()

    @pytest.mark.unit
    def test_store_commit_object(self, empty_repo, sample_commit):
        """Test storing a commit object."""
        sha1 = empty_repo.store_object(sample_commit)

        assert len(sha1) == 40
        obj_path = empty_repo.object_path(sha1)
        assert obj_path.exists()

    @pytest.mark.unit
    def test_store_tag_object(self, empty_repo, sample_tag):
        """Test storing a tag object."""
        sha1 = empty_repo.store_object(sample_tag)

        assert len(sha1) == 40
        obj_path = empty_repo.object_path(sha1)
        assert obj_path.exists()

    @pytest.mark.unit
    def test_stored_object_is_compressed(self, empty_repo, sample_blob):
        """Test that stored objects are zlib compressed."""
        sha1 = empty_repo.store_object(sample_blob)
        obj_path = empty_repo.object_path(sha1)

        compressed_data = obj_path.read_bytes()
        decompressed = zlib.decompress(compressed_data)

        assert b"blob" in decompressed
        assert sample_blob.content in decompressed


class TestRepositoryObjectRetrieval:
    """Tests for retrieving objects."""

    @pytest.mark.unit
    def test_get_blob_object(self, empty_repo):
        """Test retrieving a stored blob."""
        original = Blob(b"Test content for retrieval\n")
        sha1 = empty_repo.store_object(original)

        retrieved = empty_repo.get_object(sha1)

        assert retrieved is not None
        assert retrieved.type == "blob"
        assert retrieved.content == original.content

    @pytest.mark.unit
    def test_get_tree_object(self, empty_repo):
        """Test retrieving a stored tree."""
        # First store a blob to reference
        blob = Blob(b"file content")
        blob_sha = empty_repo.store_object(blob)

        # Create and store tree
        tree = Tree([TreeEntry("100644", "file.txt", blob_sha)])
        tree_sha = empty_repo.store_object(tree)

        retrieved = empty_repo.get_object(tree_sha)

        assert retrieved is not None
        assert retrieved.type == "tree"
        assert len(retrieved.entries) == 1

    @pytest.mark.unit
    def test_get_commit_object(self, empty_repo):
        """Test retrieving a stored commit."""
        # Create tree first
        blob = Blob(b"content")
        blob_sha = empty_repo.store_object(blob)
        tree = Tree([TreeEntry("100644", "file.txt", blob_sha)])
        tree_sha = empty_repo.store_object(tree)

        # Create commit
        author = Author("Test User", "test@example.com", 1704067200, "+0000")
        commit = Commit(tree_sha, [], author, author, "Test commit message")
        commit_sha = empty_repo.store_object(commit)

        retrieved = empty_repo.get_object(commit_sha)

        assert retrieved is not None
        assert retrieved.type == "commit"
        assert retrieved.message == "Test commit message"
        assert retrieved.author.name == "Test User"

    @pytest.mark.unit
    def test_get_tag_object(self, empty_repo):
        """Test retrieving a stored tag."""
        # Create commit to tag
        blob = Blob(b"content")
        blob_sha = empty_repo.store_object(blob)
        tree = Tree([TreeEntry("100644", "file.txt", blob_sha)])
        tree_sha = empty_repo.store_object(tree)

        author = Author("Test User", "test@example.com", 1704067200, "+0000")
        commit = Commit(tree_sha, [], author, author, "Test")
        commit_sha = empty_repo.store_object(commit)

        # Create tag
        tag = Tag(commit_sha, "commit", "v1.0.0", author, "Release tag")
        tag_sha = empty_repo.store_object(tag)

        retrieved = empty_repo.get_object(tag_sha)

        assert retrieved is not None
        assert retrieved.type == "tag"
        assert retrieved.tag_name == "v1.0.0"

    @pytest.mark.unit
    def test_get_nonexistent_object(self, empty_repo):
        """Test retrieving non-existent object returns None."""
        fake_sha = "0" * 40
        result = empty_repo.get_object(fake_sha)
        assert result is None


class TestRepositoryHead:
    """Tests for HEAD management."""

    @pytest.mark.unit
    def test_get_head_initial(self, empty_repo):
        """Test getting HEAD in fresh repository."""
        # HEAD points to refs/heads/main which doesn't exist yet
        head = empty_repo.get_head()
        assert head is None

    @pytest.mark.unit
    def test_set_head_branch_reference(self, empty_repo):
        """Test setting HEAD to a branch reference."""
        empty_repo.set_head("refs/heads/develop")

        head_content = (empty_repo.git_dir / "HEAD").read_text()
        assert head_content == "ref: refs/heads/develop\n"

    @pytest.mark.unit
    def test_set_head_detached(self, empty_repo):
        """Test setting HEAD to a detached state."""
        sha1 = "a" * 40
        empty_repo.set_head(sha1)

        head_content = (empty_repo.git_dir / "HEAD").read_text().strip()
        assert head_content == sha1

    @pytest.mark.unit
    def test_get_head_with_commit(self, empty_repo):
        """Test getting HEAD when branch has commits."""
        # Create a commit and update the branch ref
        sha1 = "abc123def456789012345678901234567890abcd"
        refs_path = empty_repo.git_dir / "refs" / "heads" / "main"
        refs_path.parent.mkdir(parents=True, exist_ok=True)
        refs_path.write_text(f"{sha1}\n")

        head = empty_repo.get_head()
        assert head == sha1


class TestRepositoryParseObjects:
    """Tests for object parsing methods."""

    @pytest.mark.unit
    def test_parse_author_full(self, empty_repo):
        """Test parsing full author string."""
        author_str = "John Doe <john@example.com> 1704067200 -0500"
        author = empty_repo._parse_author(author_str)

        assert author.name == "John Doe"
        assert author.email == "john@example.com"
        assert author.timestamp == 1704067200
        assert author.timezone == "-0500"

    @pytest.mark.unit
    def test_parse_author_missing_email(self, empty_repo):
        """Test parsing author without proper email format."""
        author_str = "JohnDoe 1704067200 +0000"
        author = empty_repo._parse_author(author_str)

        # Should handle gracefully
        assert author is not None

    @pytest.mark.unit
    def test_parse_tree_multiple_entries(self, empty_repo):
        """Test parsing tree with multiple entries."""
        # Create tree data manually
        entries = []
        for i in range(3):
            sha = bytes([i] * 20)
            entry_data = f"100644 file{i}.txt\0".encode() + sha
            entries.append(entry_data)

        tree_data = b"".join(entries)
        tree = empty_repo._parse_tree(tree_data)

        assert len(tree.entries) == 3

    @pytest.mark.unit
    def test_parse_commit_with_parents(self, empty_repo):
        """Test parsing commit with parent commits."""
        commit_data = b"""tree aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
parent bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
parent cccccccccccccccccccccccccccccccccccccccc
author Test User <test@test.com> 1704067200 +0000
committer Test User <test@test.com> 1704067200 +0000

Merge commit message"""

        commit = empty_repo._parse_commit(commit_data)

        assert commit.tree_sha1 == "a" * 40
        assert len(commit.parents) == 2
        assert commit.parents[0] == "b" * 40
        assert commit.parents[1] == "c" * 40
