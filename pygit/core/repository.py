"""
Repository management and Git directory structure implementation.

This module provides the Repository class for managing Git repositories,
including initialization, object storage, and Git directory operations.
"""

import os
import json
import zlib
from pathlib import Path
from typing import Optional, Dict, List, Any
from .objects import GitObject, Blob, Tree, Commit, Tag


class Repository:
    """Git repository management class."""

    def __init__(self, path: str = ".", create: bool = False):
        self.path = Path(path).resolve()
        self.git_dir = self.path / ".git"

        if create:
            self._init_git_dir()
        elif not self.git_dir.exists():
            raise ValueError(f"Not a git repository: {self.path}")

    def _init_git_dir(self):
        """Initialize the .git directory structure."""
        directories = [
            "objects",
            "objects/pack",
            "objects/info",
            "refs",
            "refs/heads",
            "refs/tags",
            "logs",
            "logs/refs",
            "logs/refs/heads",
            "hooks",
            "info",
        ]

        for dir_name in directories:
            (self.git_dir / dir_name).mkdir(parents=True, exist_ok=True)

        # Create required files
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (self.git_dir / "config").write_text(self._default_config())
        (self.git_dir / "description").write_text("\n")

        # Note: Don't create empty index file - Git expects either no index
        # or a properly formatted one. Index will be created when needed.

    def _default_config(self) -> str:
        """Return default repository configuration."""
        return """[core]
	repositoryformatversion = 0
	filemode = false
	bare = false
	logallrefupdates = true
"""

    @classmethod
    def init(cls, path: str = ".") -> "Repository":
        """Initialize a new git repository."""
        return cls(path, create=True)

    @property
    def is_bare(self) -> bool:
        """Check if this is a bare repository."""
        return self.git_dir == self.path

    def object_path(self, sha1: str) -> Path:
        """Get the file path for a Git object."""
        if len(sha1) != 40:
            raise ValueError("Invalid SHA-1 hash")

        obj_dir = self.git_dir / "objects" / sha1[:2]
        obj_file = obj_dir / sha1[2:]
        return obj_file

    def store_object(self, obj: GitObject) -> str:
        """Store a Git object in the object database."""
        obj_path = self.object_path(obj.sha1())

        if obj_path.exists():
            return obj.sha1()  # Object already exists

        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(obj.serialize())

        return obj.sha1()

    def get_object(self, sha1: str) -> Optional[GitObject]:
        """Retrieve a Git object from the object database."""
        obj_path = self.object_path(sha1)

        if not obj_path.exists():
            return None

        try:
            compressed_data = obj_path.read_bytes()
            data = zlib.decompress(compressed_data)

            # Parse header to determine object type
            null_pos = data.find(b"\0")
            if null_pos == -1:
                raise ValueError("Invalid object format")

            header = data[:null_pos].decode()
            obj_data = data[null_pos + 1 :]

            if " " not in header:
                raise ValueError("Invalid object header")

            obj_type, size_str = header.split(" ", 1)
            try:
                size = int(size_str)
            except ValueError:
                raise ValueError("Invalid object size")

            if len(obj_data) != size:
                raise ValueError("Object size mismatch")

            # Create appropriate object type
            if obj_type == "blob":
                return Blob(obj_data)
            elif obj_type == "tree":
                return self._parse_tree(obj_data)
            elif obj_type == "commit":
                return self._parse_commit(obj_data)
            elif obj_type == "tag":
                return self._parse_tag(obj_data)
            else:
                raise ValueError(f"Unknown object type: {obj_type}")

        except Exception as e:
            raise ValueError(f"Failed to read object {sha1}: {e}")

    def _parse_tree(self, data: bytes) -> Tree:
        """Parse tree object data."""
        from .objects import TreeEntry

        entries = []
        pos = 0

        while pos < len(data):
            # Find the null byte that separates mode from name
            null_pos = data.find(b"\0", pos)
            if null_pos == -1:
                break

            # Parse mode and name
            mode_name = data[pos:null_pos].decode()
            mode, name = mode_name.split(" ", 1)

            # Get SHA1 (20 bytes after null)
            sha1_bytes = data[null_pos + 1 : null_pos + 21]
            sha1 = sha1_bytes.hex()

            entries.append(TreeEntry(mode, name, sha1))
            pos = null_pos + 21

        return Tree(entries)

    def _parse_commit(self, data: bytes) -> Commit:
        """Parse commit object data."""
        from .objects import Author

        lines = data.decode().split("\n")

        tree_sha1 = ""
        parents = []
        author = None
        committer = None
        message_start = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            if line.startswith("tree "):
                tree_sha1 = line[5:]
            elif line.startswith("parent "):
                parents.append(line[7:])
            elif line.startswith("author "):
                author = self._parse_author(line[7:])
            elif line.startswith("committer "):
                committer = self._parse_author(line[9:])
            elif line == "":
                message_start = i + 1
                break

            i += 1

        message = "\n".join(lines[message_start:])

        return Commit(tree_sha1, parents, author, committer, message)

    def _parse_author(self, author_str: str) -> "Author":
        """Parse author/committer string."""
        from .objects import Author

        # Format: Name <email> timestamp timezone
        parts = author_str.rsplit(" ", 2)
        if len(parts) != 3:
            return Author("", "")

        timestamp = int(parts[1])
        timezone = parts[2]
        name_email = parts[0]

        if "<" in name_email and ">" in name_email:
            name = name_email[: name_email.index("<")].strip()
            email = name_email[
                name_email.index("<") + 1 : name_email.index(">")
            ].strip()
        else:
            name = name_email
            email = ""

        return Author(name, email, timestamp, timezone)

    def _parse_tag(self, data: bytes) -> Tag:
        """Parse tag object data."""
        from .objects import Author

        lines = data.decode().split("\n")

        object_sha1 = ""
        object_type = ""
        tag_name = ""
        tagger = None
        message_start = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            if line.startswith("object "):
                object_sha1 = line[7:]
            elif line.startswith("type "):
                object_type = line[5:]
            elif line.startswith("tag "):
                tag_name = line[4:]
            elif line.startswith("tagger "):
                tagger = self._parse_author(line[7:])
            elif line == "":
                message_start = i + 1
                break

            i += 1

        message = "\n".join(lines[message_start:])

        return Tag(object_sha1, object_type, tag_name, tagger, message)

    def get_head(self) -> Optional[str]:
        """Get the current HEAD reference."""
        head_file = self.git_dir / "HEAD"

        if not head_file.exists():
            return None

        content = head_file.read_text().strip()

        if content.startswith("ref: "):
            ref_path = self.git_dir / content[5:]
            if ref_path.exists():
                return ref_path.read_text().strip()
            return None
        else:
            # Detached HEAD
            return content

    def set_head(self, ref_or_sha1: str):
        """Set the HEAD reference."""
        head_file = self.git_dir / "HEAD"

        if ref_or_sha1.startswith("refs/"):
            head_file.write_text(f"ref: {ref_or_sha1}\n")
        else:
            # Detached HEAD
            head_file.write_text(f"{ref_or_sha1}\n")

    def __str__(self) -> str:
        status = "bare" if self.is_bare else "normal"
        return f"Repository({self.path}, {status})"
