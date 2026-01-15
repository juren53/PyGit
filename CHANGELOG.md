# Changelog

All notable changes to PyGit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]

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