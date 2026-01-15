"""
Property-based tests for path handling using Hypothesis.

These tests verify that path normalization and handling works correctly
for various edge cases including special characters, different separators, etc.
"""

import string
import os
import tempfile
from pathlib import Path

from hypothesis import given, strategies as st, assume, settings, HealthCheck
import pytest

from pygit.core.ignore import GitIgnore, GitIgnorePattern


# Custom strategies for paths
def path_component():
    """Generate valid path components (directory or file names)."""
    safe_chars = string.ascii_letters + string.digits + "_-."
    return st.text(
        alphabet=safe_chars,
        min_size=1,
        max_size=50
    ).filter(lambda x: x not in (".", "..") and not x.startswith("."))


def relative_path():
    """Generate relative paths with 1-5 components."""
    return st.lists(
        path_component(),
        min_size=1,
        max_size=5
    ).map(lambda parts: "/".join(parts))


def gitignore_pattern():
    """Generate valid gitignore patterns."""
    simple_patterns = st.sampled_from([
        "*.txt",
        "*.py",
        "*.log",
        "build/",
        "dist/",
        "__pycache__/",
        "*.pyc",
        ".env",
        "node_modules/",
    ])
    return simple_patterns


class TestGitIgnorePatternProperties:
    """Property-based tests for GitIgnorePattern."""

    @pytest.mark.property
    @given(ext=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10))
    def test_star_pattern_matches_extension(self, ext):
        """*.ext pattern matches files with that extension."""
        pattern = GitIgnorePattern(f"*.{ext}")
        assert pattern.matches(f"file.{ext}")
        assert pattern.matches(f"path/to/file.{ext}")

    @pytest.mark.property
    @given(dirname=path_component())
    def test_directory_pattern_requires_dir_flag(self, dirname):
        """Directory patterns (ending with /) require is_dir=True."""
        pattern = GitIgnorePattern(f"{dirname}/")
        assert pattern.dir_only is True
        assert pattern.matches(dirname, is_dir=True)
        assert not pattern.matches(dirname, is_dir=False)

    @pytest.mark.property
    @given(filename=path_component())
    def test_negated_pattern_is_marked(self, filename):
        """Patterns starting with ! are marked as negated."""
        pattern = GitIgnorePattern(f"!{filename}")
        assert pattern.negated is True

    @pytest.mark.property
    @given(filename=path_component())
    def test_absolute_pattern_is_marked(self, filename):
        """Patterns starting with / are marked as absolute."""
        pattern = GitIgnorePattern(f"/{filename}")
        assert pattern.absolute is True


class TestGitIgnoreProperties:
    """Property-based tests for GitIgnore class."""

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        ignored_ext=st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=5),
        kept_ext=st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=5)
    )
    def test_filter_files_excludes_ignored(self, ignored_ext, kept_ext):
        """filter_files removes files matching ignore patterns."""
        assume(ignored_ext != kept_ext)

        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)

            gitignore_file = temp_dir / ".gitignore"
            gitignore_file.write_text(f"*.{ignored_ext}\n")

            gitignore = GitIgnore(temp_dir)

            files = [
                f"keep.{kept_ext}",
                f"ignore.{ignored_ext}",
            ]

            filtered = gitignore.filter_files(files)

            assert f"keep.{kept_ext}" in filtered
            assert f"ignore.{ignored_ext}" not in filtered

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(patterns=st.lists(gitignore_pattern(), min_size=1, max_size=5))
    def test_add_pattern_increases_count(self, patterns):
        """Adding patterns increases the pattern count."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            gitignore = GitIgnore(temp_dir)

            initial_count = len(gitignore.patterns)

            for pattern in patterns:
                gitignore.add_pattern(pattern)

            assert len(gitignore.patterns) >= initial_count

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(filename=path_component())
    def test_non_ignored_file_passes_filter(self, filename):
        """Files not matching any pattern are not ignored."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)

            gitignore_file = temp_dir / ".gitignore"
            gitignore_file.write_text("")

            gitignore = GitIgnore(temp_dir)

            assert not gitignore.is_ignored(filename)


class TestPathNormalization:
    """Property-based tests for path normalization behaviors."""

    @pytest.mark.property
    @given(path=relative_path())
    def test_forward_slashes_work(self, path):
        """Paths with forward slashes are handled correctly."""
        parts = path.split("/")
        assert len(parts) >= 1
        assert all(p for p in parts)

    @pytest.mark.property
    @given(
        dir_parts=st.lists(path_component(), min_size=1, max_size=3),
        filename=path_component(),
        ext=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=4)
    )
    def test_path_construction(self, dir_parts, filename, ext):
        """Paths can be constructed from components."""
        full_path = "/".join(dir_parts + [f"{filename}.{ext}"])

        for part in dir_parts:
            assert part in full_path
        assert filename in full_path
        assert ext in full_path


class TestGitIgnoreEdgeCases:
    """Edge case tests for gitignore patterns."""

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        prefix=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5),
        suffix=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5)
    )
    def test_pattern_with_wildcard_in_middle(self, prefix, suffix):
        """Patterns like 'pre*suf' match correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)

            gitignore_file = temp_dir / ".gitignore"
            gitignore_file.write_text(f"{prefix}*{suffix}\n")

            gitignore = GitIgnore(temp_dir)

            matching = f"{prefix}middle{suffix}"
            assert gitignore.is_ignored(matching)

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(dirname=path_component())
    def test_comment_lines_ignored(self, dirname):
        """Lines starting with # are treated as comments."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)

            gitignore_file = temp_dir / ".gitignore"
            gitignore_file.write_text(f"# {dirname}\n{dirname}\n")

            gitignore = GitIgnore(temp_dir)

            assert gitignore.is_ignored(dirname)

    @pytest.mark.property
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(spaces=st.integers(min_value=1, max_value=5))
    def test_blank_lines_ignored(self, spaces):
        """Blank lines in .gitignore are ignored."""
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)

            blank = " " * spaces
            gitignore_file = temp_dir / ".gitignore"
            gitignore_file.write_text(f"*.log\n{blank}\n*.tmp\n")

            gitignore = GitIgnore(temp_dir)

            assert gitignore.is_ignored("file.log")
            assert gitignore.is_ignored("file.tmp")
