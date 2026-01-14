# _________ Project Rules

## Timezone Convention
**CRITICAL**: ALL timestamps, dates, and times in this project MUST use Central Time USA (CST/CDT), NEVER UTC or any other timezone.

This applies to:
- Changelog entries in source code headers
- Version labels and dates in the UI
- Git commit messages (if applicable)
- Documentation timestamps
- Any other date/time references in the project

Example formats:
- Changelog: `Tue 03 Dec 2025 09:20:00 PM CST`
- Version label: `v0.0.9b 2025-12-03`
- Always include timezone indicator (CST or CDT) in full timestamps

## Version Numbering
- Format: `v0.0.X` for releases
- Format: `v0.0.Xa`, `v0.0.Xb`, `v0.0.Xc` for point releases/patches
- Update version info in the README.md file, UI label, the About dialog and header comment when making releases  Note:  Version info consists of the Version Number, the Date  AND THE TIME!!!  e.g.  v0.2.6  2025-12-22 1125  and time should always be CST/CDT

## GitHub Releases
**CRITICAL**: TagWriter's version checker uses the GitHub Releases API, not git tags. You MUST create a proper GitHub Release for the version checker to detect new versions.

### Git Tags vs GitHub Releases
- **Git Tag**: Just a pointer to a commit in git history (created with `git tag`)
- **GitHub Release**: A published release on GitHub with release notes (what the version checker sees)

### Creating a Release
After pushing commits and tags, create a GitHub Release:

```bash
# 1. Push commits and create/push tag
git push origin main
git tag -a v0.1.X -m "Release message"
git push origin v0.1.X

# 2. Create GitHub Release (REQUIRED for version checker)
gh release create v0.1.X --title "TagWriter v0.1.X" --notes "Release notes here"
```

### Installing GitHub CLI
If `gh` command is not available:
```bash
# Debian/Ubuntu
sudo apt install gh

# Windows (using winget)
winget install GitHub.cli

# macOS
brew install gh

# First time setup
gh auth login
```

**Alternative**: Create release manually via GitHub web UI (Releases → Draft a new release)

