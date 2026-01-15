# PyGit Development Plan

## **Project Vision**
Create a full Git replacement implemented in pure Python, starting with GitHub-only support and expanding to a comprehensive Git alternative.

---

## **Current Status Summary**

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Foundation | ~85% Complete | Core architecture in place |
| Phase 2: Basic Operations | ~70% Complete | Clone, add, status, commit working |
| Phase 2.5: Testing & Stabilization | **CURRENT PRIORITY** | Required before proceeding |
| Phase 3: Remote Operations | Not Started | Blocked by testing phase |

### Lessons Learned (v0.0.3)
The following issues revealed gaps in our testing and error handling:
- **Index corruption** - Binary format edge cases not caught
- **Windows encoding** - Platform assumptions caused failures
- **Path handling** - Special characters broke operations
- **Version display** - Build/packaging inconsistencies

These issues inform our testing strategy below.

---

## **Phase 1: Foundation & Core Architecture** ✅ COMPLETE

### 1.1 Project Structure Setup
- [x] Create modular architecture with separate packages for operations
- [x] Set up proper package structure (`pygit/` with submodules)
- [x] Add configuration management system
- [x] Implement logging framework

### 1.2 Core Git Object Models
- [x] Implement Git object types: blob, tree, commit, tag
- [x] Create repository structure representation (`.git` directory)
- [x] Build SHA-1 hashing and object storage system
- [x] Implement index/staging area management

**Deliverables:** ✅
- Package structure with core modules
- Basic Git object classes
- Repository initialization framework
- Configuration and logging systems

---

## **Phase 2: Basic Operations (Priority Features)** 🔄 IN PROGRESS

### 2.1 Enhanced Clone Operation
- [x] Extend current GitHub-only clone to support full repository state
- [x] Add `.git` directory creation with proper metadata
- [ ] Implement branch switching during clone
- [ ] Add shallow clone support

### 2.2 Add & Status Operations
- [x] Build file system scanning for changes
- [x] Implement `git add` functionality (staging)
- [x] Create `git status` output formatting
- [x] Add ignore file support (`.gitignore`)

### 2.3 Commit Operation
- [x] Implement commit object creation
- [x] Build commit message handling
- [x] Add author/committer information management
- [x] Create commit tree generation

**Deliverables:**
- [x] Enhanced `pygit clone` command
- [x] Working `pygit add` and `pygit status` commands
- [x] Functional `pygit commit` command
- [ ] Branch switching during clone
- [ ] Shallow clone support

---

## **Phase 2.5: Testing & Stabilization** ⭐ CURRENT PRIORITY

> **GATE REQUIREMENT:** No development work on Phase 3+ until this phase is complete.

### 2.5.1 Testing Infrastructure Setup
- [ ] Set up pytest as the testing framework
- [ ] Create test directory structure mirroring source layout
- [ ] Configure test coverage reporting (pytest-cov)
- [ ] Set up test fixtures and shared utilities
- [ ] Create mock/stub infrastructure for GitHub API

### 2.5.2 Unit Test Suite

#### Core Objects (`pygit/core/`)
- [ ] **Blob tests:** Creation, serialization, deserialization, hash verification
- [ ] **Tree tests:** Entry management, serialization, nested trees
- [ ] **Commit tests:** Parent linking, metadata, serialization round-trips
- [ ] **Tag tests:** Annotated vs lightweight, object references
- [ ] **Index tests:** Add/remove entries, serialization, corruption recovery
- [ ] **Repository tests:** Initialization, structure validation, path handling

#### Commands (`pygit/commands/`)
- [ ] **Clone tests:** GitHub API mocking, directory creation, error handling
- [ ] **Add tests:** Staging logic, gitignore respect, path normalization
- [ ] **Status tests:** Change detection, output formatting, edge cases
- [ ] **Commit tests:** Tree generation, message handling, author info

#### Utilities (`pygit/utils/`)
- [ ] **Path handling tests:** Special characters, Unicode, Windows/Unix paths
- [ ] **Config tests:** Reading, writing, inheritance, defaults
- [ ] **HTTP tests:** Retry logic, error handling, timeout behavior

### 2.5.3 Integration Test Suite
- [ ] **End-to-end workflow:** clone → modify → add → status → commit
- [ ] **Git compatibility:** Verify PyGit repos work with standard Git
- [ ] **Round-trip tests:** Create with PyGit, read with Git, and vice versa

### 2.5.4 Test Repository Matrix
Create and maintain test fixtures for:
- [ ] **Small repository:** <100 files, simple structure
- [ ] **Medium repository:** 1000+ files, nested directories
- [ ] **Edge case repository:** Special characters in paths, Unicode filenames
- [ ] **Binary files repository:** Images, compiled files, mixed content
- [ ] **Large files repository:** Files >1MB to test streaming/memory
- [ ] **Symlinks repository:** (where platform supports)

### 2.5.5 Cross-Platform Testing
- [ ] **Windows:** Console encoding, path separators, line endings
- [ ] **Linux:** Permission handling, symlinks, case sensitivity
- [ ] **macOS:** Unicode normalization (NFD vs NFC), case sensitivity

### 2.5.6 Property-Based Testing
- [ ] Set up `hypothesis` library for property-based tests
- [ ] **Index format fuzzing:** Random valid/invalid index data
- [ ] **Path fuzzing:** Random valid paths with special characters
- [ ] **Object serialization:** Round-trip property for all Git objects

### 2.5.7 Error Handling Audit
- [ ] Document all error conditions and expected behavior
- [ ] Verify graceful degradation for corrupted data
- [ ] Test recovery mechanisms (backup/restore)
- [ ] Ensure consistent error messages across platforms

### 2.5.8 Performance Baseline
- [ ] Establish baseline metrics for core operations
- [ ] Document performance on test repository matrix
- [ ] Create benchmarks for future regression testing

**Deliverables:**
- Comprehensive test suite with >80% coverage
- All tests passing on Windows, Linux, macOS
- Performance baseline documentation
- CI configuration ready for automation

**Exit Criteria (Gate Check):**
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Cross-platform CI green
- [ ] No known corruption or data loss bugs
- [ ] Git compatibility verified for basic workflow

---

## **Phase 3: Remote Operations** (Blocked by Phase 2.5)

### 3.1 Fetch Operations (Read-Only First)
- [ ] Implement remote reference fetching
- [ ] Parse and store remote refs
- [ ] Download objects from remote
- [ ] Update local tracking branches

### 3.2 Pull Operations
- [ ] Implement fetch + merge workflow
- [ ] Add fast-forward merge logic
- [ ] Build conflict detection system
- [ ] Create branch synchronization

### 3.3 Push Operations (After Fetch is Stable)
- [ ] Build Git protocol understanding for pushing
- [ ] Implement authentication handling (token, SSH)
- [ ] Add pack file generation for transfers
- [ ] Create branch update mechanisms
- [ ] Handle push rejection and force push

**Deliverables:**
- Working `pygit fetch` command
- Functional `pygit pull` command
- Working `pygit push` command
- Remote repository synchronization
- Basic conflict detection

**Compatibility Checkpoint:**
- [ ] Fetch from GitHub, verify with standard Git
- [ ] Push from PyGit, pull with standard Git
- [ ] Round-trip: PyGit push → Git pull → Git push → PyGit pull

---

## **Phase 4: Advanced Features**

### 4.1 Branch Management
- [ ] Branch creation, deletion, listing
- [ ] Branch switching and checkout
- [ ] Merge operations (fast-forward, then three-way)
- [ ] Branch comparison and diff

### 4.2 History & Diff Operations
- [ ] Log functionality with formatting options
- [ ] Diff implementation between commits/trees
- [ ] Blame functionality
- [ ] Interactive rebase (stretch goal)

**Deliverables:**
- Complete branch management system
- Comprehensive `pygit log`, `pygit diff`, `pygit blame` commands
- Basic merge capabilities
- Advanced history exploration tools

**Compatibility Checkpoint:**
- [ ] Branch operations match standard Git behavior
- [ ] Merge results identical to Git merges
- [ ] History traversal matches Git output

---

## **Phase 5: Optimization & Polish**

### 5.1 Performance Optimization
- [ ] Profile and identify bottlenecks
- [ ] Optional Rust/C extensions for critical paths
- [ ] Caching mechanisms for large repositories
- [ ] Parallel operation support
- [ ] Memory usage optimization

### 5.2 CI/CD & Release
- [ ] Automated CI pipeline (GitHub Actions)
- [ ] Automated release process
- [ ] Documentation generation
- [ ] Package publishing (PyPI)

**Deliverables:**
- Performance-optimized implementation
- Production-ready CLI tool
- Comprehensive documentation
- Automated testing and deployment

---

## **Testing Strategy**

### Test Organization
```
pygit/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── fixtures/                # Test data
│   │   ├── repos/               # Test repositories
│   │   ├── objects/             # Sample Git objects
│   │   └── index/               # Sample index files
│   ├── unit/
│   │   ├── core/
│   │   │   ├── test_blob.py
│   │   │   ├── test_tree.py
│   │   │   ├── test_commit.py
│   │   │   ├── test_tag.py
│   │   │   ├── test_index.py
│   │   │   └── test_repository.py
│   │   ├── commands/
│   │   │   ├── test_clone.py
│   │   │   ├── test_add.py
│   │   │   ├── test_status.py
│   │   │   └── test_commit.py
│   │   └── utils/
│   │       ├── test_paths.py
│   │       ├── test_config.py
│   │       └── test_http.py
│   ├── integration/
│   │   ├── test_workflow.py     # End-to-end workflows
│   │   ├── test_git_compat.py   # Git compatibility
│   │   └── test_round_trip.py   # PyGit ↔ Git
│   ├── property/
│   │   ├── test_index_fuzzing.py
│   │   ├── test_path_fuzzing.py
│   │   └── test_object_roundtrip.py
│   └── performance/
│       ├── test_benchmarks.py
│       └── conftest.py          # Performance fixtures
```

### Testing Principles
1. **Test before code:** Write tests for new features before implementation
2. **Regression tests:** Every bug fix must include a test that would have caught it
3. **Compatibility tests:** Verify Git compatibility at every phase gate
4. **Property tests:** Use hypothesis for binary formats and edge cases
5. **Platform parity:** All tests must pass on all supported platforms

### Coverage Requirements
| Component | Minimum Coverage |
|-----------|-----------------|
| Core objects | 90% |
| Commands | 85% |
| Utilities | 80% |
| Overall | 85% |

---

## **Key Technical Decisions**

### Dependencies
- **Core:** Pure Python, standard library only
- **Testing:** pytest, pytest-cov, hypothesis
- **Optional:** Performance extensions in Rust/C (Phase 5)

### Error Handling Strategy
- **Explicit errors:** Use custom exception hierarchy
- **Recovery:** Automatic backup before destructive operations
- **Logging:** All errors logged with context for debugging
- **User feedback:** Clear, actionable error messages

### Path Handling Strategy
- **Normalization:** All paths normalized at entry points
- **Encoding:** UTF-8 with surrogate escape for invalid sequences
- **Platform:** Abstract platform differences in utility layer

### API Design
- **CLI:** Mirror Git CLI commands for familiarity
- **Programmatic:** Pythonic API for integration
- **Configuration:** Git-compatible configuration files

### Storage & Protocol
- **Storage:** Git-compatible object database with zlib compression
- **Protocol:** GitHub API initially, then Git protocol
- **Authentication:** Token-based (GitHub), SSH keys (future)

### Compatibility
- **Repository Format:** 100% Git-compatible
- **Remote Operations:** GitHub first, expand later
- **CLI Interface:** Git command compatibility where feasible

---

## **Implementation Strategy**

### Development Approach
1. **Test-First:** Write tests before implementing new features
2. **Incremental:** Build core features first, expand functionality
3. **Gate-Driven:** No phase advancement until gate criteria met
4. **Documentation:** Living documentation alongside code

### Phase Dependencies
```
Phase 1 (Foundation)
    ↓
Phase 2 (Basic Ops)
    ↓
Phase 2.5 (Testing) ← GATE: All tests green, cross-platform
    ↓
Phase 3a (Fetch) ← GATE: Fetch compatible with Git
    ↓
Phase 3b (Push) ← GATE: Round-trip verified
    ↓
Phase 4 (Advanced)
    ↓
Phase 5 (Polish)
```

### Success Metrics
- [ ] Can clone, modify, and push a repository end-to-end
- [ ] 100% compatible with standard Git repositories
- [ ] Performance suitable for medium-sized repositories (<10k files)
- [ ] Test coverage >85%
- [ ] All tests passing on Windows, Linux, macOS

---

## **Immediate Next Steps**

1. **Set up testing infrastructure**
   - Install pytest, pytest-cov, hypothesis
   - Create test directory structure
   - Set up conftest.py with shared fixtures

2. **Write unit tests for existing code**
   - Start with core objects (blob, tree, commit)
   - Test index serialization thoroughly
   - Add path handling edge case tests

3. **Create integration test suite**
   - End-to-end workflow test
   - Git compatibility verification
   - Cross-platform validation

4. **Establish CI pipeline**
   - GitHub Actions for automated testing
   - Multi-platform test matrix
   - Coverage reporting

5. **Complete Phase 2 remaining items**
   - Branch switching during clone
   - Shallow clone support

---

## **Resources & References**

### Testing Resources
- **pytest documentation:** https://docs.pytest.org/
- **hypothesis documentation:** https://hypothesis.readthedocs.io/
- **Git test suite:** Study Git's own test approach

### Existing Solutions to Study
- **Dulwich:** Pure Python Git implementation
- **GitPython:** Git wrapper library
- **libgit2:** C Git library (for protocol understanding)

### Documentation Standards
- Git source code and documentation
- Git protocol specification
- GitHub API documentation

---

*This plan is a living document. Phase gates ensure stability before advancing. Testing is not optional—it is the foundation for reliable software.*
