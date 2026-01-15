"""
Git index (staging area) management.

This module provides functionality for managing the Git index,
including staging files, tracking changes, and preparing commits.
"""

import os
import sys
import struct
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
from .objects import Blob, Tree, TreeEntry
from .repository import Repository
from ..utils.logging import get_logger


class IndexEntry:
    """Represents a single entry in the Git index."""

    # File modes
    MODE_DIRECTORY = 0o040000
    MODE_FILE = 0o100644
    MODE_EXECUTABLE = 0o100755
    MODE_SYMLINK = 0o120000

    def __init__(
        self,
        path: str,
        sha1: str,
        mode: int = MODE_FILE,
        size: int = 0,
        mtime: float = None,
        ctime: float = None,
    ):
        self.path = path
        self.sha1 = sha1
        self.mode = mode
        self.size = size

        # Set safe default values
        self.mtime = 0
        self.ctime = 0
        self.dev = 0
        self.ino = 0
        self.uid = 0
        self.gid = 0

        # Only get file stats if path exists and is safe
        try:
            if os.path.exists(path):
                stat = os.stat(path)
                self.mtime = int(stat.st_mtime) & 0xFFFFFFFF
                self.ctime = int(stat.st_ctime) & 0xFFFFFFFF
                self.dev = stat.st_dev & 0xFFFFFFFF if stat.st_dev <= 0xFFFFFFFF else 0
                self.ino = stat.st_ino & 0xFFFFFFFF if stat.st_ino <= 0xFFFFFFFF else 0
                self.uid = stat.st_uid & 0xFFFFFFFF if stat.st_uid <= 0xFFFFFFFF else 0
                self.gid = stat.st_gid & 0xFFFFFFFF if stat.st_gid <= 0xFFFFFFFF else 0
        except (OSError, OverflowError):
            # Use defaults if stat fails
            pass

        # Git specific fields
        self.flags = min(len(path), 0xFFFF)  # Ensure flags fit in 16-bit

    def serialize(self) -> bytes:
        """Serialize the index entry for writing to the index file."""
        # Entry structure (62 bytes + path + null padding)
        data = bytearray(66)  # Need 66 bytes for header

        # Write timestamps (ensure they fit in 32-bit unsigned)
        ctime_val = int(self.ctime) if int(self.ctime) <= 0xFFFFFFFF else 0
        mtime_val = int(self.mtime) if int(self.mtime) <= 0xFFFFFFFF else 0
        struct.pack_into(">I", data, 0, ctime_val)
        struct.pack_into(">I", data, 4, mtime_val)

        # Write device and inode
        struct.pack_into(">I", data, 8, self.dev)
        struct.pack_into(">I", data, 12, self.ino)

        # Write mode and uid/gid
        struct.pack_into(">I", data, 16, self.mode)
        struct.pack_into(">I", data, 20, self.uid)
        struct.pack_into(">I", data, 24, self.gid)

        # Write SHA1
        sha1_bytes = bytes.fromhex(self.sha1)
        struct.pack_into("20s", data, 40, sha1_bytes)

        # Write flags and size
        struct.pack_into(">H", data, 60, self.flags)
        struct.pack_into(">I", data, 62, self.size)

        # Add path with null terminator and pad to 8-byte boundary
        path_bytes = self.path.encode("utf-8") + b"\x00"
        entry_size = 62 + len(path_bytes)
        padding_len = (8 - entry_size % 8) % 8
        path_bytes += b"\x00" * padding_len

        return bytes(data + path_bytes)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple["IndexEntry", int]:
        """Deserialize an index entry from the index file."""
        # Read basic fields
        ctime = struct.unpack_from(">I", data, offset)[0]
        mtime = struct.unpack_from(">I", data, offset + 4)[0]
        dev = struct.unpack_from(">I", data, offset + 8)[0]
        ino = struct.unpack_from(">I", data, offset + 12)[0]
        mode = struct.unpack_from(">I", data, offset + 16)[0]
        uid = struct.unpack_from(">I", data, offset + 20)[0]
        gid = struct.unpack_from(">I", data, offset + 24)[0]
        size = struct.unpack_from(">I", data, offset + 62)[0]
        flags = struct.unpack_from(">H", data, offset + 60)[0]

        # Read SHA1
        sha1_bytes = struct.unpack_from("20s", data, offset + 40)[0]
        sha1 = sha1_bytes.hex()

        # Read path
        path_start = offset + 62
        path_end = data.find(b"\x00", path_start)
        path = data[path_start:path_end].decode("utf-8")

        entry = cls(path, sha1, mode, size, mtime, ctime)
        entry.dev = dev
        entry.ino = ino
        entry.uid = uid
        entry.gid = gid
        entry.flags = flags

        # Calculate next entry offset (pad to 8-byte boundary)
        entry_size = 62 + path_end - path_start + 1
        padding = (8 - entry_size % 8) % 8
        next_offset = offset + entry_size + padding

        return entry, next_offset

    def __eq__(self, other) -> bool:
        if not isinstance(other, IndexEntry):
            return False
        return self.path == other.path and self.sha1 == other.sha1


class Index:
    """Git index (staging area) management."""

    def __init__(self, repository: Repository):
        self.repository = repository
        self.entries: Dict[str, IndexEntry] = {}
        self.logger = get_logger()
        self._load()

    def _load(self):
        """Load the index file."""
        index_path = self.repository.git_dir / "index"

        if not index_path.exists():
            self.logger.debug("No index file found, creating empty index")
            return

        try:
            with index_path.open("rb") as f:
                data = f.read()

            if len(data) < 12:
                raise ValueError("Index file too small")

            # Read header
            signature = data[:4]
            if signature != b"DIRC":
                raise ValueError(f"Invalid index signature: {signature}")

            version = struct.unpack_from(">I", data, 4)[0]
            if version != 2:
                raise ValueError(f"Unsupported index version: {version}")

            entry_count = struct.unpack_from(">I", data, 8)[0]

            # Read entries
            offset = 12
            for i in range(entry_count):
                entry, offset = IndexEntry.deserialize(data, offset)
                self.entries[entry.path] = entry

            self.logger.debug(f"Loaded {len(self.entries)} entries from index")

        except (ValueError, struct.error, UnicodeDecodeError) as e:
            self.logger.error(f"Error loading index: {e}")
            self.logger.warning("Index appears corrupted, creating empty index")
            self.entries = {}
            # Backup corrupted index
            try:
                backup_path = index_path.with_suffix(".backup")
                index_path.rename(backup_path)
                self.logger.info(f"Corrupted index backed up to {backup_path}")
            except Exception as backup_e:
                self.logger.error(f"Could not backup corrupted index: {backup_e}")
        except Exception as e:
            self.logger.error(f"Unexpected error loading index: {e}")
            self.entries = {}

    def save(self):
        """Save the index to disk."""
        index_path = self.repository.git_dir / "index"

        # Prepare header
        header = struct.pack(">4sII", b"DIRC", 2, len(self.entries))

        # Serialize entries
        entries_data = bytearray()
        for entry in sorted(self.entries.values(), key=lambda e: e.path):
            entries_data.extend(entry.serialize())

        # Write file
        index_path.write_bytes(header + entries_data)
        self.logger.debug(f"Saved {len(self.entries)} entries to index")

    def add(self, path: str, repo_path: Path = None) -> bool:
        """Add a file to the index."""
        if repo_path is None:
            repo_path = self.repository.path

        full_path = repo_path / path

        if not full_path.exists():
            self.logger.error(f"File not found: {path}")
            return False

        if not full_path.is_file():
            self.logger.error(f"Not a file: {path}")
            return False

        try:
            # Read file content and create blob
            content = full_path.read_bytes()
            blob = Blob(content)
            sha1 = self.repository.store_object(blob)

            # Determine file mode
            # Note: On Windows, os.access(X_OK) is unreliable (returns True for all files)
            # so we only check executable status on Unix-like systems
            mode = IndexEntry.MODE_FILE
            if sys.platform != 'win32' and os.access(full_path, os.X_OK):
                mode = IndexEntry.MODE_EXECUTABLE

            # Create index entry
            entry = IndexEntry(
                path=path,
                sha1=sha1,
                mode=mode,
                size=len(content),
                mtime=full_path.stat().st_mtime,
                ctime=full_path.stat().st_ctime,
            )

            self.entries[path] = entry
            self.logger.object_operation("add", "blob", sha1)
            return True

        except Exception as e:
            self.logger.error(f"Error adding {path} to index: {e}")
            return False

    def remove(self, path: str) -> bool:
        """Remove a file from the index."""
        if path in self.entries:
            del self.entries[path]
            self.logger.debug(f"Removed {path} from index")
            return True
        return False

    def clear(self):
        """Clear all entries from the index."""
        self.entries.clear()
        self.logger.debug("Cleared index")

    def get_entry(self, path: str) -> Optional[IndexEntry]:
        """Get an index entry by path."""
        return self.entries.get(path)

    def list_entries(self) -> List[IndexEntry]:
        """List all entries in the index."""
        return list(self.entries.values())

    def is_tracked(self, path: str) -> bool:
        """Check if a file is tracked in the index."""
        return path in self.entries

    def get_modified_files(self, repo_path: Path = None) -> Dict[str, str]:
        """Get modified files compared to working directory."""
        if repo_path is None:
            repo_path = self.repository.path

        modified = {}

        for path, entry in self.entries.items():
            full_path = repo_path / path

            if not full_path.exists():
                modified[path] = "deleted"
                continue

            # Check if file was modified
            current_mtime = full_path.stat().st_mtime
            current_size = full_path.stat().st_size

            if current_mtime != entry.mtime or current_size != entry.size:
                # Check if content actually changed
                try:
                    content = full_path.read_bytes()
                    blob = Blob(content)
                    if blob.sha1() != entry.sha1:
                        modified[path] = "modified"
                except:
                    modified[path] = "modified"

        return modified

    def write_tree(self) -> str:
        """Write the index content as a tree and return the SHA1."""
        tree_entries = []

        # Group entries by directory
        directories: Dict[str, List[IndexEntry]] = {}

        for entry in self.entries.values():
            parts = Path(entry.path).parts

            if len(parts) == 1:
                # Root-level file
                tree_entries.append(
                    TreeEntry(
                        mode=f"{entry.mode:06o}", name=entry.path, sha1=entry.sha1
                    )
                )
            else:
                # File in subdirectory
                dir_path = "/".join(parts[:-1])
                if dir_path not in directories:
                    directories[dir_path] = []

                directories[dir_path].append(entry)

        # Process subdirectories recursively
        for dir_path, entries in directories.items():
            subtree = self._create_subtree(dir_path, entries)
            subtree_sha1 = self.repository.store_object(subtree)

            # Add subtree entry to parent tree
            parent_dir, dir_name = (
                dir_path.rsplit("/", 1) if "/" in dir_path else ("", dir_path)
            )
            tree_entries.append(
                TreeEntry(mode="040000", name=dir_name, sha1=subtree_sha1)
            )

        # Create root tree
        root_tree = Tree(tree_entries)
        root_sha1 = self.repository.store_object(root_tree)

        self.logger.operation(
            "write_tree", {"sha1": root_sha1, "entries": len(tree_entries)}
        )
        return root_sha1

    def _create_subtree(self, dir_path: str, entries: List[IndexEntry]) -> Tree:
        """Create a tree for a subdirectory."""
        tree_entries = []

        # Group files by subdirectory
        subdirs: Dict[str, List[IndexEntry]] = {}

        for entry in entries:
            relative_path = entry.path
            if dir_path:
                relative_path = relative_path[len(dir_path) + 1 :]

            parts = relative_path.split("/")

            if len(parts) == 1:
                # File in this directory
                tree_entries.append(
                    TreeEntry(mode=f"{entry.mode:06o}", name=parts[0], sha1=entry.sha1)
                )
            else:
                # File in subdirectory
                subdir = parts[0]
                if subdir not in subdirs:
                    subdirs[subdir] = []
                subdirs[subdir].append(entry)

        # Process subdirectories
        for subdir, sub_entries in subdirs.items():
            sub_path = f"{dir_path}/{subdir}" if dir_path else subdir
            subtree = self._create_subtree(sub_path, sub_entries)
            subtree_sha1 = self.repository.store_object(subtree)
            tree_entries.append(
                TreeEntry(mode="040000", name=subdir, sha1=subtree_sha1)
            )

        return Tree(tree_entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, path: str) -> bool:
        return path in self.entries
