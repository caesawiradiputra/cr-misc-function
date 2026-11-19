# Changelog — wsl-proxy-basic-auth: ECONNRESET behind a Basic-auth proxy in the WSL guide

**Ticket:** none (own-initiative docs change, keyed by slug)
**Branch:** docs/wsl-proxy-basic-auth

All notable changes for this change are documented here. Newest entry on top.

---

## [Unreleased] — 2026-11-19

**Type:** Docs

### 📝 Summary

The WSL troubleshooting section of the Claude Code setup guide gets a third proxy case.
When direct HTTPS egress is blocked network-wide and the corporate proxy requires Basic
auth, Claude Code fails with `ECONNRESET` (the earlier cases gave `ERR_PROXY_TUNNEL`).
The new subsection has the direct-versus-proxy test, how to read the result, the
`~/.proxyenv` and `NO_PROXY`/`no_proxy` setup, the gotchas, and a table of the three
causes that share the "cannot reach Anthropic" symptom. Real hosts, user ids and the
machine name are replaced with placeholders because the repo is public.

### 📋 Changes Made

**Files Modified**

- `docs/claude-code-wsl-setup.md` — new subsection and table-of-contents entry under
  "17. Troubleshooting"

### 🧪 Testing

Documentation only. The commands are taken from a working diagnosis on a corporate
network and were not re-run for this change.
