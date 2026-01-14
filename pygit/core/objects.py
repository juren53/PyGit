"""
Git object models implementation.

This module provides the fundamental Git object types: blob, tree, commit, and tag.
Each object follows Git's object model with SHA-1 hashing and proper serialization.
"""

import hashlib
import zlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


class GitObject(ABC):
    """Base class for all Git objects."""

    def __init__(self, data: bytes = None):
        self._data = data or b""
        self._sha1: Optional[str] = None

    @property
    @abstractmethod
    def type(self) -> str:
        """Return the Git object type."""
        pass

    @property
    @abstractmethod
    def data(self) -> bytes:
        """Return the object data."""
        pass

    def sha1(self) -> str:
        """Calculate and return the SHA-1 hash of the object."""
        if self._sha1 is None:
            header = f"{self.type} {len(self.data)}\0".encode()
            self._sha1 = hashlib.sha1(header + self.data).hexdigest()
        return self._sha1

    def serialize(self) -> bytes:
        """Serialize the object for storage in Git's object database."""
        header = f"{self.type} {len(self.data)}\0".encode()
        return zlib.compress(header + self.data)

    def __str__(self) -> str:
        return f"{self.type} {self.sha1()}"

    def __eq__(self, other) -> bool:
        if isinstance(other, GitObject):
            return self.sha1() == other.sha1()
        return False


class Blob(GitObject):
    """Git blob object representing file contents."""

    def __init__(self, content: bytes = b""):
        self.content = content
        super().__init__(content)

    @property
    def type(self) -> str:
        return "blob"

    @property
    def data(self) -> bytes:
        return self.content

    def __str__(self) -> str:
        return f"blob {self.sha1()} ({len(self.content)} bytes)"


class TreeEntry:
    """Represents a single entry in a tree object."""

    def __init__(self, mode: str, name: str, sha1: str):
        self.mode = mode  # e.g., "100644" for file, "100755" for executable, "040000" for directory
        self.name = name
        self.sha1 = sha1

    def serialize(self) -> bytes:
        """Serialize the tree entry."""
        return f"{self.mode} {self.name}\0".encode() + bytes.fromhex(self.sha1)


class Tree(GitObject):
    """Git tree object representing directory contents."""

    def __init__(self, entries: List[TreeEntry] = None):
        self.entries = entries or []
        super().__init__()

    @property
    def type(self) -> str:
        return "tree"

    @property
    def data(self) -> bytes:
        # Sort entries by name for consistent hashing
        sorted_entries = sorted(self.entries, key=lambda e: e.name)
        return b"".join(entry.serialize() for entry in sorted_entries)

    def add_entry(self, mode: str, name: str, sha1: str):
        """Add an entry to the tree."""
        self.entries.append(TreeEntry(mode, name, sha1))
        self._sha1 = None  # Invalidate cache

    def get_entry(self, name: str) -> Optional[TreeEntry]:
        """Get an entry by name."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def __str__(self) -> str:
        return f"tree {self.sha1()} ({len(self.entries)} entries)"


class Author:
    """Represents author/committer information in a commit."""

    def __init__(
        self, name: str, email: str, timestamp: int = None, timezone: str = None
    ):
        self.name = name
        self.email = email
        self.timestamp = timestamp or int(datetime.now().timestamp())
        self.timezone = timezone or "+0000"

    def serialize(self) -> str:
        """Serialize author information for commit data."""
        return f"{self.name} <{self.email}> {self.timestamp} {self.timezone}"


class Commit(GitObject):
    """Git commit object representing a repository state."""

    def __init__(
        self,
        tree_sha1: str,
        parents: List[str] = None,
        author: Author = None,
        committer: Author = None,
        message: str = "",
    ):
        self.tree_sha1 = tree_sha1
        self.parents = parents or []
        self.author = author or Author("", "")
        self.committer = committer or self.author
        self.message = message
        super().__init__()

    @property
    def type(self) -> str:
        return "commit"

    @property
    def data(self) -> bytes:
        lines = [f"tree {self.tree_sha1}"]

        for parent in self.parents:
            lines.append(f"parent {parent}")

        lines.append(f"author {self.author.serialize()}")
        lines.append(f"committer {self.committer.serialize()}")
        lines.append("")
        lines.append(self.message)

        return "\n".join(lines).encode()

    def add_parent(self, parent_sha1: str):
        """Add a parent commit."""
        self.parents.append(parent_sha1)
        self._sha1 = None  # Invalidate cache

    def __str__(self) -> str:
        parent_info = f" +{len(self.parents) - 1}" if len(self.parents) > 1 else ""
        return f"commit {self.sha1()}{parent_info}"


class Tag(GitObject):
    """Git tag object representing annotated tags."""

    def __init__(
        self,
        object_sha1: str,
        object_type: str,
        tag_name: str,
        tagger: Author = None,
        message: str = "",
    ):
        self.object_sha1 = object_sha1
        self.object_type = object_type
        self.tag_name = tag_name
        self.tagger = tagger or Author("", "")
        self.message = message
        super().__init__()

    @property
    def type(self) -> str:
        return "tag"

    @property
    def data(self) -> bytes:
        lines = [
            f"object {self.object_sha1}",
            f"type {self.object_type}",
            f"tag {self.tag_name}",
            f"tagger {self.tagger.serialize()}",
            "",
            self.message,
        ]

        return "\n".join(lines).encode()

    def __str__(self) -> str:
        return f"tag {self.tag_name} -> {self.object_sha1}"
