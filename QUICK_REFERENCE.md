# PyGit Quick Reference

**Version:** v0.0.2  
**Updated:** Wed 14 Jan 2026 05:22:08 PM CST

A quick reference for PyGit CLI commands. PyGit provides Git-compatible commands implemented in pure Python.

## 🚀 Getting Started

```bash
# Show version and help
python pygit.py --version
python pygit.py --help

# Show help for specific command
python pygit.py <command> --help
```

---

## 📁 Repository Operations

### Initialize Repository
```bash
# Initialize in current directory
python pygit.py init

# Initialize in specific directory
python pygit.py init my-project

# Create bare repository
python pygit.py init --bare
```

### Clone Repository
```bash
# Clone repository (GitHub only)
python pygit.py clone https://github.com/owner/repo.git

# Clone to specific directory
python pygit.py clone https://github.com/owner/repo.git my-folder

# Clone specific branch
python pygit.py clone --branch main https://github.com/owner/repo.git

# Create shallow clone (depth limited)
python pygit.py clone --depth 1 https://github.com/owner/repo.git

# Clone bare repository
python pygit.py clone --bare https://github.com/owner/repo.git
```

---

## 📝 File Operations

### Add Files to Staging Area
```bash
# Add specific files
python pygit.py add file1.txt file2.py

# Add all files (respects .gitignore)
python pygit.py add --all

# Add directory contents
python pygit.py add src/
```

### Show Working Tree Status
```bash
# Show detailed status
python pygit.py status

# Show short format
python pygit.py status --short

# Show porcelain format (for scripts)
python pygit.py status --porcelain
```

---

## 💾 Commit Operations

### Create Commit
```bash
# Create commit with message
python pygit.py commit --message "Add new feature"

# Override author
python pygit.py commit --message "Fix bug" --author "John Doe <john@example.com>"
```

---

## 🔧 Configuration Examples

PyGit uses Git-compatible configuration. Set up user info:

```bash
# In Git (PyGit will read this)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Or PyGit will use repository-specific config
python pygit.py commit --message "Initial commit" --author "Your Name <your.email@example.com>"
```

---

## 📊 Workflow Examples

### Basic Git Workflow
```bash
# 1. Initialize new repository
python pygit.py init my-project
cd my-project

# 2. Create files and add them
echo "Hello PyGit" > README.md
python pygit.py add README.md

# 3. Check status
python pygit.py status

# 4. Commit changes
python pygit.py commit --message "Initial commit" --author "Your Name <you@example.com>"

# 5. Clone an existing repository
cd ..
python pygit.py clone https://github.com/owner/existing-repo.git
cd existing-repo

# 6. Make changes and commit
echo "New feature" >> feature.txt
python pygit.py add feature.txt
python pygit.py commit --message "Add feature"
```

### Working with GitHub
```bash
# Clone your repository
python pygit.py clone https://github.com/yourusername/yourrepo.git

# Make changes locally
cd yourrepo
# ... edit files ...
python pygit.py add .
python pygit.py commit --message "My changes"

# Note: Push/pull coming in Phase 3
```

---

## 🚫 .gitignore Support

PyGit respects standard .gitignore patterns:

```bash
# Create .gitignore file
echo "*.pyc" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.log" >> .gitignore

# PyGit will automatically respect these patterns
python pygit.py add --all  # Ignores .pyc, __pycache__, *.log files
```

---

## 🐛 Common Issues & Solutions

### "Not a git repository" error
```bash
# You need to initialize first
python pygit.py init
```

### "Please configure user.name and user.email" error
```bash
# Set globally (recommended)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Or override per commit
python pygit.py commit --message "Fix" --author "Name <email@example.com>"
```

### "No changes added to commit" error
```bash
# Add files first
python pygit.py add --all
python pygit.py status  # Check what's staged
python pygit.py commit --message "Commit message"
```

---

## 📋 Current Command Summary

| Command | Status | Description |
|---------|--------|-------------|
| `init` | ✅ Working | Initialize new repository |
| `clone` | ✅ Working | Clone GitHub repository |
| `add` | ✅ Working | Stage files for commit |
| `status` | ✅ Working | Show working tree status |
| `commit` | ✅ Working | Create commits |
| `push` | 🚧 Phase 3 | Push to remote (planned) |
| `pull` | 🚧 Phase 3 | Pull from remote (planned) |
| `fetch` | 🚧 Phase 3 | Fetch remote changes (planned) |
| `branch` | 🚧 Phase 4 | Branch management (planned) |
| `log` | 🚧 Phase 4 | Show commit history (planned) |
| `diff` | 🚧 Phase 4 | Show changes (planned) |

---

## 🔗 More Information

- **Full Documentation:** See [README.md](README.md)
- **Development Plan:** See [PLAN_PyGit.md](PLAN_PyGit.md)
- **Changelog:** See [CHANGELOG.md](CHANGELOG.md)
- **Repository:** https://github.com/juren53/PyGit

---

**Note:** PyGit v0.0.2 implements basic Git operations. Advanced features like push/pull, branching, and history exploration are planned for future phases.