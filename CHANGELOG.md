# Changelog

All notable changes to PyGit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]

---

## [0.0.6] - Wed 15 Jan 2026 11:45:00 PM CST

### Added

- **Phase 3 Remote Operations - COMPLETE**
  - 352 total tests (351 passed, 1 skipped)
  - 70 new tests for remote operations

- **Fetch Command (Phase 3.1)**
  - `pygit fetch [remote] [branch]` - Download objects and refs from remote
  - Recursive commit/tree/blob fetching via GitHub API
  - Support for `--all` (all branches), `--prune` (remove stale refs), `--dry-run`
  - Remote tracking refs stored in `.git/refs/remotes/<remote>/`
  - 20 unit tests covering fetch operations

- **Pull Command (Phase 3.2)**
  - `pygit pull [remote] [branch]` - Fetch and merge changes
  - Fast-forward merge support with working directory checkout
  - Support for `--ff-only`, `--no-ff` flags
  - Tracking branch detection from config
  - Tree checkout with file creation/update
  - 23 unit tests covering pull operations

- **Push Command (Phase 3.3)**
  - `pygit push [remote] [branch]` - Upload commits to remote
  - GitHub Git Data API integration (blobs, trees, commits, refs)
  - Token authentication via `--token` flag or `GITHUB_TOKEN` env var
  - Support for `--force`, `--set-upstream`, `--dry-run`, `--all`
  - Fast-forward detection prevents accidental overwrites
  - Commit chain recreation on remote
  - 27 unit tests covering push operations

- **GitHub API Extensions**
  - `_post_request()` - POST requests for write operations
  - `_patch_request()` - PATCH requests for updates
  - `create_blob()` - Create blob objects (base64 encoded)
  - `create_tree()` - Create tree objects with entries
  - `create_commit()` - Create commit objects with author/committer
  - `create_ref()` - Create new branch references
  - `update_ref()` - Update existing references
  - `get_ref()` - Get SHA for a reference

### Files Added

- `pygit/commands/fetch.py` - Fetch command implementation
- `pygit/commands/pull.py` - Pull command implementation
- `pygit/commands/push.py` - Push command implementation
- `tests/unit/commands/test_fetch.py` - Fetch unit tests (20)
- `tests/unit/commands/test_pull.py` - Pull unit tests (23)
- `tests/unit/commands/test_push.py` - Push unit tests (27)

### Modified

- `pygit/commands/main.py` - Added fetch, pull, push parsers and handlers
- `pygit/core/github.py` - Added POST/PATCH methods and Git Data API

---

## [0.0.5] - Wed 15 Jan 2026

### Added

- **Phase 2.5 Testing Enhancement - COMPLETE**
  - 283 total tests (282 passed, 1 skipped)
  - 82% code coverage

- **Testing Infrastructure (Phase 2.5.1)**
  - pytest configuration with markers (unit, integration, property, slow, network)
  - Coverage configuration with 80% threshold
  - Test directory structure (unit/integration/property)
  - Hypothesis integration for property-based testing

- **Unit Tests (Phase 2.5.2)**
  - 196 unit tests across all core modules
  - Repository operations (init, object storage, HEAD management)
  - Git objects (Blob, Tree, Commit, Tag, Author)
  - Index operations (add, remove, save/load, write_tree)
  - Configuration management (sections, types, scopes)
  - GitIgnore pattern matching
  - CLI command tests
  - HTTP utilities and clone operations

- **Integration Tests (Phase 2.5.3)**
  - 43 integration tests for end-to-end workflows
  - Git compatibility tests (PyGit repos readable by Git and vice versa)
  - Round-trip tests for blob, tree, commit, index, and config
  - Mixed workflow tests (alternating PyGit/Git operations)

- **Property-Based Tests (Phase 2.5.4)**
  - 44 property-based tests using Hypothesis
  - Object model invariants (SHA consistency, format, uniqueness)
  - Index operation properties (add/remove, serialization)
  - Path handling and GitIgnore pattern properties
  - Custom strategies for SHA1, filenames, modes, timezones

### Fixed

- **Empty Index File on Init:** Removed empty index file creation that caused Git to fail with "index file smaller than expected"
- **Tree Entry Mode Serialization:** Fixed mode output from decimal (33188) to octal (100644) format
- **Windows Executable Detection:** Added platform check to skip unreliable `os.access(X_OK)` on Windows
- **Windows Reserved Filenames:** Added filter for reserved device names (NUL, CON, PRN, etc.) in property tests
- **Hypothesis Deadline Issues:** Added deadline=None for I/O-bound property tests

### Documentation

- REPORT-Testing_Infrastructure.md - Phase 2.5.1 report
- REPORT-Testing_UnitTests.md - Phase 2.5.2 report
- REPORT-Testing_IntegrationTests.md - Phase 2.5.3 report
- REPORT-Testing_PropertyTests.md - Phase 2.5.4 report

### Known Limitations

- Index format not fully compatible with Git's native format (workaround: use `git read-tree HEAD`)

---

## [0.0.4] - Wed 14 Jan 2026 06:52:00 PM CST

### Changed

- **Development Plan Overhaul:** Complete revision of PLAN_PyGit.md with testing-first approach
- **Phase Structure:** Inserted Phase 2.5 (Testing & Stabilization) as mandatory gate before remote operations
- **Phase 3 Split:** Divided remote operations into Fetch (read-only), Pull, then Push for reduced risk

### Added

- **Testing Strategy Section:** Comprehensive test organization structure and principles
- **Test Repository Matrix:** Defined test fixtures for various repository types and edge cases
- **Cross-Platform Testing Requirements:** Windows, Linux, macOS validation criteria
- **Property-Based Testing Plan:** Hypothesis-based fuzzing for binary formats and paths
- **Coverage Requirements:** Defined minimum coverage targets by component (90%/85%/80%)
- **Phase Gate Criteria:** Exit criteria that must be met before advancing phases
- **Compatibility Checkpoints:** Git compatibility verification at each phase boundary
- **Error Handling Strategy:** Documented approach for exceptions, recovery, and logging
- **Path Handling Strategy:** Defined normalization and encoding standards

### Removed

- **Timeline Estimates:** Removed calendar-based estimates in favor of dependency-driven gates
- **Deferred Testing:** Moved testing from Phase 5 to immediate priority (Phase 2.5)

### Documentation

- **Current Status Summary:** Added progress tracking table at top of plan
- **Lessons Learned:** Documented v0.0.3 issues that informed testing strategy
- **Phase Dependencies:** Added visual dependency graph for phase progression
- **Immediate Next Steps:** Reordered to prioritize testing infrastructure

---

## [0.0.3] - Wed 14 Jan 2026 06:03:27 PM CST

### Fixed

- **Index Corruption Issues:** Added robust error handling with automatic backup and recovery
- **Windows Console Encoding:** Fixed encoding issues for Windows console output
- **Status Display:** Improved untracked files detection and Git directory exclusion
- **Version Display:** Fixed CLI to use dynamic package version correctly
- **GitIgnore Patterns:** Added comprehensive Python project .gitignore support
- **Path Handling:** Added safe path encoding for file names with special characters

### Enhanced

- **Error Recovery:** Graceful handling of corrupted index files with automatic cleanup
- **Console Output:** Windows-compatible text encoding with error replacement
- **Status Command:** Better separation of staged, modified, and untracked files

---

## [0.0.2] - Wed 14 Jan 2026 05:22:08 PM CST

### Added

- **Enhanced Clone Operation:** Full repository state support with GitHub API integration
- **Staging Area Management:** Complete index implementation with Git-compatible format
- **Add & Status Operations:** File staging, change detection, and multiple output formats
- **Commit Operation:** Full commit workflow with author/committer management
- **CLI Interface:** Git-compatible command structure with proper routing
- **GitIgnore Support:** Complete .gitignore pattern matching and file filtering
- **HTTP Utilities:** Download progress tracking and retry logic
- **GitHub API Module:** Repository metadata, branch management, and file operations

### Enhanced

- **PyGitClone.py Integration:** Refactored into modular architecture with backward compatibility
- **Index Serialization:** Git-compatible index file format with proper handling
- **Error Handling:** Comprehensive error handling and logging throughout

### Fixed

- **Index File Corruption:** Fixed buffer size and timestamp serialization issues
- **File Stat Handling:** Safe handling of large file timestamps and device IDs
- **CLI Argument Parsing:** Proper command routing and error messages

---

## [0.0.1] - Wed 14 Jan 2026 04:56:58 PM CST

### Added

- Modular package architecture with separate packages for operations
- Core Git object models (Blob, Tree, Commit, Tag) with SHA-1 hashing
- Repository management system with Git directory structure support
- Git-compatible configuration management system
- Structured logging framework with multiple output formats
- Complete package structure (pygit/{core,commands,utils,tests})
- Project initialization and planning documentation

---

*Note: Versioning follows project conventions with CST timestamps.*