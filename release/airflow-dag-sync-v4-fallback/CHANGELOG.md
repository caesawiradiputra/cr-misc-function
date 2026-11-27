# Changelog — airflow-dag-sync-v4-fallback: the airflow-dag-sync fallback in step with the template repo

**Ticket:** none (own-initiative chore, keyed by slug)
**Branch:** chore/airflow-dag-sync-v4-fallback

All notable changes for this change are documented here. Newest entry on top.

---

## [Unreleased] — 2026-11-27

**Type:** Chore

### 📝 Summary

`da-template-airflow-dags` is the source of truth for DAG repos and is at `airflow-dag-sync@4`; this repo
holds the fallback copy and was still at `@3`. The two scripts (`sync_dags.sh`, `publish_dags.sh`) are
identical in both repos, so only the version moved.

### 📋 Changes Made

**Files Modified**

- `templates/github-workflows/airflow-dag-sync/sync-dags.yml` — marker `# template: airflow-dag-sync@4`
- `templates/manifest.json` — `airflow-dag-sync` version 3 to 4 (the digest is unchanged)
- `README.md`, `CLAUDE.md` — docs version line date

### ⚠️ Notes

- `template_sync.py verify --source .` passes.
- The workflow header and placeholders differ from the template repo on purpose (this copy points at
  `docs/guidelines/AIRFLOW-DAG-SYNC-STANDARD.md` and keeps `<dag-slug>` placeholders).
