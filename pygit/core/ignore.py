"""
Git ignore pattern handling.

This module provides .gitignore pattern matching and file filtering
functionality for PyGit operations.
"""

import os
import re
from pathlib import Path
from typing import List, Set, Pattern, Optional
from ..utils.logging import get_logger


class GitIgnorePattern:
    """Represents a single .gitignore pattern."""

    def __init__(self, pattern: str, source_file: str = None):
        self.pattern = pattern
        self.source_file = source_file
        self.negated = pattern.startswith("!")
        self.dir_only = pattern.endswith("/")

        # Remove negation and directory markers for processing
        clean_pattern = pattern
        if self.negated:
            clean_pattern = clean_pattern[1:]
        if self.dir_only:
            clean_pattern = clean_pattern[:-1]

        # Handle absolute paths
        self.absolute = clean_pattern.startswith("/")
        if self.absolute:
            clean_pattern = clean_pattern[1:]

        # Convert to regex pattern
        self.regex = self._pattern_to_regex(clean_pattern)

    def _pattern_to_regex(self, pattern: str) -> Pattern:
        """Convert glob pattern to regex."""
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)

        # Convert escaped wildcards back to regex equivalents
        escaped = escaped.replace(r"\*", ".*")
        escaped = escaped.replace(r"\?", ".")

        # Handle character ranges like [abc]
        escaped = escaped.replace(r"\[", "[").replace(r"\]", "]")

        # Handle ** for recursive matching
        escaped = escaped.replace(r"\*\*/\*", ".*/.*")
        escaped = escaped.replace(r"\*\*", ".*")

        # If pattern doesn't start with anchor, match anywhere in path
        if not self.absolute and not pattern.startswith("**"):
            if "/" in escaped:
                # Complex pattern - need to handle directory structure
                escaped = f"(^|.*/)({escaped})(/.*|$)"
            else:
                # Simple pattern - can match anywhere in the path
                escaped = f"(^|.*/)({escaped})(/.*|$)"
        else:
            # Absolute pattern - match from beginning
            escaped = f"^{escaped}(/.*)?$"

        return re.compile(escaped, flags=re.IGNORECASE if os.name == "nt" else 0)

    def matches(self, path: str, is_dir: bool = False) -> bool:
        """Check if this pattern matches the given path."""
        if self.dir_only and not is_dir:
            return False

        match = self.regex.match(path)
        return bool(match)

    def __str__(self) -> str:
        return (
            f"{'!' if self.negated else ''}{self.pattern}{'/' if self.dir_only else ''}"
        )


class GitIgnore:
    """Git ignore file manager."""

    def __init__(self, repository_root: Path):
        self.repository_root = repository_root
        self.patterns: List[GitIgnorePattern] = []
        self.logger = get_logger()
        self._load_ignore_files()

    def _load_ignore_files(self):
        """Load ignore files from various locations."""
        self.patterns.clear()

        # Load repository-level .gitignore
        self._load_ignore_file(self.repository_root / ".gitignore")

        # Load .git/info/exclude
        git_dir = self.repository_root / ".git"
        if git_dir.exists():
            self._load_ignore_file(git_dir / "info" / "exclude")

        # Load user-level gitignore
        home_gitignore = Path.home() / ".gitignore"
        self._load_ignore_file(home_gitignore)

    def _load_ignore_file(self, ignore_file: Path):
        """Load patterns from a single ignore file."""
        if not ignore_file.exists() or not ignore_file.is_file():
            return

        try:
            lines = ignore_file.read_text(encoding="utf-8", errors="ignore")

            for line_num, line in enumerate(lines.splitlines(), 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                try:
                    pattern = GitIgnorePattern(line, str(ignore_file))
                    self.patterns.append(pattern)

                except Exception as e:
                    self.logger.debug(
                        f"Invalid ignore pattern '{line}' in {ignore_file}:{line_num}: {e}"
                    )

        except Exception as e:
            self.logger.warning(f"Could not read ignore file {ignore_file}: {e}")

    def is_ignored(self, path: str, is_dir: bool = False) -> bool:
        """Check if a path is ignored."""
        # Convert to relative path from repository root
        if os.path.isabs(path):
            try:
                rel_path = str(Path(path).relative_to(self.repository_root))
            except ValueError:
                # Path is outside repository - not ignored by our rules
                return False
        else:
            rel_path = path

        # Normalize path separators
        rel_path = rel_path.replace(os.sep, "/")

        # Check each pattern in order
        ignored = False

        for pattern in self.patterns:
            if pattern.matches(rel_path, is_dir):
                if pattern.negated:
                    ignored = False
                else:
                    ignored = True

        return ignored

    def filter_files(self, files: List[str]) -> List[str]:
        """Filter a list of files, removing ignored ones."""
        return [f for f in files if not self.is_ignored(f, False)]

    def filter_paths(self, paths: List[Path]) -> List[Path]:
        """Filter a list of Path objects, removing ignored ones."""
        result = []
        for path in paths:
            try:
                rel_path = str(path.relative_to(self.repository_root))
                if not self.is_ignored(rel_path, path.is_dir()):
                    result.append(path)
            except ValueError:
                # Path is outside repository - keep it
                result.append(path)

        return result

    def get_ignored_files(self, paths: List[Path]) -> List[Path]:
        """Get list of paths that are ignored."""
        ignored = []
        for path in paths:
            try:
                rel_path = str(path.relative_to(self.repository_root))
                if self.is_ignored(rel_path, path.is_dir()):
                    ignored.append(path)
            except ValueError:
                # Path is outside repository - not ignored
                pass

        return ignored

    def add_pattern(self, pattern: str):
        """Add a new ignore pattern (in-memory only)."""
        try:
            git_pattern = GitIgnorePattern(pattern)
            self.patterns.append(git_pattern)
        except Exception as e:
            self.logger.error(f"Invalid ignore pattern '{pattern}': {e}")

    def reload(self):
        """Reload ignore files from disk."""
        self._load_ignore_files()

    def __contains__(self, path: str) -> bool:
        """Check if path is ignored using 'in' operator."""
        return self.is_ignored(path)

    def __str__(self) -> str:
        return f"GitIgnore({len(self.patterns)} patterns)"
