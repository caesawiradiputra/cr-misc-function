---
name: graphify-setup
description: Set up Graphify (the `graphifyy` code knowledge-graph CLI) safely in one repo, or in every child repo of an umbrella folder such as ~/repo/<group>/. Writes a `.graphifyignore` with the secret and noise patterns, ignores `graphify-out/` in git, builds the graph with the AST-only `graphify update` (no LLM, nothing leaves the machine), reports what was and was not indexed, and optionally merges the per-repo graphs. It never runs `graphify install`, never installs hooks and never edits CLAUDE.md. Use whenever the user says "/graphify-setup", "set up graphify", "use graphify on this repo", "build the code graph", "scan the umbrella with graphify", "add .graphifyignore", or asks how to try Graphify on a repo, even if they do not say "skill".
---

# Graphify setup

Graphify turns a repo into a queryable graph (`graphify-out/graph.json`, `GRAPH_REPORT.md`, `graph.html`). This skill sets it up **passively and safely**: CLI only, AST only, no hooks, no global config changes.

Facts verified on this machine (2026-10-28, graphifyy 0.9.97) that shape the rules below:

- `graphify update .` parses code locally with tree-sitter, uses no LLM, and needs no API key. It reported 0 tokens.
- It stores symbols and structure, never file contents: unique markers planted in `.env*`, YAML, JSON and SQL comments never appeared in the output.
- Files with no extension (`.env`, `.env.dev`, `Dockerfile`) are skipped as unclassified, and JSON is not indexed. A YAML file that is not ignored **is** parsed, and its key names (`password`, `user`) become nodes.
- Gitignore handling was not proven, so a `.graphifyignore` is mandatory.
- `.graphifyignore` uses gitignore syntax (directory patterns, `*.md`, `**/x.py` and `!negation` all worked) and prunes nodes already in the graph on the next `update`.
- SQL needs the `sql` extra, and even then dbt/Jinja models and macros yield no symbols. Use `dbt ls --select model+` for lineage.
- Cross-repo continuous graphs are the paid Graphify Cloud. The CLI offers `merge-graphs`.

## Hard rules

1. **Never run** `graphify install`, `graphify <platform> install`, `graphify hook install`, `graphify uninstall` (unless the user asks to remove something), `graphify extract`, `/graphify` or `graphify add`. Install writes CLAUDE.md registrations and PreToolUse hooks; `extract`, `/graphify` and `add` send docs, PDFs or URLs to an LLM.
2. **Unset model API keys for every graphify call** (`env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u GEMINI_API_KEY -u GOOGLE_API_KEY graphify ...`), so a semantic pass can never start by accident.
3. **Ignore file before the first build.** Write `.graphifyignore` first; build second.
4. **Do not read, print or embed secret values.** Check tracked secret files by name only.
5. **Multi-repo sessions:** edit files in other repos but leave them uncommitted; commit only in the session's focus repo (global rule). Say which files changed in each repo.

## Workflow

### 1. Preflight

```bash
command -v graphify || uv tool install "graphifyy[sql]"
graphify --version 2>&1 | head -1
python3 --version   # Graphify needs 3.10+ (uv brings its own)
```

If `graphify` is missing, installing it with `uv tool install "graphifyy[sql]"` is part of this skill. If it is installed without the `sql` extra, reinstall with `uv tool install --force "graphifyy[sql]"`. Do not use `pip`.

### 2. Resolve the targets

- Inside a git repo: the target is `git rev-parse --show-toplevel`.
- In a non-git umbrella folder (per the global "focus root" rule): the targets are the child folders that contain `.git`. List them with file counts and skip the rest, saying which were skipped.
- Never point Graphify at the umbrella itself or at `~/repo`: it is not a git repo, the child `.gitignore` files may not apply, and it would walk every `.venv`.

### 3. Per repo: ignore files

Read first (check state before writing).

- **`.graphifyignore`:** create it, or add the missing lines to an existing one without removing the user's lines. Standard content:

  ```text
  ## Managed by graphify-setup: secrets and noise. Add repo-specific lines below.
  .env
  .env.*
  !.env.template
  !.env.example
  profile.yaml
  profile.yml
  profiles.yml
  profiles.yaml
  settings.local.json
  credentials*.json
  token.json
  service-account*.json
  *.pem
  *.key
  *.pfx
  *.p12
  id_rsa*
  id_ed25519*
  .netrc
  *.tfvars
  *.tfstate
  secrets/
  .venv/
  venv/
  node_modules/
  __pycache__/
  *.whl
  *.log
  legacy/
  graphify-out/
  ```

  Keep the repo's own deny rules from `.claude/settings.json` in sync (add its extra `.env.<name>` variants). Add `legacy/` only if the repo has it and the user wants snapshots excluded.
- **`.gitignore`:** append `graphify-out/` when `git check-ignore -q graphify-out/graph.json` says it is not ignored. The output is large (16 MB for a 330-file repo).
- **Tracked secrets:** `git ls-files` filtered by the secret names above. Report any hit loudly by path; do not untrack or open it.

### 4. Per repo: build

```bash
cd <repo>
env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u GEMINI_API_KEY -u GOOGLE_API_KEY graphify update .
```

Report per repo: nodes, edges, communities, the "not classified" and "yielded no symbols" counts (with the notable file types), the build time and the `graphify-out/` size. Then confirm the ignore file worked: no node whose `source_file` matches an ignored pattern.

```bash
python3 - <<'PY'
import json
g = json.load(open("graphify-out/graph.json"))
bad = [n["source_file"] for n in g["nodes"] if any(s in str(n.get("source_file", "")) for s in (".env", "credentials", "settings.local", ".pem", ".key"))]
print("secret-like source files in graph:", sorted(set(bad)) or "none")
PY
```

### 5. Umbrella: merge (optional)

Only when the user wants cross-repo questions:

```bash
graphify merge-graphs <repoA>/graphify-out/graph.json <repoB>/graphify-out/graph.json --out <umbrella>/graphify-out/merged-graph.json
```

Say that the merged graph is a snapshot (rebuild the per-repo graphs, then merge again), and that node names can collide across repos.

### 6. Tell the user how to use it

```bash
graphify query "how does a request reach the database?" --budget 1500
graphify explain "BaseRepository"
graphify path "router.py" "base.py"
graphify update .        # after a pull or big edits (no hooks are installed)
```

Add `--graph <path>` to query a graph from another folder. Claude can read `graphify-out/GRAPH_REPORT.md` first (god nodes, communities, suggested questions), then run `query` or `explain` for the part it needs. Do not add a CLAUDE.md line about Graphify unless the user asks.

### 7. Report

State, briefly: repos set up, files changed per repo (all uncommitted unless it is the focus repo and the user asked), build numbers, the limits that apply to this repo (for example SQL/Jinja yields no symbols, YAML key names are indexed), and any tracked secret files found. Offer to commit `.graphifyignore` and the `.gitignore` line in the repo's own session.
