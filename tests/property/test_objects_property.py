"""
Property-based tests for Git objects using Hypothesis.

These tests verify that object serialization is correct for arbitrary inputs,
catching edge cases that manual tests might miss.
"""

import string
from hypothesis import given, strategies as st, assume, settings

import pytest

from pygit.core.objects import Blob, Tree, TreeEntry, Commit, Author, Tag


# Custom strategies for Git-specific types
def sha1_hex():
    """Generate valid SHA1 hex strings (40 lowercase hex chars)."""
    return st.text(
        alphabet=string.hexdigits[:16],  # Only lowercase hex
        min_size=40,
        max_size=40
    )


def valid_filename():
    """Generate valid filenames (no null bytes, slashes, or empty)."""
    safe_chars = string.ascii_letters + string.digits + "._-"
    return st.text(
        alphabet=safe_chars,
        min_size=1,
        max_size=100
    ).filter(lambda x: x not in (".", ".."))


def file_mode():
    """Generate valid Git file modes."""
    return st.sampled_from([
        0o100644,  # Regular file
        0o100755,  # Executable
        0o120000,  # Symlink
        0o040000,  # Directory/tree
    ])


def timezone_str():
    """Generate valid timezone strings."""
    return st.sampled_from([
        "+0000", "-0500", "+0530", "-0800", "+1200", "-1200"
    ])


class TestBlobProperties:
    """Property-based tests for Blob objects."""

    @pytest.mark.property
    @given(content=st.binary(min_size=0, max_size=10000))
    def test_blob_sha1_is_consistent(self, content):
        """SHA1 of the same content is always identical."""
        blob1 = Blob(content)
        blob2 = Blob(content)
        assert blob1.sha1() == blob2.sha1()

    @pytest.mark.property
    @given(content=st.binary(min_size=0, max_size=10000))
    def test_blob_sha1_is_valid_hex(self, content):
        """SHA1 is always a 40-character hex string."""
        blob = Blob(content)
        sha = blob.sha1()
        assert len(sha) == 40
        assert all(c in string.hexdigits for c in sha)

    @pytest.mark.property
    @given(content=st.binary(min_size=0, max_size=10000))
    def test_blob_type_is_blob(self, content):
        """Blob type property always returns blob."""
        blob = Blob(content)
        assert blob.type == "blob"

    @pytest.mark.property
    @given(content=st.binary(min_size=0, max_size=10000))
    def test_blob_data_matches_content(self, content):
        """Blob data property returns original content."""
        blob = Blob(content)
        assert blob.data == content

    @pytest.mark.property
    @given(content1=st.binary(min_size=1, max_size=1000),
           content2=st.binary(min_size=1, max_size=1000))
    def test_different_content_different_sha(self, content1, content2):
        """Different content produces different SHA1."""
        assume(content1 != content2)
        blob1 = Blob(content1)
        blob2 = Blob(content2)
        assert blob1.sha1() != blob2.sha1()


class TestTreeEntryProperties:
    """Property-based tests for TreeEntry objects."""

    @pytest.mark.property
    @given(mode=file_mode(), name=valid_filename(), sha=sha1_hex())
    def test_tree_entry_serialize_contains_name(self, mode, name, sha):
        """Serialized tree entry contains the filename."""
        entry = TreeEntry(mode, name, sha)
        serialized = entry.serialize()
        assert name.encode() in serialized

    @pytest.mark.property
    @given(mode=file_mode(), name=valid_filename(), sha=sha1_hex())
    def test_tree_entry_serialize_contains_sha_bytes(self, mode, name, sha):
        """Serialized tree entry contains SHA as binary."""
        entry = TreeEntry(mode, name, sha)
        serialized = entry.serialize()
        sha_bytes = bytes.fromhex(sha)
        assert sha_bytes in serialized

    @pytest.mark.property
    @given(mode=file_mode(), name=valid_filename(), sha=sha1_hex())
    def test_tree_entry_serialize_has_null_separator(self, mode, name, sha):
        """Serialized tree entry has null byte between name and SHA."""
        entry = TreeEntry(mode, name, sha)
        serialized = entry.serialize()
        assert b"\0" in serialized


class TestTreeProperties:
    """Property-based tests for Tree objects."""

    @pytest.mark.property
    @given(st.lists(
        st.tuples(file_mode(), valid_filename(), sha1_hex()),
        min_size=0,
        max_size=20,
        unique_by=lambda x: x[1]
    ))
    def test_tree_sha1_is_consistent(self, entries_data):
        """Tree SHA1 is consistent for same entries."""
        entries = [TreeEntry(m, n, s) for m, n, s in entries_data]
        tree1 = Tree(entries.copy())
        tree2 = Tree(entries.copy())
        assert tree1.sha1() == tree2.sha1()

    @pytest.mark.property
    @given(st.lists(
        st.tuples(file_mode(), valid_filename(), sha1_hex()),
        min_size=0,
        max_size=20,
        unique_by=lambda x: x[1]
    ))
    def test_tree_type_is_tree(self, entries_data):
        """Tree type property always returns tree."""
        entries = [TreeEntry(m, n, s) for m, n, s in entries_data]
        tree = Tree(entries)
        assert tree.type == "tree"

    @pytest.mark.property
    @given(st.lists(
        st.tuples(file_mode(), valid_filename(), sha1_hex()),
        min_size=0,
        max_size=20,
        unique_by=lambda x: x[1]
    ))
    def test_tree_sha1_is_valid_hex(self, entries_data):
        """Tree SHA1 is always a 40-character hex string."""
        entries = [TreeEntry(m, n, s) for m, n, s in entries_data]
        tree = Tree(entries)
        sha = tree.sha1()
        assert len(sha) == 40
        assert all(c in string.hexdigits for c in sha)


class TestAuthorProperties:
    """Property-based tests for Author objects."""

    @pytest.mark.property
    @given(
        name=st.text(alphabet=string.ascii_letters + " ", min_size=1, max_size=50),
        # Use min_value=1 since 0/None triggers default timestamp behavior
        timestamp=st.integers(min_value=1, max_value=2**31-1),
        tz=timezone_str()
    )
    def test_author_properties_stored(self, name, timestamp, tz):
        """Author properties are stored correctly."""
        # Use fixed email to avoid edge cases
        email = "test@example.com"
        author = Author(name, email, timestamp, tz)
        assert author.name == name
        assert author.email == email
        assert author.timestamp == timestamp
        assert author.timezone == tz


class TestCommitProperties:
    """Property-based tests for Commit objects."""

    @pytest.mark.property
    @given(
        tree_sha=sha1_hex(),
        message=st.text(min_size=1, max_size=500)
    )
    def test_commit_sha1_is_valid_hex(self, tree_sha, message):
        """Commit SHA1 is always a 40-character hex string."""
        author = Author("Test", "test@test.com", 1234567890, "+0000")
        commit = Commit(tree_sha, [], author, author, message)
        sha = commit.sha1()
        assert len(sha) == 40
        assert all(c in string.hexdigits for c in sha)

    @pytest.mark.property
    @given(
        tree_sha=sha1_hex(),
        message=st.text(min_size=1, max_size=500)
    )
    def test_commit_type_is_commit(self, tree_sha, message):
        """Commit type property always returns commit."""
        author = Author("Test", "test@test.com", 1234567890, "+0000")
        commit = Commit(tree_sha, [], author, author, message)
        assert commit.type == "commit"

    @pytest.mark.property
    @given(
        tree_sha=sha1_hex(),
        parent_shas=st.lists(sha1_hex(), min_size=0, max_size=5),
        message=st.text(min_size=1, max_size=500)
    )
    def test_commit_stores_parents(self, tree_sha, parent_shas, message):
        """Commit stores parent SHAs correctly."""
        author = Author("Test", "test@test.com", 1234567890, "+0000")
        commit = Commit(tree_sha, parent_shas, author, author, message)
        assert commit.parents == parent_shas


class TestTagProperties:
    """Property-based tests for Tag objects."""

    @pytest.mark.property
    @given(
        object_sha=sha1_hex(),
        tag_name=st.text(alphabet=string.ascii_letters + string.digits + "-_.", min_size=1, max_size=50),
        message=st.text(min_size=1, max_size=500)
    )
    def test_tag_sha1_is_valid_hex(self, object_sha, tag_name, message):
        """Tag SHA1 is always a 40-character hex string."""
        author = Author("Test", "test@test.com", 1234567890, "+0000")
        tag = Tag(object_sha, "commit", tag_name, author, message)
        sha = tag.sha1()
        assert len(sha) == 40
        assert all(c in string.hexdigits for c in sha)

    @pytest.mark.property
    @given(
        object_sha=sha1_hex(),
        tag_name=st.text(alphabet=string.ascii_letters + string.digits + "-_.", min_size=1, max_size=50),
        message=st.text(min_size=1, max_size=500)
    )
    def test_tag_type_is_tag(self, object_sha, tag_name, message):
        """Tag type property always returns tag."""
        author = Author("Test", "test@test.com", 1234567890, "+0000")
        tag = Tag(object_sha, "commit", tag_name, author, message)
        assert tag.type == "tag"
