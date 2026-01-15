"""
Unit tests for pygit.core.objects module.

Tests for Git object types: Blob, Tree, Commit, Tag.
"""

import pytest
import hashlib
import zlib

from pygit.core.objects import GitObject, Blob, Tree, TreeEntry, Commit, Tag, Author


class TestBlob:
    """Tests for Blob object."""

    @pytest.mark.unit
    def test_blob_creation(self, sample_blob):
        """Test basic blob creation."""
        assert sample_blob.type == "blob"
        assert sample_blob.content == b"Hello, World!\n"

    @pytest.mark.unit
    def test_blob_empty(self, sample_blob_empty):
        """Test empty blob creation."""
        assert sample_blob_empty.type == "blob"
        assert sample_blob_empty.content == b""
        # Known SHA for empty blob
        assert sample_blob_empty.sha1() == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

    @pytest.mark.unit
    def test_blob_sha1_consistency(self):
        """Test that SHA1 is consistent for same content."""
        blob1 = Blob(b"test content")
        blob2 = Blob(b"test content")
        assert blob1.sha1() == blob2.sha1()

    @pytest.mark.unit
    def test_blob_sha1_different_content(self):
        """Test that different content produces different SHA1."""
        blob1 = Blob(b"content 1")
        blob2 = Blob(b"content 2")
        assert blob1.sha1() != blob2.sha1()

    @pytest.mark.unit
    def test_blob_sha1_matches_git(self):
        """Test that SHA1 calculation matches Git's format."""
        content = b"Hello, World!\n"
        blob = Blob(content)

        # Git's SHA1 format: "blob {size}\0{content}"
        header = f"blob {len(content)}\0".encode()
        expected_sha = hashlib.sha1(header + content).hexdigest()

        assert blob.sha1() == expected_sha

    @pytest.mark.unit
    def test_blob_serialize(self, sample_blob):
        """Test blob serialization produces valid compressed data."""
        serialized = sample_blob.serialize()

        # Should be zlib compressed
        decompressed = zlib.decompress(serialized)

        # Should start with "blob {size}\0"
        assert decompressed.startswith(b"blob ")
        assert b"\0" in decompressed

    @pytest.mark.unit
    def test_blob_equality(self):
        """Test blob equality based on SHA1."""
        blob1 = Blob(b"same content")
        blob2 = Blob(b"same content")
        blob3 = Blob(b"different content")

        assert blob1 == blob2
        assert blob1 != blob3

    @pytest.mark.unit
    def test_blob_binary_content(self, sample_blob_binary):
        """Test blob with binary content."""
        assert sample_blob_binary.type == "blob"
        assert len(sample_blob_binary.content) == 256
        # Should be able to calculate SHA1
        assert len(sample_blob_binary.sha1()) == 40


class TestTreeEntry:
    """Tests for TreeEntry."""

    @pytest.mark.unit
    def test_tree_entry_creation(self, sample_tree_entry):
        """Test tree entry creation."""
        assert sample_tree_entry.mode == "100644"
        assert sample_tree_entry.name == "test.txt"
        assert len(sample_tree_entry.sha1) == 40

    @pytest.mark.unit
    def test_tree_entry_serialize(self, sample_tree_entry):
        """Test tree entry serialization."""
        serialized = sample_tree_entry.serialize()

        # Format: "{mode} {name}\0{20-byte-sha}"
        assert serialized.startswith(b"100644 test.txt\0")
        # Should end with 20 raw bytes (SHA1 in binary)
        assert len(serialized) == len(b"100644 test.txt\0") + 20


class TestTree:
    """Tests for Tree object."""

    @pytest.mark.unit
    def test_tree_creation(self, sample_tree):
        """Test basic tree creation."""
        assert sample_tree.type == "tree"
        assert len(sample_tree.entries) == 1

    @pytest.mark.unit
    def test_tree_empty(self):
        """Test empty tree creation."""
        tree = Tree()
        assert tree.type == "tree"
        assert len(tree.entries) == 0

    @pytest.mark.unit
    def test_tree_add_entry(self):
        """Test adding entries to tree."""
        tree = Tree()
        tree.add_entry("100644", "file1.txt", "a" * 40)
        tree.add_entry("100644", "file2.txt", "b" * 40)

        assert len(tree.entries) == 2

    @pytest.mark.unit
    def test_tree_get_entry(self, sample_tree):
        """Test getting entry by name."""
        entry = sample_tree.get_entry("test.txt")
        assert entry is not None
        assert entry.name == "test.txt"

        missing = sample_tree.get_entry("nonexistent.txt")
        assert missing is None

    @pytest.mark.unit
    def test_tree_sha1_changes_on_add(self):
        """Test that SHA1 changes when entries are added."""
        tree = Tree()
        sha1_empty = tree.sha1()

        tree.add_entry("100644", "file.txt", "a" * 40)
        sha1_with_entry = tree.sha1()

        assert sha1_empty != sha1_with_entry

    @pytest.mark.unit
    def test_tree_entries_sorted(self):
        """Test that tree entries are sorted by name in data."""
        tree = Tree()
        tree.add_entry("100644", "zebra.txt", "c" * 40)  # Using valid hex chars
        tree.add_entry("100644", "apple.txt", "a" * 40)
        tree.add_entry("100644", "mango.txt", "b" * 40)

        data = tree.data
        # apple should come before mango, mango before zebra
        assert data.find(b"apple.txt") < data.find(b"mango.txt")
        assert data.find(b"mango.txt") < data.find(b"zebra.txt")


class TestAuthor:
    """Tests for Author."""

    @pytest.mark.unit
    def test_author_creation(self, sample_author):
        """Test author creation."""
        assert sample_author.name == "Test User"
        assert sample_author.email == "test@example.com"
        assert sample_author.timestamp == 1704067200
        assert sample_author.timezone == "-0600"

    @pytest.mark.unit
    def test_author_serialize(self, sample_author):
        """Test author serialization."""
        serialized = sample_author.serialize()
        assert serialized == "Test User <test@example.com> 1704067200 -0600"

    @pytest.mark.unit
    def test_author_default_timestamp(self):
        """Test author with default timestamp."""
        author = Author("Name", "email@test.com")
        assert author.timestamp > 0
        assert author.timezone == "+0000"


class TestCommit:
    """Tests for Commit object."""

    @pytest.mark.unit
    def test_commit_creation(self, sample_commit):
        """Test basic commit creation."""
        assert sample_commit.type == "commit"
        assert sample_commit.message == "Test commit message"

    @pytest.mark.unit
    def test_commit_data_format(self, sample_commit):
        """Test commit data format matches Git."""
        data = sample_commit.data.decode()

        # Should have tree line
        assert data.startswith("tree ")
        # Should have author and committer
        assert "author " in data
        assert "committer " in data
        # Message should be at the end
        assert data.endswith("Test commit message")

    @pytest.mark.unit
    def test_commit_with_parent(self, sample_tree, sample_author):
        """Test commit with parent."""
        parent_sha = "p" * 40
        commit = Commit(
            tree_sha1=sample_tree.sha1(),
            parents=[parent_sha],
            author=sample_author,
            message="Child commit",
        )

        data = commit.data.decode()
        assert f"parent {parent_sha}" in data

    @pytest.mark.unit
    def test_commit_add_parent(self, sample_commit):
        """Test adding parent to commit."""
        sha1_before = sample_commit.sha1()
        sample_commit.add_parent("p" * 40)
        sha1_after = sample_commit.sha1()

        assert sha1_before != sha1_after
        assert len(sample_commit.parents) == 1


class TestTag:
    """Tests for Tag object."""

    @pytest.mark.unit
    def test_tag_creation(self, sample_tag):
        """Test basic tag creation."""
        assert sample_tag.type == "tag"
        assert sample_tag.tag_name == "v1.0.0"
        assert sample_tag.object_type == "commit"

    @pytest.mark.unit
    def test_tag_data_format(self, sample_tag):
        """Test tag data format matches Git."""
        data = sample_tag.data.decode()

        assert data.startswith("object ")
        assert "type commit" in data
        assert "tag v1.0.0" in data
        assert "tagger " in data
        assert data.endswith("Release v1.0.0")

    @pytest.mark.unit
    def test_tag_str(self, sample_tag, sample_commit):
        """Test tag string representation."""
        tag_str = str(sample_tag)
        assert "v1.0.0" in tag_str
        assert sample_commit.sha1() in tag_str
