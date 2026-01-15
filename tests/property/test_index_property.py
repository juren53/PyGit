"""
Property-based tests for Index operations using Hypothesis.

These tests verify that index operations behave correctly for
various inputs and edge cases.
"""

import string
import tempfile
from pathlib import Path

from hypothesis import given, strategies as st, assume, settings, HealthCheck, Verbosity
import pytest

from pygit.core.index import Index, IndexEntry
from pygit.core.repository import Repository


# Windows reserved device names that cannot be used as filenames
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


# Custom strategies
def valid_filename():
    """Generate valid filenames."""
    safe_chars = string.ascii_letters + string.digits + "_-."
    return st.text(
        alphabet=safe_chars,
        min_size=1,
        max_size=50
    ).filter(lambda x: x not in (".", "..") and x.upper() not in WINDOWS_RESERVED)


def sha1_hex():
    """Generate valid SHA1 hex strings."""
    return st.text(
        alphabet=string.hexdigits[:16],
        min_size=40,
        max_size=40
    )


def file_content():
    """Generate file content (text or binary)."""
    return st.binary(min_size=0, max_size=5000)


class TestIndexEntryProperties:
    """Property-based tests for IndexEntry."""

    @pytest.mark.property
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        path=valid_filename(),
        sha=sha1_hex(),
        size=st.integers(min_value=0, max_value=2**31-1)
    )
    def test_entry_stores_properties(self, path, sha, size):
        """IndexEntry correctly stores all properties."""
        entry = IndexEntry(
            path=path,
            sha1=sha,
            mode=IndexEntry.MODE_FILE,
            size=size
        )
        assert entry.path == path
        assert entry.sha1 == sha
        assert entry.mode == IndexEntry.MODE_FILE
        assert entry.size == size

    @pytest.mark.property
    @given(path=valid_filename(), sha=sha1_hex())
    def test_entry_equality(self, path, sha):
        """Two entries with same path and SHA are equal."""
        entry1 = IndexEntry(path, sha)
        entry2 = IndexEntry(path, sha)
        assert entry1 == entry2

    @pytest.mark.property
    @given(
        path=valid_filename(),
        sha1=sha1_hex(),
        sha2=sha1_hex()
    )
    def test_different_sha_not_equal(self, path, sha1, sha2):
        """Entries with different SHAs are not equal."""
        assume(sha1 != sha2)
        entry1 = IndexEntry(path, sha1)
        entry2 = IndexEntry(path, sha2)
        assert entry1 != entry2

    @pytest.mark.property
    @given(
        path1=valid_filename(),
        path2=valid_filename(),
        sha=sha1_hex()
    )
    def test_different_path_not_equal(self, path1, path2, sha):
        """Entries with different paths are not equal."""
        assume(path1 != path2)
        entry1 = IndexEntry(path1, sha)
        entry2 = IndexEntry(path2, sha)
        assert entry1 != entry2

    @pytest.mark.property
    @given(path=valid_filename(), sha=sha1_hex())
    def test_serialization_produces_bytes(self, path, sha):
        """Serialization always produces bytes."""
        entry = IndexEntry(path, sha)
        serialized = entry.serialize()
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0


class TestIndexOperations:
    """Property-based tests for Index operations."""

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filenames=st.lists(valid_filename(), min_size=1, max_size=10, unique=True))
    def test_add_multiple_files(self, filenames):
        """Adding multiple files increases index length correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            added_count = 0
            for filename in filenames:
                file_path = temp_dir / filename
                file_path.write_text(f"Content of {filename}")

                if index.add(filename, temp_dir):
                    added_count += 1

            assert len(index) == added_count

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=valid_filename())
    def test_add_creates_entry(self, filename):
        """Adding a file creates an entry in the index."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            file_path = temp_dir / filename
            file_path.write_text(f"Content of {filename}")

            result = index.add(filename, temp_dir)

            assert result is True
            assert filename in index
            assert index.is_tracked(filename)

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=valid_filename())
    def test_remove_removes_entry(self, filename):
        """Removing a file removes the entry from the index."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            file_path = temp_dir / filename
            file_path.write_text(f"Content of {filename}")
            index.add(filename, temp_dir)

            assert filename in index

            result = index.remove(filename)

            assert result is True
            assert filename not in index

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=valid_filename())
    def test_get_entry_returns_correct_entry(self, filename):
        """get_entry returns the correct entry for a path."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            file_path = temp_dir / filename
            file_path.write_text(f"Content of {filename}")
            index.add(filename, temp_dir)

            entry = index.get_entry(filename)

            assert entry is not None
            assert entry.path == filename

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=valid_filename())
    def test_nonexistent_file_not_added(self, filename):
        """Adding a nonexistent file returns False."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            result = index.add(filename, temp_dir)

            assert result is False
            assert filename not in index

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filenames=st.lists(valid_filename(), min_size=2, max_size=5, unique=True))
    def test_clear_removes_all(self, filenames):
        """Clear removes all entries from index."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            for filename in filenames:
                file_path = temp_dir / filename
                file_path.write_text(f"Content of {filename}")
                index.add(filename, temp_dir)

            assert len(index) > 0

            index.clear()

            assert len(index) == 0


class TestIndexContentTracking:
    """Property-based tests for content tracking."""

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        filename=valid_filename(),
        content1=st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=100),
        content2=st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=100)
    )
    def test_modified_file_detected(self, filename, content1, content2):
        """Modified files are detected correctly."""
        assume(content1 != content2)

        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            file_path = temp_dir / filename
            file_path.write_text(content1)
            index.add(filename, temp_dir)
            index.save()

            file_path.write_text(content2)

            modified = index.get_modified_files(temp_dir)

            assert filename in modified

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=valid_filename())
    def test_deleted_file_detected(self, filename):
        """Deleted files are detected correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            file_path = temp_dir / filename
            file_path.write_text(f"Content of {filename}")
            index.add(filename, temp_dir)

            file_path.unlink()

            modified = index.get_modified_files(temp_dir)

            assert filename in modified
            assert modified[filename] == "deleted"


class TestIndexWriteTree:
    """Property-based tests for write_tree operation."""

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filenames=st.lists(valid_filename(), min_size=1, max_size=5, unique=True))
    def test_write_tree_produces_valid_sha(self, filenames):
        """write_tree always produces a valid SHA1."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))
            index = Index(repo)

            for filename in filenames:
                file_path = temp_dir / filename
                file_path.write_text(f"Content of {filename}")
                index.add(filename, temp_dir)

            tree_sha = index.write_tree()

            assert len(tree_sha) == 40
            assert all(c in string.hexdigits for c in tree_sha)

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filenames=st.lists(valid_filename(), min_size=1, max_size=5, unique=True))
    def test_write_tree_is_consistent(self, filenames):
        """write_tree produces same SHA for same content."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            repo = Repository.init(str(temp_dir))

            for filename in filenames:
                file_path = temp_dir / filename
                file_path.write_text(f"Fixed content for {filename}")

            index1 = Index(repo)
            for filename in filenames:
                index1.add(filename, temp_dir)
            tree_sha1 = index1.write_tree()

            index2 = Index(repo)
            for filename in filenames:
                index2.add(filename, temp_dir)
            tree_sha2 = index2.write_tree()

            assert tree_sha1 == tree_sha2
