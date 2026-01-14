# Changelog

All notable changes to PyGit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [Previous Versions]

---

*Note: Versioning follows project conventions with CST timestamps.*