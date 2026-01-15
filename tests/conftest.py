"""
PyGit Test Configuration and Shared Fixtures

This module provides pytest fixtures and utilities shared across all tests.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pygit.core.objects import Blob, Tree, TreeEntry, Commit, Tag, Author
from pygit.core.repository import Repository
from pygit.core.index import Index


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return PROJECT_ROOT / "tests" / "fixtures"


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that is cleaned up after the test."""
    temp_path = Path(tempfile.mkdtemp(prefix="pygit_test_"))
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_repo_dir(temp_dir: Path) -> Path:
    """Create a temporary directory for a test repository."""
    repo_dir = temp_dir / "test_repo"
    repo_dir.mkdir()
    return repo_dir


# ============================================================================
# Git Object Fixtures
# ============================================================================

@pytest.fixture
def sample_blob() -> Blob:
    """Create a sample blob object."""
    return Blob(b"Hello, World!\n")


@pytest.fixture
def sample_blob_empty() -> Blob:
    """Create an empty blob object."""
    return Blob(b"")


@pytest.fixture
def sample_blob_binary() -> Blob:
    """Create a blob with binary content."""
    return Blob(bytes(range(256)))


@pytest.fixture
def sample_tree_entry() -> TreeEntry:
    """Create a sample tree entry."""
    return TreeEntry(
        mode="100644",
        name="test.txt",
        sha1="e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"  # Empty blob SHA
    )


@pytest.fixture
def sample_tree(sample_tree_entry: TreeEntry) -> Tree:
    """Create a sample tree with one entry."""
    return Tree([sample_tree_entry])


@pytest.fixture
def sample_author() -> Author:
    """Create a sample author."""
    return Author(
        name="Test User",
        email="test@example.com",
        timestamp=1704067200,  # 2024-01-01 00:00:00 UTC
        timezone="-0600"
    )


@pytest.fixture
def sample_commit(sample_tree: Tree, sample_author: Author) -> Commit:
    """Create a sample commit object."""
    return Commit(
        tree_sha1=sample_tree.sha1(),
        parents=[],
        author=sample_author,
        committer=sample_author,
        message="Test commit message"
    )


@pytest.fixture
def sample_tag(sample_commit: Commit, sample_author: Author) -> Tag:
    """Create a sample annotated tag."""
    return Tag(
        object_sha1=sample_commit.sha1(),
        object_type="commit",
        tag_name="v1.0.0",
        tagger=sample_author,
        message="Release v1.0.0"
    )


# ============================================================================
# Repository Fixtures
# ============================================================================

@pytest.fixture
def empty_repo(temp_repo_dir: Path) -> Generator[Repository, None, None]:
    """Create an empty initialized repository."""
    repo = Repository.init(str(temp_repo_dir))
    yield repo


@pytest.fixture
def repo_with_file(empty_repo: Repository, temp_repo_dir: Path) -> Repository:
    """Create a repository with a single file."""
    test_file = temp_repo_dir / "test.txt"
    test_file.write_text("Hello, World!\n")
    return empty_repo


@pytest.fixture
def repo_with_files(empty_repo: Repository, temp_repo_dir: Path) -> Repository:
    """Create a repository with multiple files and directories."""
    # Create files in root
    (temp_repo_dir / "README.md").write_text("# Test Repository\n")
    (temp_repo_dir / "main.py").write_text("print('hello')\n")

    # Create subdirectory with files
    src_dir = temp_repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "module.py").write_text("# Module\n")
    (src_dir / "utils.py").write_text("# Utils\n")

    return empty_repo


# ============================================================================
# Index Fixtures
# ============================================================================

@pytest.fixture
def empty_index(temp_repo_dir: Path) -> Index:
    """Create an empty index."""
    return Index(temp_repo_dir)


@pytest.fixture
def index_with_entries(empty_index: Index, temp_repo_dir: Path) -> Index:
    """Create an index with sample entries."""
    # Create test files
    test_file = temp_repo_dir / "test.txt"
    test_file.write_text("Hello, World!\n")

    # Add to index
    empty_index.add(test_file)
    return empty_index


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_file_content() -> bytes:
    """Return sample file content for testing."""
    return b"This is sample file content.\nLine 2.\nLine 3.\n"


@pytest.fixture
def sample_commit_message() -> str:
    """Return a sample commit message."""
    return "Add new feature\n\nThis commit adds a new feature that does something useful."


@pytest.fixture
def sample_gitignore_content() -> str:
    """Return sample .gitignore content."""
    return """# Python
__pycache__/
*.py[cod]
*.so

# Virtual environments
venv/
.env

# IDE
.vscode/
.idea/
"""


# ============================================================================
# Path Test Data
# ============================================================================

@pytest.fixture
def special_character_paths() -> list:
    """Return a list of paths with special characters for testing."""
    return [
        "normal_file.txt",
        "file with spaces.txt",
        "file-with-dashes.txt",
        "file_with_underscores.txt",
        "file.multiple.dots.txt",
        "UPPERCASE.TXT",
        "MixedCase.Txt",
    ]


@pytest.fixture
def unicode_paths() -> list:
    """Return a list of paths with Unicode characters for testing."""
    return [
        "archivo.txt",           # Spanish
        "fichier.txt",           # French
        "datei.txt",             # German
        "tiedosto.txt",          # Finnish
    ]


# ============================================================================
# GitHub API Mock Data
# ============================================================================

@pytest.fixture
def mock_repo_info() -> Dict[str, Any]:
    """Return mock GitHub repository information."""
    return {
        "id": 123456,
        "name": "test-repo",
        "full_name": "testuser/test-repo",
        "default_branch": "main",
        "private": False,
        "description": "A test repository",
        "clone_url": "https://github.com/testuser/test-repo.git",
        "ssh_url": "git@github.com:testuser/test-repo.git",
    }


@pytest.fixture
def mock_tree_data() -> Dict[str, Any]:
    """Return mock GitHub tree data."""
    return {
        "sha": "abc123",
        "tree": [
            {"path": "README.md", "mode": "100644", "type": "blob", "sha": "def456"},
            {"path": "src", "mode": "040000", "type": "tree", "sha": "ghi789"},
            {"path": "src/main.py", "mode": "100644", "type": "blob", "sha": "jkl012"},
        ],
        "truncated": False,
    }


@pytest.fixture
def mock_branch_info() -> Dict[str, Any]:
    """Return mock GitHub branch information."""
    return {
        "name": "main",
        "commit": {
            "sha": "abc123def456",
            "url": "https://api.github.com/repos/testuser/test-repo/commits/abc123def456",
        },
        "protected": False,
    }


# ============================================================================
# Utility Functions
# ============================================================================

def create_test_file(path: Path, content: str = "test content\n") -> Path:
    """Helper to create a test file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def create_test_files(base_dir: Path, files: Dict[str, str]) -> None:
    """Helper to create multiple test files.

    Args:
        base_dir: Base directory for files
        files: Dict mapping relative paths to content
    """
    for rel_path, content in files.items():
        file_path = base_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)


# ============================================================================
# Platform Detection
# ============================================================================

def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


# Skip decorators for platform-specific tests
skip_on_windows = pytest.mark.skipif(is_windows(), reason="Test not applicable on Windows")
skip_on_linux = pytest.mark.skipif(is_linux(), reason="Test not applicable on Linux")
skip_on_macos = pytest.mark.skipif(is_macos(), reason="Test not applicable on macOS")
windows_only = pytest.mark.skipif(not is_windows(), reason="Windows-only test")
linux_only = pytest.mark.skipif(not is_linux(), reason="Linux-only test")
macos_only = pytest.mark.skipif(not is_macos(), reason="macOS-only test")
