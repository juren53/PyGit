#!/usr/bin/env python3
"""
PyGit CLI - Standalone entry point

This script provides a standalone entry point for PyGit commands
and serves as a replacement for the original PyGitClone.py.
"""

import sys
from pathlib import Path

# Add the pygit package to the Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from pygit.commands.main import main

if __name__ == "__main__":
    # For backward compatibility with PyGitClone.py usage
    if len(sys.argv) >= 2 and sys.argv[1] == "clone":
        # Handle clone command with Git-like syntax
        sys.exit(main())
    elif len(sys.argv) >= 2 and "github.com" in sys.argv[1]:
        # Backward compatibility: treat first arg as repo URL
        new_args = ["pygit", "clone"] + sys.argv[1:]
        sys.argv = new_args
        sys.exit(main())
    else:
        # Normal PyGit usage
        sys.exit(main())
