"""
PyGit - A pure Python Git implementation

This package provides a complete Git replacement implemented in Python,
starting with GitHub-only support and expanding to a comprehensive Git alternative.
"""

__version__ = "0.0.4"
__author__ = "juren53"

from .core.repository import Repository
from .core.objects import GitObject, Blob, Tree, Commit, Tag

__all__ = ["Repository", "GitObject", "Blob", "Tree", "Commit", "Tag"]
