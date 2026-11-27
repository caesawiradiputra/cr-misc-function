# Changelog — deny-more-secret-files: block more secret files in the shared Claude Code settings

**Ticket:** none (own-initiative chore, keyed by slug)
**Branch:** chore/deny-more-secret-files

All notable changes for this change are documented here. Newest entry on top.

---

## [Unreleased] — 2026-11-27

**Type:** Chore

### 📝 Summary

A review suggested blocking a few more secret files in `.claude/settings.json`. `permissions.deny` now
also blocks reading and editing `.env.production`, `*.key` and Google service-account JSON files.

### 📋 Changes Made

**Files Modified**

- `.claude/settings.json` — `Read` and `Edit` deny rules for `**/.env.production`, `**/*.key`,
  `**/*service-account*.json`
- `CLAUDE.md` — the `permissions.deny` description lists the new patterns

### ⚠️ Notes

- Google has no fixed name for service-account keys, so the pattern only matches file names that contain
  `service-account`. Widen it if keys are named differently.
