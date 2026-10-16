# CAB Register Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read the user's hand-filled CAB register CSV, use it as the source of dates (registered, CAB, deploy, PAT end), and feed the logbook helper: a `cab` report, board flags in `pipeline` and `check`, and a "CAB this week" block in `week`.

**Architecture:** All code goes into the existing stdlib-only helper `CLAUDE/skills/logbook/logbook.py`, in one new section placed before `group_items`. The register is read-only and read once per run into a plain dict (`rows`, `by_ticket`, `problems`, `mtime`); pure functions turn that into a per-ticket `cab_info`, which `board_entry`, `cmd_check` and the weekly block consume. Jira stays the owner of status; the register owns dates; a register older than the last CAB session is stale and suppresses its flags.

**Tech Stack:** Python 3.9-compatible stdlib, pytest (3.11 project, 3.9 and 3.12 via `uv run --no-project --python X`), ruff, mypy, Markdown.

**Spec:** `docs/superpowers/specs/2026-10-15-cab-register-integration-design.md` (builds on `2026-10-15-dev-workflow-design.md`)

## Global Constraints

- Helper must run on system `python3` 3.9 and on 3.10+: keep `from __future__ import annotations`, no `match`, no `zip(strict=...)`, no runtime `X | None` outside annotations. `dict | dict` union is allowed on 3.9 but this plan avoids it.
- Nothing is committed, pushed or opened as a PR unless the user asks. A "Checkpoint" step means: show `git status` and the diff summary, and commit only when the user says so.
- Commits: Conventional Commits + gitmoji ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- The repo is public: no real names, Confluence links, ticket titles or register contents in repo files or tests. Use synthetic data (`DA-1234`, `[BAST] DA-1234 - x`).
- Markdown: code fences carry a language, table separators are `| --- |`, object names in backticks. `ruff format --check .` also formats Python blocks inside Markdown, so run `uv run ruff format docs` after writing any doc with Python blocks.
- The register file is never written. All times use the fixed offset +07:00 (`WIB`); the helper never depends on the system time zone for CAB logic.
- Resolving or reading the register must never exit the helper: failures turn the feature off with one note.
- Register date formats: `Tanggal Register CAB` is `M/D/YYYY` (with typed `D/M` cells resolved by the lag window); `jadwal CAB`, `Deploye Plan Date`, `Deployed Real Date`, `Last PAT Date` are `D/M/YY` or `D/M/YYYY`; `Closed Date` and `Deploy Plan Time` are clock times and ignored. `cab_max_lag_days` default 21, clamped to 26.
- `Closed` in the register means deployed. Register `Status` values: `Register CAB`, `Done CAB And Progress Deployment`, `Onprogress Deployment`, `Closed`, `Pending`, `CAB Ulang`, `OK tp Perlu Rekonfirm`, `Rollback`, `Cancel`. `Status PAT` values: `Open`, `Closed`, `NA`, blank.
- The board never changes Jira or the logbook; it proposes. Jira transitions and logbook rows are written only after the user's OK.

## Review Focus

Failure modes the spec implies that the happy-path tests of a single task do not exercise:

1. An Excel re-save changes the file (`;` separator, cp1252, CRLF, short rows) and must not crash `pipeline`, `check` or `week` (Tasks 1 and 7).
2. A stale register must not influence any decision, including PAT dates (Tasks 3 and 5).
3. A ticket with an ambiguous current row must produce no stage and no flag (Tasks 2, 3, 5).
4. The assumed-PAT rule must not fire without a known planned end, and a `Fixing` row inside the PAT window must withhold it (Tasks 3 and 5).
5. A register missing, unreadable or unconfigured must leave `week` working when the logbook has no entries that week (Task 6).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `CLAUDE/skills/logbook/logbook.py` | New CAB section: reading, parsing, mapping, freshness, `cab`, board and `check` flags, weekly block |
| `tests/test_logbook.py` | New tests, same fixture `lb` as the existing tests |
| `CLAUDE/skills/logbook/SKILL.md` | CAB register section: config keys, commands, flags, update cadence |
| `CLAUDE/skills/logbook/config.example.json` | `cab_register`, `cab_sessions`, `cab_max_lag_days`, `cab_grace_days` |
| `CLAUDE/commands/pipeline.md` | Mention the register banner and flags |
| `CLAUDE/CLAUDE.md`, `docs/guidelines/DEV-WORKFLOW.md` | Short pointers to the CAB register |

---

### Task 1: Read the register file safely

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (add `import io`; new section before `def group_items`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Produces:
  - `WIB: dt.timezone`, `CAB_REQUIRED: list[str]`, `CAB_OPTIONAL: list[str]`, `CAB_COLUMNS: list[str]`
  - `resolve_register_path(cfg: dict) -> Path | None` (never exits)
  - `read_register(path: Path) -> dict` with keys `rows` (list of dicts keyed by canonical column name, stripped), `problems` (list[str]), `encoding` (str), `delimiter` (str), `mtime` (aware datetime in WIB or None), `off` (str, non-empty means the feature is off)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_logbook.py`:

```python
REG_COLUMNS = [
    "Column 1", "Status", "TYPE CAB", "Type", "IN / Project", "Kategori",
    "Tanggal \nRegister CAB", "Nama CAB", "Link ", "Requester \nPIC CAB",
    "User Requester", "jadwal CAB", "PIC Deploy Ops", "PIC Deploy Dev",
    "Last PAT Date", "Status PAT", "Deploye Plan Date", "Deploy Plan Time",
    "Deployed Real Date", "Closed Date", "Approval By", "Column 2",
]  # fmt: skip
_REG_ALIAS = {
    "n": "Column 1", "status": "Status", "reg": "Tanggal \nRegister CAB",
    "name": "Nama CAB", "cab": "jadwal CAB", "pat_end": "Last PAT Date",
    "pat_status": "Status PAT", "plan": "Deploye Plan Date",
    "real": "Deployed Real Date",
}  # fmt: skip


def reg_line(**kw: str) -> list[str]:
    """One register row aligned with REG_COLUMNS (aliases above, defaults blank)."""
    cells = dict.fromkeys(REG_COLUMNS, "")
    cells["Status"] = "Closed"
    cells["Nama CAB"] = "[BAST] DA-1234 - x"
    for key, value in kw.items():
        cells[_REG_ALIAS[key]] = value
    return [cells[c] for c in REG_COLUMNS]


def write_register(
    path: Path,
    lines: list[list[str]],
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    terminator: str = "\n",
    header: list[str] | None = None,
) -> None:
    with path.open("w", newline="", encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter, lineterminator=terminator)
        writer.writerow(header or REG_COLUMNS)
        writer.writerows(lines)


def test_read_register_matches_wrapped_headers(lb: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="7", reg="10/12/2026", cab="14/10/26")])
    out = lb.read_register(path)
    assert out["off"] == "" and out["encoding"] == "utf-8-sig"
    row = out["rows"][0]
    assert row["Column 1"] == "7" and row["Tanggal Register CAB"] == "10/12/2026"
    assert row["jadwal CAB"] == "14/10/26" and row["Nama CAB"] == "[BAST] DA-1234 - x"
    assert out["mtime"].utcoffset() == dt.timedelta(hours=7)


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_read_register_handles_bom_and_crlf(lb, tmp_path, terminator) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")], terminator=terminator)
    assert lb.read_register(path)["rows"][0]["Column 1"] == "1"


def test_read_register_detects_semicolon_and_tab(lb, tmp_path) -> None:
    for delimiter in (";", "\t"):
        path = tmp_path / "reg.csv"
        write_register(path, [reg_line(n="5")], delimiter=delimiter)
        out = lb.read_register(path)
        assert out["delimiter"] == delimiter and out["rows"][0]["Column 1"] == "5"


def test_read_register_falls_back_to_cp1252(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(name="SRF – DA-1234")], encoding="cp1252")
    out = lb.read_register(path)
    assert out["encoding"] == "cp1252" and "–" in out["rows"][0]["Nama CAB"]


def test_read_register_pads_short_rows_and_skips_blank_rows(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")[:3], [""] * 22, ["", "", ""]])
    out = lb.read_register(path)
    assert len(out["rows"]) == 1 and out["rows"][0]["Nama CAB"] == ""


def test_read_register_turns_the_feature_off_instead_of_crashing(
    lb: ModuleType, tmp_path: Path
) -> None:
    missing = lb.read_register(tmp_path / "nope.csv")
    assert missing["off"] and missing["rows"] == []
    assert lb.read_register(tmp_path)["off"]  # a directory is unreadable
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert lb.read_register(empty)["off"]
    header_only = tmp_path / "h.csv"
    write_register(header_only, [])
    out = lb.read_register(header_only)
    assert out["off"] == "" and out["rows"] == []


def test_read_register_names_a_missing_required_column(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    header = [c for c in REG_COLUMNS if c != "Last PAT Date"]
    write_register(path, [], header=header)
    assert "Last PAT Date" in lb.read_register(path)["off"]


def test_read_register_reports_a_duplicate_column_and_keeps_the_first(
    lb, tmp_path
) -> None:
    path = tmp_path / "reg.csv"
    header = [*REG_COLUMNS, "Status"]
    write_register(path, [[*reg_line(status="Closed"), "Pending"]], header=header)
    out = lb.read_register(path)
    assert out["rows"][0]["Status"] == "Closed"
    assert any("duplicate" in p for p in out["problems"])


def test_read_register_ignores_extra_columns(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [[*reg_line(n="3"), "x"]], header=[*REG_COLUMNS, "Extra"])
    assert lb.read_register(path)["rows"][0]["Column 1"] == "3"


def test_resolve_register_path_never_exits(lb, tmp_path, monkeypatch) -> None:
    assert lb.resolve_register_path({"cab_register": "~/x.csv"}).name == "x.csv"
    monkeypatch.delenv("LOGBOOK_WINDOWS_DIR", raising=False)
    monkeypatch.setattr(lb, "WINDOWS_DIR_FILE", tmp_path / "missing.txt")
    assert lb.resolve_register_path({}) is None
    monkeypatch.setenv("LOGBOOK_WINDOWS_DIR", str(tmp_path / "win"))
    assert lb.resolve_register_path({}) == tmp_path / "win" / "cab-register.csv"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "read_register or resolve_register"`
Expected: FAIL (`read_register` / `resolve_register_path` missing).

- [ ] **Step 3: Implement**

In `CLAUDE/skills/logbook/logbook.py` add `import io` to the imports (same edit as its first use below), then insert before `def group_items`:

```python
## ---- CAB register (spec 2026-10-15-cab-register-integration-design.md) ----
WIB = dt.timezone(dt.timedelta(hours=7))  # Indonesia (WIB) has no daylight saving
CAB_REQUIRED = [
    "Column 1", "Status", "Tanggal Register CAB", "Nama CAB", "jadwal CAB",
    "Deployed Real Date", "Last PAT Date", "Status PAT",
]  # fmt: skip
CAB_OPTIONAL = ["TYPE CAB", "Kategori", "Deploye Plan Date"]
CAB_COLUMNS = CAB_REQUIRED + CAB_OPTIONAL


def resolve_register_path(cfg: dict[str, Any]) -> Path | None:
    """Where the CAB register CSV is, or None. Never exits (unlike windows_dir())."""
    configured = cfg.get("cab_register")
    if configured:
        return Path(str(configured)).expanduser()
    folder = os.environ.get("LOGBOOK_WINDOWS_DIR", "").strip()
    if not folder and WINDOWS_DIR_FILE.exists():
        try:
            lines = WINDOWS_DIR_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        folder = lines[0].strip() if lines else ""
    return Path(folder) / "cab-register.csv" if folder else None


def _norm_header(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _decode(raw: bytes) -> tuple[str, str]:
    """UTF-8 (BOM allowed), else cp1252 (Excel's 'CSV (comma delimited)')."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("cp1252", raw, 0, 1, "neither UTF-8 nor cp1252")


def _detect_delimiter(text: str) -> str:
    first = text.lstrip("\r\n").split("\n", 1)[0]
    counts = {d: first.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ","


def read_register(path: Path) -> dict[str, Any]:
    """Read the CAB register. Read-only; any failure sets 'off' and never raises."""
    out: dict[str, Any] = {
        "rows": [], "problems": [], "encoding": "", "delimiter": ",",
        "mtime": None, "off": "",
    }  # fmt: skip
    try:
        raw = path.read_bytes()
        mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, WIB)
        text, out["encoding"] = _decode(raw)
    except FileNotFoundError:
        out["off"] = f"no CAB register at {path}"
        return out
    except (OSError, UnicodeDecodeError) as exc:
        out["off"] = f"cannot read the CAB register {path}: {exc}"
        return out
    out["mtime"] = mtime
    out["delimiter"] = _detect_delimiter(text)
    try:
        table = list(
            csv.reader(io.StringIO(text, newline=""), delimiter=out["delimiter"])
        )
    except csv.Error as exc:
        out["off"] = f"cannot parse the CAB register: {exc}"
        return out
    table = [r for r in table if any(c.strip() for c in r)]
    if not table:
        out["off"] = "the CAB register is empty"
        return out
    header, body = table[0], table[1:]
    index: dict[str, int] = {}
    for i, cell in enumerate(header):
        key = _norm_header(cell)
        if key in index:
            out["problems"].append(
                f"duplicate column {cell.strip()!r}: the first one is used"
            )
        else:
            index[key] = i
    missing = [c for c in CAB_REQUIRED if _norm_header(c) not in index]
    if missing:
        out["off"] = "the CAB register lacks column(s): " + ", ".join(missing)
        return out
    for line in body:
        padded = line + [""] * (len(header) - len(line))
        out["rows"].append({
            col: padded[index[_norm_header(col)]].strip() if _norm_header(col) in index else ""
            for col in CAB_COLUMNS
        })  # fmt: skip
    return out
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q`
Expected: PASS (all, including the existing 78).

- [ ] **Step 5: Checkpoint**

`uv run ruff format -q . && uv run ruff check . && uv run mypy . && uv run pytest -q`. Show `git status`; commit only on request (`✨ feat(claude): read the CAB register CSV safely`).

---

### Task 2: Parse rows: keys, dates, current row

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (same section)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `read_register` rows from Task 1 (dicts keyed by `CAB_COLUMNS`).
- Produces:
  - `CAB_KEY: re.Pattern[str]`
  - `register_date(cell: str, cab: dt.date | None, max_lag: int) -> tuple[dt.date | None, str]` (note is `""`, `"swapped"`, `"unverified"` or `"unknown"`)
  - `read_dmy(cell: str) -> dt.date | None`
  - `build_register(read: dict, cfg: dict, today: dt.date) -> dict` with keys `rows` (parsed row dicts: `n`, `status`, `pat_status`, `type`, `kategori`, `name`, `keys`, `reg`, `reg_note`, `cab`, `plan`, `real`, `pat_end`), `by_ticket` (`ticket -> {"current": row | None, "ambiguous": str, "history": list[row]}`), `problems`, `unlinked` (int), `encoding`, `delimiter`, `mtime`

- [ ] **Step 1: Write the failing tests**

```python
def raw(**kw: str) -> dict[str, str]:
    """A row as read_register returns it, with synthetic defaults."""
    base = dict.fromkeys(
        ["Column 1", "Status", "Tanggal Register CAB", "Nama CAB", "jadwal CAB",
         "Deployed Real Date", "Last PAT Date", "Status PAT", "TYPE CAB",
         "Kategori", "Deploye Plan Date"], ""
    )  # fmt: skip
    base.update({"Column 1": "1", "Status": "Closed", "Nama CAB": "[BAST] DA-1234 - x"})
    alias = {"n": "Column 1", "status": "Status", "reg": "Tanggal Register CAB",
             "name": "Nama CAB", "cab": "jadwal CAB", "real": "Deployed Real Date",
             "pat_end": "Last PAT Date", "pat_status": "Status PAT",
             "plan": "Deploye Plan Date"}  # fmt: skip
    base.update({alias[k]: v for k, v in kw.items()})
    return base


def build(
    lb: ModuleType, rows: list[dict[str, str]], cfg=None, today=dt.date(2026, 10, 15)
):
    read = {"rows": rows, "problems": [], "encoding": "utf-8-sig",
            "delimiter": ",", "mtime": None, "off": ""}  # fmt: skip
    return lb.build_register(read, cfg or {}, today)


@pytest.mark.parametrize(
    ("name", "keys"),
    [
        ("[BAST] DA-1234 - x", ["DA-1234"]),
        ("DA1234 - x", ["DA-1234"]),
        ("DA 1234 - x", ["DA-1234"]),
        ("da-1234 and DA-5678", ["DA-1234", "DA-5678"]),
        ("DA-1234 / DA-1234", ["DA-1234"]),
        ("soda 1234 is not a key", []),
        ("BAST Master Data", []),
    ],
)
def test_ticket_keys_are_extracted(lb, name, keys) -> None:
    assert build(lb, [raw(name=name)])["rows"][0]["keys"] == keys


def test_fixed_formats_two_digit_years_and_clock_times(lb: ModuleType) -> None:
    reg = build(lb, [raw(reg="10/12/2026", cab="14/10/26", plan="15/10/26",
                         real="15/10/2026", pat_end="22/10/26")])  # fmt: skip
    row = reg["rows"][0]
    assert row["reg"] == dt.date(2026, 10, 12) and row["cab"] == dt.date(2026, 10, 14)
    assert row["plan"] == dt.date(2026, 10, 15) and row["real"] == dt.date(2026, 10, 15)
    assert row["pat_end"] == dt.date(2026, 10, 22)
    assert not any("Closed Date" in p for p in reg["problems"])


def test_mixed_register_column_uses_the_lag_window(lb: ModuleType) -> None:
    read = lambda reg, cab: lb.register_date(reg, cab, 21)  # noqa: E731
    cab = dt.date(2026, 1, 7)
    assert read("6/1/2026", cab) == (dt.date(2026, 1, 6), "swapped")  # typed 6 Jan
    assert read("1/6/2026", cab) == (dt.date(2026, 1, 6), "")  # M/D already plausible
    assert read("12/31/2025", dt.date(2026, 1, 2)) == (dt.date(2025, 12, 31), "")
    assert read("17/6/2026", dt.date(2026, 6, 17)) == (dt.date(2026, 6, 17), "swapped")
    assert read("5/5/2026", dt.date(2026, 5, 6)) == (dt.date(2026, 5, 5), "")
    assert read("7/27/2026", dt.date(2026, 10, 1)) == (None, "unknown")


def test_register_date_without_a_cab_date_is_unverified(lb: ModuleType) -> None:
    assert lb.register_date("7/27/2026", None, 21) == (
        dt.date(2026, 7, 27),
        "unverified",
    )
    assert lb.register_date("27/7/2026", None, 21) == (
        dt.date(2026, 7, 27),
        "unverified",
    )
    assert lb.register_date("", None, 21) == (None, "")


def test_two_readings_of_a_cell_are_at_least_27_days_apart(lb: ModuleType) -> None:
    closest = 999
    for year in (2026, 2028):
        for a in range(1, 13):
            for b in range(1, 13):
                if a == b:
                    continue
                first = dt.date(year, a, b)  # month a, day b
                second = dt.date(year, b, a)
                closest = min(closest, abs((first - second).days))
    assert closest >= 27
    assert lb.register_cfg_lag({"cab_max_lag_days": 99}) == 26
    assert lb.register_cfg_lag({}) == 21


def test_order_violations_make_only_the_later_field_unknown(lb: ModuleType) -> None:
    reg = build(
        lb, [raw(reg="10/12/2026", cab="14/10/26", real="10/10/26", pat_end="22/10/26")]
    )
    row = reg["rows"][0]
    assert row["real"] is None and row["pat_end"] == dt.date(2026, 10, 22)
    assert any("Deployed Real Date" in p for p in reg["problems"])


def test_future_real_deploy_and_unparsable_dates_are_unknown_and_reported(lb) -> None:
    reg = build(lb, [raw(real="20/10/26", pat_end="soon")], today=dt.date(2026, 10, 15))
    row = reg["rows"][0]
    assert row["real"] is None and row["pat_end"] is None
    assert (
        len(
            [p for p in reg["problems"] if "Deployed Real Date" in p or "Last PAT" in p]
        )
        == 2
    )


def test_current_row_is_the_highest_column_1(lb: ModuleType) -> None:
    rows = [
        raw(n="12", status="Closed"),
        raw(n="3", status="Pending"),
        raw(n="7", status="Cancel"),
    ]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"]["status"] == "Closed" and entry["ambiguous"] == ""
    assert len(entry["history"]) == 3


@pytest.mark.parametrize(
    ("numbers", "expect_ambiguous"),
    [
        (["5", "5"], True),
        (["", "x"], True),
        (["32.0", "31"], False),
        ([" 8 ", "2"], False),
    ],
)
def test_ambiguous_current_row(lb, numbers, expect_ambiguous) -> None:
    rows = [raw(n=n) for n in numbers]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert bool(entry["ambiguous"]) is expect_ambiguous
    assert (entry["current"] is None) is expect_ambiguous
    assert len(entry["history"]) == len(numbers)


def test_invalid_number_rows_are_history_only(lb: ModuleType) -> None:
    rows = [raw(n="x", status="Cancel"), raw(n="4", status="Closed")]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"]["n"] == 4 and entry["ambiguous"] == ""


def test_a_lower_number_with_a_later_date_makes_the_ticket_ambiguous(lb) -> None:
    rows = [
        raw(n="10", cab="2/10/26", real="2/10/26"),
        raw(n="9", cab="5/10/26", real="6/10/26"),
    ]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"] is None and "later date" in entry["ambiguous"]


def test_multi_key_rows_link_to_each_ticket_and_unlinked_rows_are_counted(lb) -> None:
    reg = build(
        lb,
        [raw(n="1", name="DA-1111 and DA-2222"), raw(n="2", name="BAST Master Data")],
    )
    assert set(reg["by_ticket"]) == {"DA-1111", "DA-2222"} and reg["unlinked"] == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "ticket_keys or fixed_formats or mixed_register or unverified or 27_days or order_violations or future_real or current_row or ambiguous or invalid_number or lower_number or multi_key"`
Expected: FAIL (`build_register` etc. missing).

- [ ] **Step 3: Implement**

Add to the CAB section (below `read_register`):

```python
CAB_KEY = re.compile(r"(?<![A-Za-z0-9])DA-?\s?(\d{3,5})(?!\d)", re.IGNORECASE)


def register_cfg_lag(cfg: dict[str, Any]) -> int:
    """cab_max_lag_days (default 21), clamped to 26: readings of a cell are >= 27 days apart."""
    try:
        return max(0, min(int(cfg.get("cab_max_lag_days", 21)), 26))
    except (TypeError, ValueError):
        return 21


def _split_date(cell: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\s*", cell)
    if not m:
        return None
    year = int(m[3])
    return int(m[1]), int(m[2]), year + 2000 if year < 100 else year


def _mk(a: int, b: int, year: int, day_first: bool) -> dt.date | None:
    day, month = (a, b) if day_first else (b, a)
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def read_dmy(cell: str) -> dt.date | None:
    parts = _split_date(cell)
    return _mk(*parts, True) if parts else None


def register_date(
    cell: str, cab: dt.date | None, max_lag: int
) -> tuple[dt.date | None, str]:
    """The register date: primary M/D, typed D/M only if the primary is not plausible."""
    parts = _split_date(cell)
    if parts is None:
        return None, ""
    primary, swapped = _mk(*parts, False), _mk(*parts, True)
    if swapped == primary:
        swapped = None
    if cab is None:
        chosen = primary or swapped
        return chosen, "unverified" if chosen else ""

    def plausible(d: dt.date | None) -> bool:
        return d is not None and 0 <= (cab - d).days <= max_lag

    if plausible(primary):
        return primary, ""
    if plausible(swapped):
        return swapped, "swapped"
    return None, "unknown"


def _column_number(cell: str) -> int | None:
    m = re.fullmatch(r"(\d+)(?:\.0+)?", cell.strip())
    return int(m[1]) if m else None


def _current_row(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    """The ticket's current CAB row by Column 1, or (None, why it is ambiguous)."""
    numbered = [r for r in rows if r["n"] is not None]
    if not numbered:
        return None, "no valid Column 1"
    top = max(r["n"] for r in numbered)
    tops = [r for r in numbered if r["n"] == top]
    if len(tops) > 1:
        return None, f"duplicate Column 1 {top}"
    current = tops[0]
    for r in numbered:
        for field in ("cab", "real"):
            if (
                r is not current
                and r[field]
                and current[field]
                and r[field] > current[field]
            ):
                return None, "a lower Column 1 has a later date"
    return current, ""


def build_register(
    read: dict[str, Any], cfg: dict[str, Any], today: dt.date
) -> dict[str, Any]:
    """Parsed rows plus a per-ticket index. Pure: no file access."""
    max_lag = register_cfg_lag(cfg)
    problems = list(read["problems"])
    rows: list[dict[str, Any]] = []
    for line, rawrow in enumerate(read["rows"], start=1):
        label = rawrow["Column 1"] or f"row {line}"
        n = _column_number(rawrow["Column 1"])
        if n is None:
            problems.append(f"{label}: Column 1 is not a number")

        def date(column: str) -> dt.date | None:
            value = read_dmy(rawrow[column])
            if rawrow[column] and value is None:
                problems.append(f"{label}: {column} is not a date")
            return value

        cab = date("jadwal CAB")
        reg, note = register_date(rawrow["Tanggal Register CAB"], cab, max_lag)
        if rawrow["Tanggal Register CAB"] and reg is None:
            problems.append(f"{label}: Tanggal Register CAB is unknown")
        plan, real, pat_end = (
            date("Deploye Plan Date"),
            date("Deployed Real Date"),
            date("Last PAT Date"),
        )
        if real is not None and real > today:
            problems.append(f"{label}: Deployed Real Date is in the future")
            real = None
        if reg and cab and cab < reg:
            problems.append(f"{label}: jadwal CAB is before the register date")
            cab = None
        if cab and plan and plan < cab:
            problems.append(f"{label}: Deploye Plan Date is before jadwal CAB")
            plan = None
        if cab and real and real < cab:
            problems.append(f"{label}: Deployed Real Date is before jadwal CAB")
            real = None
        if real and pat_end and pat_end < real:
            problems.append(f"{label}: Last PAT Date is before Deployed Real Date")
            pat_end = None
        keys: list[str] = []
        for m in CAB_KEY.finditer(rawrow["Nama CAB"]):
            key = f"DA-{m[1]}"
            if key not in keys:
                keys.append(key)
        rows.append({
            "n": n, "status": rawrow["Status"], "pat_status": rawrow["Status PAT"],
            "type": rawrow["TYPE CAB"], "kategori": rawrow["Kategori"],
            "name": rawrow["Nama CAB"], "keys": keys, "reg": reg, "reg_note": note,
            "cab": cab, "plan": plan, "real": real, "pat_end": pat_end,
        })  # fmt: skip
    by_ticket: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in row["keys"]:
            by_ticket.setdefault(key, {"history": []})["history"].append(row)
    for entry in by_ticket.values():
        entry["current"], entry["ambiguous"] = _current_row(entry["history"])
    return {
        "rows": rows, "by_ticket": by_ticket, "problems": problems,
        "unlinked": sum(1 for r in rows if not r["keys"]),
        "encoding": read.get("encoding", ""), "delimiter": read.get("delimiter", ","),
        "mtime": read.get("mtime"),
    }  # fmt: skip
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff format and check, mypy, pytest; show diff; commit only on request (`✨ feat(claude): parse CAB register rows, keys and dates`).

---

### Task 3: Stage mapping, PAT rules, freshness

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (CAB section)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `build_register` output, `STAGE`, `PAGE_TO_LOGBOOK`, `JIRA_STATUS`.
- Produces:
  - `CAB_STATUS_STAGE`, `CAB_ERROR_STATUS`, `CAB_PAT_CONFIRMED`
  - `cab_info(register: dict, ticket: str, fixing_dates: list[dt.date], today: dt.date) -> dict | None` with keys `ticket`, `history`, `ambiguous`, `row`, `stage` (one of `Ready For Release`, `Deployment`, `PAT`, `Done`, `Rollback`, `Cancel`, `unknown`, or `""` when ambiguous), `planned_end`, `pat_confirmed`, `pat_assumed`, `error_signal`
  - `now_wib() -> dt.datetime`, `cab_sessions(cfg) -> dict`, `last_session_end(now, sessions) -> dt.datetime`, `register_fresh(register, now, sessions) -> bool`, `stale_banner(now, sessions) -> str`, `fixing_dates_by_ticket(rows) -> dict[str, list[dt.date]]`, `load_register_for_run(cfg) -> tuple[dict | None, str]`

- [ ] **Step 1: Write the failing tests**

```python
def info_for(lb, rows, fixing=(), today=dt.date(2026, 10, 15)):
    return lb.cab_info(build(lb, rows, today=today), "DA-1234", list(fixing), today)


@pytest.mark.parametrize(
    ("status", "stage"),
    [
        ("Register CAB", "Ready For Release"), ("Pending", "Ready For Release"),
        ("CAB Ulang", "Ready For Release"), ("OK tp Perlu Rekonfirm", "Ready For Release"),
        ("Done CAB And Progress Deployment", "Deployment"),
        ("Onprogress Deployment", "Deployment"), ("Rollback", "Rollback"),
        ("Cancel", "Cancel"), ("Whatever", "unknown"),
    ],
)  # fmt: skip
def test_register_status_maps_to_a_stage(lb, status, stage) -> None:
    assert info_for(lb, [raw(status=status)])["stage"] == stage


def test_closed_means_deployed_and_pat_decides_the_rest(lb: ModuleType) -> None:
    open_pat = info_for(
        lb, [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    )
    assert open_pat["stage"] == "PAT" and not open_pat["pat_assumed"]
    for pat_status in ("Closed", "NA", "closed"):
        done = info_for(lb, [raw(pat_status=pat_status)])
        assert done["stage"] == "Done" and done["pat_confirmed"]


@pytest.mark.parametrize(
    ("today", "stage"),
    [
        (dt.date(2026, 10, 18), "PAT"),
        (dt.date(2026, 10, 19), "Done"),
        (dt.date(2026, 10, 20), "Done"),
    ],
)
def test_pat_is_assumed_done_on_the_planned_end_date(lb, today, stage) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    info = info_for(lb, rows, today=today)
    assert info["stage"] == stage and info["pat_assumed"] is (stage == "Done")


def test_a_missing_or_invalid_planned_end_never_assumes_done(lb: ModuleType) -> None:
    for pat_end in ("", "soon"):
        info = info_for(
            lb,
            [raw(real="12/10/26", pat_end=pat_end, pat_status="")],
            today=dt.date(2030, 1, 1),
        )
        assert info["stage"] == "PAT" and not info["pat_assumed"]


def test_a_fixing_row_inside_the_window_withholds_the_assumption(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    today = dt.date(2026, 10, 20)
    blocked = info_for(lb, rows, fixing=[dt.date(2026, 10, 15)], today=today)
    assert blocked["stage"] == "PAT" and "Fixing" in blocked["error_signal"]
    late = info_for(lb, rows, fixing=[dt.date(2026, 10, 25)], today=today)
    assert late["stage"] == "Done" and late["error_signal"] == ""
    early = info_for(lb, rows, fixing=[dt.date(2026, 10, 11)], today=today)
    assert early["stage"] == "Done"
    no_deploy = info_for(
        lb, [raw(pat_end="19/10/26")], fixing=[dt.date(2026, 10, 15)], today=today
    )
    assert (
        no_deploy["stage"] == "Done"
    )  # no deploy date known: only the status signals apply


def test_confirmed_pat_ignores_error_signals(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Closed")]
    info = info_for(lb, rows, fixing=[dt.date(2026, 10, 15)])
    assert info["stage"] == "Done" and info["pat_confirmed"]


def test_rollback_and_cab_ulang_are_error_statuses(lb: ModuleType) -> None:
    for status in ("Rollback", "CAB Ulang", "Cancel"):
        assert status in info_for(lb, [raw(status=status)])["error_signal"]


def test_an_ambiguous_ticket_has_no_stage(lb: ModuleType) -> None:
    info = info_for(lb, [raw(n="5"), raw(n="5")])
    assert info["row"] is None and info["stage"] == "" and info["ambiguous"]
    assert lb.cab_info(build(lb, [raw()]), "DA-9999", [], dt.date(2026, 10, 15)) is None


def test_fixing_dates_come_from_logbook_rows(lb: ModuleType) -> None:
    rows = [row("2026-10-15", "DA-1", "Fixing"), row("2026-10-16", "DA-1", "Testing")]
    assert lb.fixing_dates_by_ticket(rows) == {"DA-1": [dt.date(2026, 10, 15)]}


WED_1500 = dt.datetime(2026, 10, 14, 15, 0, tzinfo=dt.timezone(dt.timedelta(hours=7)))


def test_last_session_end_for_monday_and_wednesday_sessions(lb: ModuleType) -> None:
    wib = dt.timezone(dt.timedelta(hours=7))
    sessions = lb.cab_sessions({})
    assert sessions == {"days": ["Mon", "Wed"], "end": "15:00"}
    thursday = dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib)
    assert lb.last_session_end(thursday, sessions) == WED_1500
    wed_before = dt.datetime(2026, 10, 14, 14, 59, tzinfo=wib)
    assert lb.last_session_end(wed_before, sessions) == dt.datetime(
        2026, 10, 12, 15, 0, tzinfo=wib
    )
    saturday = dt.datetime(2026, 10, 17, 9, 0, tzinfo=wib)
    assert lb.last_session_end(saturday, sessions) == WED_1500
    monday = dt.datetime(2026, 10, 19, 16, 0, tzinfo=wib)
    assert lb.last_session_end(monday, sessions) == dt.datetime(
        2026, 10, 19, 15, 0, tzinfo=wib
    )


@pytest.mark.parametrize(("minutes", "fresh"), [(-1, False), (0, True), (1, True)])
def test_register_is_fresh_at_or_after_the_session_end(lb, minutes, fresh) -> None:
    sessions = lb.cab_sessions({})
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=WED_1500.tzinfo)
    register = {"mtime": WED_1500 + dt.timedelta(minutes=minutes)}
    assert lb.register_fresh(register, now, sessions) is fresh
    assert lb.register_fresh({"mtime": None}, now, sessions) is False


def test_stale_banner_names_the_session(lb: ModuleType) -> None:
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=WED_1500.tzinfo)
    text = lb.stale_banner(now, lb.cab_sessions({}))
    assert "Wednesday" in text and "14 Oct" in text


def test_load_register_for_run_reports_why_it_is_off(lb, tmp_path) -> None:
    register, note = lb.load_register_for_run(
        {"cab_register": str(tmp_path / "nope.csv")}
    )
    assert register is None and "no CAB register" in note
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")])
    register, note = lb.load_register_for_run({"cab_register": str(path)})
    assert note == "" and "DA-1234" in register["by_ticket"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "register_status_maps or closed_means or planned_end or fixing_row or confirmed_pat or error_statuses or ambiguous_ticket or fixing_dates or session_end or fresh_at_or_after or stale_banner or load_register_for_run"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
CAB_STATUS_STAGE = {
    "register cab": "Ready For Release", "pending": "Ready For Release",
    "cab ulang": "Ready For Release", "ok tp perlu rekonfirm": "Ready For Release",
    "done cab and progress deployment": "Deployment",
    "onprogress deployment": "Deployment", "closed": "PAT",
    "rollback": "Rollback", "cancel": "Cancel",
}  # fmt: skip
CAB_ERROR_STATUS = {"rollback", "cab ulang", "cancel"}
CAB_PAT_CONFIRMED = {"closed", "na"}  # Status PAT: Closed, or NA = not applicable
_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def now_wib() -> dt.datetime:
    return dt.datetime.now(WIB)


def fixing_dates_by_ticket(rows: list[dict[str, str]]) -> dict[str, list[dt.date]]:
    out: dict[str, list[dt.date]] = {}
    for r in rows:
        if r["status"] == "Fixing":
            out.setdefault(r["ticket"], []).append(dt.date.fromisoformat(r["date"]))
    return out


def cab_info(
    register: dict[str, Any],
    ticket: str,
    fixing_dates: list[dt.date],
    today: dt.date,
) -> dict[str, Any] | None:
    """The CAB view of one ticket: stage, PAT state and error signal (spec sections 4 and 5)."""
    entry = register["by_ticket"].get(ticket)
    if entry is None:
        return None
    row = entry["current"]
    info: dict[str, Any] = {
        "ticket": ticket, "history": entry["history"], "ambiguous": entry["ambiguous"],
        "row": row, "stage": "", "planned_end": None, "pat_confirmed": False,
        "pat_assumed": False, "error_signal": "",
    }  # fmt: skip
    if row is None:
        return info
    status = row["status"].lower()
    stage = CAB_STATUS_STAGE.get(status, "unknown")
    end = row["pat_end"]
    info["planned_end"] = end
    signal = ""
    if status in CAB_ERROR_STATUS:
        signal = f"the register status is {row['status']}"
    else:
        start = row["real"] or row["plan"]
        if start and end and any(start <= d <= end for d in fixing_dates):
            signal = "a Fixing row in the logbook during the PAT window"
    info["error_signal"] = signal
    if stage == "PAT":
        confirmed = row["pat_status"].lower() in CAB_PAT_CONFIRMED
        assumed = not confirmed and not signal and end is not None and today >= end
        info["pat_confirmed"], info["pat_assumed"] = confirmed, assumed
        if confirmed or assumed:
            stage = "Done"
    info["stage"] = stage
    return info


def cab_sessions(cfg: dict[str, Any]) -> dict[str, Any]:
    given = cfg.get("cab_sessions") or {}
    return {"days": given.get("days", ["Mon", "Wed"]), "end": given.get("end", "15:00")}


def last_session_end(now: dt.datetime, sessions: dict[str, Any]) -> dt.datetime:
    days = {_WEEKDAYS[d[:3].lower()] for d in sessions["days"]}
    hour, minute = (int(x) for x in sessions["end"].split(":"))
    for back in range(8):
        day = (now - dt.timedelta(days=back)).date()
        if day.weekday() in days:
            end = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=WIB)
            if end <= now:
                return end
    raise ValueError("cab_sessions lists no session day")


def register_fresh(
    register: dict[str, Any], now: dt.datetime, sessions: dict[str, Any]
) -> bool:
    """Fresh = the file was modified at or after the end of the last CAB session."""
    mtime = register.get("mtime")
    return mtime is not None and mtime >= last_session_end(now, sessions)


def stale_banner(now: dt.datetime, sessions: dict[str, Any]) -> str:
    end = last_session_end(now, sessions)
    return (
        f"CAB register not updated since the {end:%A} {end.day} {end:%b} session; "
        "CAB flags are hidden."
    )


def load_register_for_run(cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """(register, note). Register is None when the feature is off; note says why."""
    path = resolve_register_path(cfg)
    if path is None:
        return None, ""
    read = read_register(path)
    if read["off"]:
        return None, read["off"]
    return build_register(read, cfg, now_wib().date()), ""
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest; also the 3.9/3.12 helper import check:
`for v in 3.9 3.12; do uv run --no-project --python $v python -c "import importlib.util,sys;s=importlib.util.spec_from_file_location('l','CLAUDE/skills/logbook/logbook.py');m=importlib.util.module_from_spec(s);sys.modules['l']=m;s.loader.exec_module(m);print('$v ok')"; done`
Expected: `3.9 ok`, `3.12 ok`. Show diff; commit only on request (`✨ feat(claude): map CAB statuses to stages and decide PAT state`).

---

### Task 4: `cab` command

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`cmd_cab`, argparse)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: Tasks 1-3 functions, `load_config`, `load_cache`, `read_rows`.
- Produces: `cmd_cab(args)` with `args.ticket: str` and `args.show_unlinked: bool`; `register_quality(register) -> list[str]` (pure, returns the quality report lines).

- [ ] **Step 1: Write the failing tests**

```python
def run_cab(lb, capsys, **kw):
    lb.cmd_cab(
        argparse.Namespace(
            ticket=kw.get("ticket", ""), show_unlinked=kw.get("show_unlinked", False)
        )
    )
    return capsys.readouterr().out


def cab_env(lb, tmp_path, rows):
    path = tmp_path / "reg.csv"
    write_register(path, rows)
    (tmp_path / "config.json").write_text(json.dumps({"cab_register": str(path)}))
    return path


def test_cab_report_lists_tickets_dates_and_quality(lb, tmp_path, capsys) -> None:
    cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                reg="10/12/2026",
                cab="14/10/26",
                real="15/10/26",
                pat_end="22/10/26",
                pat_status="",
            ),
            reg_line(n="2", name="BAST Master Data"),
            reg_line(
                n="3",
                status="Onprogress Deployment",
                name="DA-5678 - y",
                pat_status="Closed",
            ),
        ],
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment"}})
    )
    out = run_cab(lb, capsys)
    assert "DA-1234" in out and "2026-10-15" in out and "2026-10-22" in out
    assert "Jira Deployment" in out
    assert "1 row(s) without a ticket key" in out
    assert "Onprogress Deployment" in out and "Status PAT is Closed" in out
    assert "BAST Master Data" not in out


def test_cab_show_unlinked_lists_them(lb, tmp_path, capsys) -> None:
    cab_env(lb, tmp_path, [reg_line(n="2", name="BAST Master Data")])
    assert "BAST Master Data" in run_cab(lb, capsys, show_unlinked=True)


def test_cab_single_ticket_shows_history_and_notes_jira_ahead(
    lb, tmp_path, capsys
) -> None:
    cab_env(
        lb,
        tmp_path,
        [reg_line(n="1", status="Register CAB"), reg_line(n="2", status="Pending")],
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment"}})
    )
    out = run_cab(lb, capsys, ticket="DA-1234")
    assert "history" in out.lower() and out.count("Register CAB") >= 1
    assert "Jira ahead of the register" in out


def test_cab_reports_why_it_is_off(lb, tmp_path, capsys) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"cab_register": str(tmp_path / "nope.csv")})
    )
    assert "no CAB register" in run_cab(lb, capsys)


def test_cab_reports_ambiguous_tickets(lb, tmp_path, capsys) -> None:
    cab_env(lb, tmp_path, [reg_line(n="5"), reg_line(n="5")])
    assert "ambiguous" in run_cab(lb, capsys)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "cab_report or cab_show or cab_single or cab_reports"`
Expected: FAIL (`cmd_cab` missing).

- [ ] **Step 3: Implement**

```python
def register_quality(register: dict[str, Any]) -> list[str]:
    """Data quality lines for the cab report (counts, not row dumps)."""
    lines = list(register["problems"])
    if register["unlinked"]:
        lines.append(
            f"{register['unlinked']} row(s) without a ticket key (--show-unlinked lists them)"
        )
    for row in register["rows"]:
        deploying = row["status"].lower() in (
            "onprogress deployment",
            "done cab and progress deployment",
        )
        if deploying and row["pat_status"].lower() == "closed":
            lines.append(
                f"Column 1 {row['n']}: status is {row['status']} but Status PAT is Closed"
            )
        if row["reg_note"] == "unverified":
            lines.append(
                f"Column 1 {row['n']}: register date is unverified (no CAB date)"
            )
        if row["reg_note"] == "swapped":
            lines.append(f"Column 1 {row['n']}: register date read as day/month")
    for key, entry in sorted(register["by_ticket"].items()):
        if entry["ambiguous"]:
            lines.append(f"{key}: ambiguous current row ({entry['ambiguous']})")
        elif len(entry["history"]) > 1:
            lines.append(
                f"{key}: {len(entry['history'])} CAB rows (the highest Column 1 is current)"
            )
    return lines


def _iso(value: dt.date | None) -> str:
    return value.isoformat() if value else "-"


def cmd_cab(args: argparse.Namespace) -> None:
    """Per-ticket view of the CAB register. Read-only."""
    cfg = load_config()
    register, note = load_register_for_run(cfg)
    if register is None:
        print(note or "No CAB register configured (set cab_register in config.json).")
        return
    now, sessions = now_wib(), cab_sessions(cfg)
    fresh = register_fresh(register, now, sessions)
    cache, fixing = load_cache(), fixing_dates_by_ticket(read_rows())
    print(
        f"## CAB register: {len(register['rows'])} row(s), {register['encoding']}, "
        f"delimiter {register['delimiter']!r}, "
        + ("fresh" if fresh else stale_banner(now, sessions))
    )
    for ticket in sorted(register["by_ticket"]):
        if args.ticket and ticket != args.ticket:
            continue
        info = cab_info(register, ticket, fixing.get(ticket, []), now.date())
        assert info is not None
        jira = cache.get(ticket, {}).get("jira_status", "")
        if info["row"] is None:
            print(f"- {ticket}: ambiguous ({info['ambiguous']}) | Jira {jira or '-'}")
        else:
            row = info["row"]
            print(
                f"- {ticket}: {info['stage']} | Jira {jira or '-'} | CAB {_iso(row['cab'])} | "
                f"deploy {_iso(row['real'] or row['plan'])} | PAT end {_iso(row['pat_end'])} | "
                f"Status PAT {row['pat_status'] or '-'}"
            )
            jira_stage = PAGE_TO_LOGBOOK.get(JIRA_STATUS.get(jira, ""), "")
            if STAGE.get(jira_stage, 0) > STAGE.get(info["stage"], 0) > 0:
                print("  note: Jira ahead of the register")
        if args.ticket:
            for r in info["history"]:
                print(
                    f"  history: Column 1 {r['n']} | {r['status']} | CAB {_iso(r['cab'])}"
                )
    print("\n## Data quality")
    quality = register_quality(register)
    print(
        "\n".join(f"- {line}" for line in quality) if quality else "- nothing to flag"
    )
    if args.show_unlinked:
        print("\n## Unlinked rows")
        for r in register["rows"]:
            if not r["keys"]:
                print(f"- Column 1 {r['n']}: {r['name']}")
```

Add the subcommand in `main()` after `pipeline`:

```python
cab = sub.add_parser("cab", help="Per-ticket view of the CAB register (read-only)")
cab.add_argument("--ticket", default="", help="show one ticket with its history")
cab.add_argument(
    "--show-unlinked", action="store_true", help="list rows without a ticket key"
)
cab.set_defaults(func=cmd_cab)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q`
Expected: PASS. (Adjust the exact substrings in the tests, not the meaning, if the printed wording differs by a word.)

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest; show diff; commit only on request (`✨ feat(claude): add the read-only cab report`).

---

### Task 5: Board and `check` flags, Cancel mapping

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`JIRA_STATUS`, `STATUS_COLOR`, `cab_flags`, `board_entry`, `derive_board`, `render_board`, `cmd_pipeline`, `cmd_check`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `cab_info`, `register_fresh`, `fixing_dates_by_ticket`, `load_register_for_run`, `stale_banner`, existing `board_entry` / `derive_board` / `render_board` / `cmd_check`.
- Produces:
  - `JIRA_STATUS["Cancel"] = "CANCELLED"`, `STATUS_COLOR["CANCELLED"] = "neutral"`
  - `cab_flags(info: dict | None, word: str, today: dt.date) -> tuple[list[tuple[str, str]], bool]` (flags, propose_done)
  - `board_entry(ticket, info, item, ev, today, live, no_git="", cab=None, cab_fresh=False, not_registered=False)`; the entry gains `cab_line: str`, `propose_done: bool`
  - `derive_board(cache, items, evidence, today, repo_paths=None, register=None, now=None, sessions=None)`
  - `render_board(entries, live, refreshed, notes, cab_banner="")`

- [ ] **Step 1: Write the failing tests**

```python
def cab_entry(
    lb,
    word_jira,
    rows,
    *,
    today=dt.date(2026, 10, 15),
    fresh=True,
    item=None,
    not_registered=False,
    fixing=(),
):
    register = build(lb, rows, today=today)
    cab = lb.cab_info(register, "DA-1234", list(fixing), today)
    info = {"jira_status": word_jira}
    return lb.board_entry(
        "DA-1234", info, item or [], None, today, True, "", cab, fresh, not_registered
    )


def flag_fixes(e) -> list[str]:
    return [fix for _, fix in e["flags"]]


def test_jira_cancel_leaves_the_board(lb: ModuleType) -> None:
    assert (
        lb.JIRA_STATUS["Cancel"] == "CANCELLED"
        and lb.STATUS_COLOR["CANCELLED"] == "neutral"
    )
    cache = {
        "DA-1": {"track": True, "jira_status": "Cancel", "refreshed": TODAY.isoformat()}
    }
    entries, _, _ = lb.derive_board(cache, [], {}, TODAY)
    assert entries == []


def test_register_ahead_of_jira_proposes_the_jira_move(lb: ModuleType) -> None:
    e = cab_entry(
        lb, "Deployment", [raw(real="15/10/26", pat_end="22/10/26", pat_status="")]
    )
    assert any("move Jira to PAT" in f for f in flag_fixes(e))


def test_jira_ahead_of_the_register_is_not_a_board_flag(lb: ModuleType) -> None:
    e = cab_entry(lb, "Deployment", [raw(status="Register CAB")])
    assert e["flags"] == []


def test_pat_done_is_proposed_with_the_register_values(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 19))
    assert e["propose_done"] is True
    text = " ".join(t for t, _ in e["flags"])
    assert "Status PAT" in text and "Open" in text and "2026-10-19" in text


def test_pat_window_ended_with_an_error_signal_proposes_nothing(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    e = cab_entry(
        lb, "PAT", rows, today=dt.date(2026, 10, 20), fixing=[dt.date(2026, 10, 15)]
    )
    assert e["propose_done"] is False
    assert any("PAT window ended but" in t for t, _ in e["flags"])


def test_before_the_planned_end_the_board_says_nothing(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 16))
    assert e["flags"] == [] and e["propose_done"] is False


def test_the_register_decides_pat_and_the_changelog_age_is_skipped(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    register = build(lb, rows)
    cab = lb.cab_info(register, "DA-1234", [], TODAY)
    info = {"jira_status": "PAT", "pat_since": "2026-01-01"}
    e = lb.board_entry("DA-1234", info, [], None, TODAY, True, "", cab, True, False)
    assert not any("in PAT since" in t for t, _ in e["flags"])


def test_stale_register_adds_no_cab_flags_and_keeps_the_old_pat_logic(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Closed")]
    e = cab_entry(lb, "PAT", rows, fresh=False)
    assert e["propose_done"] is False
    assert not any("register" in t.lower() for t, _ in e["flags"])


def test_ambiguous_ticket_gets_no_cab_flag(lb: ModuleType) -> None:
    e = cab_entry(lb, "Deployment", [raw(n="5"), raw(n="5")])
    assert e["flags"] == []


def test_rollback_and_cancel_flags_only_when_jira_is_later(lb: ModuleType) -> None:
    rollback = cab_entry(lb, "PAT", [raw(status="Rollback")])
    assert any("Rollback" in t for t, _ in rollback["flags"])
    assert not any("move Jira" in f for f in flag_fixes(rollback))
    early = cab_entry(lb, "Data Development", [raw(status="Rollback")])
    assert early["flags"] == []
    cancel = cab_entry(lb, "Deployment", [raw(status="Cancel")])
    assert any("move Jira to Cancel" in f for f in flag_fixes(cancel))


def test_not_registered_flag_comes_only_from_derive_board(lb: ModuleType) -> None:
    today = dt.date(2026, 10, 15)
    wib = dt.timezone(dt.timedelta(hours=7))
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib)
    register = build(lb, [raw(name="DA-9999 - other")], today=today)
    register["mtime"] = dt.datetime(2026, 10, 14, 16, 0, tzinfo=wib)
    cache = {
        "DA-1234": {
            "track": True,
            "jira_status": "Ready For Release",
            "refreshed": today.isoformat(),
        }
    }
    items = [
        [
            row("2026-10-08", "DA-1234", "Ready For Release"),
            row("2026-10-12", "DA-1234", "Ready For Release"),
        ]
    ]
    entries, _, _ = lb.derive_board(
        cache, items, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert any("not registered for CAB" in t for t, _ in entries[0]["flags"])
    young = [[row("2026-10-14", "DA-1234", "Ready For Release")]]
    entries, _, _ = lb.derive_board(
        cache, young, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])
    nonjira = {
        "bug-1": {
            "track": True,
            "jira_status": "Ready For Release",
            "refreshed": today.isoformat(),
        }
    }
    old = [[row("2026-10-01", "bug-1", "Ready For Release")]]
    entries, _, _ = lb.derive_board(
        nonjira, old, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])
    register["mtime"] = dt.datetime(
        2026, 10, 14, 14, 0, tzinfo=wib
    )  # before the session end
    entries, _, _ = lb.derive_board(
        cache, items, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])


def test_board_line_shows_the_cab_dates(lb: ModuleType) -> None:
    e = cab_entry(
        lb,
        "Deployment",
        [raw(status="Onprogress Deployment", cab="14/10/26", plan="15/10/26")],
    )
    assert "CAB 2026-10-14" in e["cab_line"] and "deploy 2026-10-15" in e["cab_line"]


def test_render_board_batches_pat_done_and_shows_the_register_banner(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 19))
    text = lb.render_board(
        [e],
        True,
        "2026-10-19",
        [],
        "CAB register not updated since the Wednesday 14 Oct session",
    )
    assert "PAT done: propose Done" in text and "DA-1234" in text
    assert "CAB register not updated" in text


def test_check_reports_register_flags_only_when_fresh(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    path = cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                real="15/10/26",
                cab="14/10/26",
                pat_end="22/10/26",
                pat_status="",
            )
        ],
    )
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg["repo_paths"] = {}
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    today = dt.date.today().isoformat()
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment", "refreshed": today}})
    )
    write_csv(lb.LOGBOOK, [row("2026-10-12", "DA-1234", "Deployment")])
    monkeypatch.setattr(lb, "_run", fake_run_factory([]))
    wib = dt.timezone(dt.timedelta(hours=7))
    monkeypatch.setattr(
        lb, "now_wib", lambda: dt.datetime(2026, 10, 16, 9, 0, tzinfo=wib)
    )
    os.utime(path, (dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib).timestamp(),) * 2)
    out = run_check(lb, capsys)
    assert "move Jira to PAT" in out
    os.utime(path, (dt.datetime(2026, 10, 13, 9, 0, tzinfo=wib).timestamp(),) * 2)
    out = run_check(lb, capsys)
    assert "move Jira to PAT" not in out and "not updated" in out
```

(Add `import os` to the test file imports in the same edit as its first use.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "cancel_leaves or register_ahead or jira_ahead or pat_done_is or window_ended or before_the_planned or register_decides or stale_register_adds or ambiguous_ticket_gets or rollback_and_cancel or not_registered or board_line_shows or render_board_batches or check_reports_register"`
Expected: FAIL.

- [ ] **Step 3: Implement**

Constants: add `"Cancel": "CANCELLED",` to `JIRA_STATUS` and `"CANCELLED": "neutral",` to `STATUS_COLOR`.

Add (CAB section, after `load_register_for_run`):

```python
def cab_flags(
    info: dict[str, Any] | None, word: str, today: dt.date
) -> tuple[list[tuple[str, str]], bool]:
    """Board and check flags from the register: (flags, propose_done). Spec 6.2."""
    if info is None or info["row"] is None or word in ("HOLD", "CANCELLED", "TODO"):
        return [], False
    stage, row = info["stage"], info["row"]
    flags: list[tuple[str, str]] = []
    jira_rank = STAGE.get(PAGE_TO_LOGBOOK.get(word, ""), 0)
    if stage == "Done" and word == "PAT":
        kind = "confirmed" if info["pat_confirmed"] else "assumed"
        return [(
            f"PAT done ({kind}): Status PAT {row['pat_status'] or '-'}, planned end "
            f"{_iso(info['planned_end'])}",
            "propose Done in Jira and the logbook",
        )], True  # fmt: skip
    if stage in ("Deployment", "PAT", "Done") and STAGE[stage] > jira_rank > 0:
        target = "PAT" if stage == "Done" else stage
        flags.append(
            (f"register says {stage}, Jira is {word}", f"move Jira to {target}")
        )
    if (
        word == "PAT" and stage == "PAT" and info["error_signal"]
        and info["planned_end"] is not None and today >= info["planned_end"]
    ):  # fmt: skip
        flags.append((
            f"PAT window ended but {info['error_signal']}", "check it before moving to Done"
        ))  # fmt: skip
    if stage == "Rollback" and jira_rank > STAGE["Development"]:
        flags.append((
            f"register says Rollback, Jira is {word}",
            "check the rollback: Jira should be Data Development or Bug Fixing",
        ))  # fmt: skip
    if stage == "Cancel" and word != "CANCELLED":
        flags.append((f"register says Cancel, Jira is {word}", "move Jira to Cancel"))
    return flags, False


def rfr_run_start(item: list[dict[str, str]]) -> dt.date | None:
    """First date of the trailing run of 'Ready For Release' logbook rows, or None."""
    start = None
    for r in reversed(item):
        if r["status"] != "Ready For Release":
            break
        start = dt.date.fromisoformat(r["date"])
    return start
```

`board_entry`: extend the signature with `cab: dict[str, Any] | None = None, cab_fresh: bool = False, not_registered: bool = False`; in the entry dict add `"propose_done": False, "cab_line": ""`; after the entry dict is built (before the Hold branch) add:

```python
    row = cab["row"] if cab else None
    if row is not None:
        entry["cab_line"] = (
            f"CAB {_iso(row['cab'])} | deploy {_iso(row['real'] or row['plan'])} | "
            f"PAT end {_iso(row['pat_end'])}"
        )
    cab_decides = bool(cab_fresh and cab and row is not None)
```

Change `if word == "PAT":` (the changelog-based block) to `if word == "PAT" and not cab_decides:`, and add after the Jira-vs-logbook block, before `return entry`:

```python
if cab_fresh:
    cflags, propose = cab_flags(cab, word, today)
    flags.extend(cflags)
    entry["propose_done"] = propose
    if not_registered:
        flags.append(
            ("not registered for CAB", "register the BAST in the CAB register")
        )
```

`derive_board`: new signature `(cache, items, evidence, today, repo_paths=None, register=None, now=None, sessions=None)`. Before the loop compute:

```python
fresh = bool(
    register is not None
    and now is not None
    and sessions is not None
    and register_fresh(register, now, sessions)
)
fixing = fixing_dates_by_ticket([r for i in items for r in i])
grace = int(load_config().get("cab_grace_days", 3)) if fresh else 3
```

and per ticket pass the new arguments:

```python
cab = cab_info(register, ticket, fixing.get(ticket, []), today) if register else None
start = rfr_run_start(item)
not_registered = bool(
    fresh
    and cab is None
    and JIRA_KEY.fullmatch(ticket)
    and start is not None
    and (today - start).days >= grace
)
e = board_entry(
    ticket,
    info,
    item,
    evidence.get(ticket),
    today,
    info.get("refreshed", "") == today.isoformat(),
    _no_git(item, repo_paths),
    cab,
    fresh,
    not_registered,
)
```

Skip cancelled tickets: `if e["word"] not in ("DONE", "CANCELLED"):`. Note `not_registered` is only appended by `board_entry` when the word is not Hold and Jira is live; additionally require in `board_entry` that `word == "READY FOR RELEASE"` before appending the flag.

`render_board`: new parameter `cab_banner: str = ""`. After the existing stale-Jira banner add `if cab_banner: lines += ["", cab_banner]`. Before the stage groups add:

```python
    proposals = [e for e in entries if e.get("propose_done")]
    if proposals:
        lines += ["", f"## PAT done: propose Done ({len(proposals)})"]
        lines += [f"- {e['ticket']}: {e['flags'][0][0]}" for e in proposals]
```

and after each entry's `next:` line print `lines.append(f"  {e['cab_line']}")` when `e["cab_line"]` is non-empty. (`e["flags"][0]` is the PAT-done flag because `cab_flags` returns it alone.)

`cmd_pipeline`: after `repo_paths = ...` add

```python
    register, cab_note = load_register_for_run(cfg)
    now, sessions = now_wib(), cab_sessions(cfg)
    banner = ""
    if cab_note:
        notes.append(cab_note)
    elif register is not None and not register_fresh(register, now, sessions):
        banner = stale_banner(now, sessions)
```

(declare `notes` first from `git_evidence`, as today), pass `register, now, sessions` to `derive_board` and `banner` to `render_board`. Keep the existing positional calls working (new parameters have defaults).

`cmd_check`: before `print(f"## Recheck ...")` add the block:

```python
register, cab_note = load_register_for_run(cfg)
if cab_note:
    notes.append(cab_note)
elif register is not None:
    now, sessions = now_wib(), cab_sessions(cfg)
    if register_fresh(register, now, sessions):
        fixing = fixing_dates_by_ticket(read_rows())
        for ticket in sorted(
            set(items) | {t for t, i in cache.items() if i.get("track")}
        ):
            info = cache.get(ticket, {})
            word = (
                JIRA_STATUS.get(info.get("jira_status", ""))
                if jira_fresh(info)
                else None
            )
            if not word:
                continue
            cab = cab_info(register, ticket, fixing.get(ticket, []), now.date())
            flags, _ = cab_flags(cab, word, now.date())
            findings += [f"{ticket}: {text} -> {fix}" for text, fix in flags]
    else:
        notes.append(stale_banner(now, sessions))
```

The `check` test patches `now_wib` on the module, so `cmd_check` must call `now_wib()` (not a cached value). The same holds for `cmd_cab` and `load_register_for_run`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q && for v in 3.9 3.12; do uv run --no-project --python $v --with pytest python -m pytest tests/test_logbook.py -q -p no:cacheprovider 2>&1 | tail -1; done`
Expected: all pass on 3.11, 3.9 and 3.12. In the stale-register test the existing changelog-based flags (`in PAT since`, `PAT date unknown`) may still appear; only register flags must be absent.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, full pytest; show diff; commit only on request (`✨ feat(claude): add CAB register flags to the board and check`).

---

### Task 6: "CAB this week" in `week`

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`cab_week_lines`, `cmd_week`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `build_register` output, `iso_week`, `load_register_for_run`, `register_fresh`, `stale_banner`.
- Produces: `cab_week_lines(week: str, register: dict | None, banner: str = "") -> list[str]`; `cmd_week` prints the block and no longer returns early when only the CAB block has content.

- [ ] **Step 1: Write the failing tests**

```python
def week_lines(lb, rows, week="2026-W42", banner=""):
    return lb.cab_week_lines(week, build(lb, rows), banner)


def test_cab_week_block_groups_registered_sessions_deployed_and_pat_ends(
    lb: ModuleType,
) -> None:
    rows = [
        raw(
            n="1",
            name="DA-1111 - a",
            reg="10/12/2026",
            cab="12/10/26",
            real="13/10/26",
            pat_end="18/10/26",
        ),
        raw(
            n="2",
            name="DA-2222 - b",
            reg="10/12/2026",
            cab="14/10/26",
            real="15/10/26",
            pat_end="22/10/26",
        ),
        raw(n="3", name="DA-3333 - c", status="Register CAB", reg="10/12/2026"),
    ]
    text = "\n".join(week_lines(lb, rows))
    assert "### CAB this week" in text
    assert "Registered: DA-1111, DA-2222, DA-3333 (date unverified)" in text
    assert "2026-10-12 (DA-1111)" in text and "2026-10-14 (DA-2222)" in text
    assert "DA-1111 (2026-10-13)" in text and "DA-2222 (2026-10-15)" in text
    assert "PAT windows ending" in text and "DA-1111 (2026-10-18)" in text


def test_cab_week_lists_a_ticket_once_per_row_and_keeps_history(lb: ModuleType) -> None:
    rows = [
        raw(
            n="1", reg="10/12/2026", cab="12/10/26", real="13/10/26", pat_end="20/10/26"
        ),
        raw(
            n="2", reg="10/14/2026", cab="14/10/26", real="14/10/26", pat_end="21/10/26"
        ),
    ]
    text = "\n".join(week_lines(lb, rows))
    assert text.count("DA-1234") == 6  # registered, session and deploy, once per row


def test_cab_week_skips_rollback_and_cancel_in_pat_windows(lb: ModuleType) -> None:
    rows = [
        raw(
            status="Rollback",
            reg="10/12/2026",
            cab="12/10/26",
            real="13/10/26",
            pat_end="16/10/26",
        )
    ]
    assert "PAT windows ending" not in "\n".join(week_lines(lb, rows))


def test_cab_week_empty_week_prints_nothing_and_off_register_too(
    lb: ModuleType,
) -> None:
    assert week_lines(lb, [raw(reg="1/5/2026", cab="2/5/26")]) == []
    assert lb.cab_week_lines("2026-W42", None, "") == []


def test_cab_week_marks_unverified_dates_counts_unlinked_and_shows_the_banner(
    lb,
) -> None:
    rows = [
        raw(n="1", reg="10/12/2026"),
        raw(n="2", name="BAST Master Data", reg="10/12/2026", cab="12/10/26"),
    ]
    text = "\n".join(
        week_lines(
            lb,
            rows,
            banner="CAB register not updated since the Wednesday 14 Oct session",
        )
    )
    assert "unverified" in text and "Unlinked rows: 1" in text
    assert text.splitlines()[0].startswith("CAB register not updated")


def test_week_prints_the_cab_block_even_with_no_logbook_entries(
    lb, tmp_path, capsys
) -> None:
    cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                reg="10/12/2026",
                cab="12/10/26",
                real="13/10/26",
                pat_end="18/10/26",
            )
        ],
    )
    lb.cmd_week(argparse.Namespace(week="2026-W42"))
    out = capsys.readouterr().out
    assert "CAB this week" in out and "No entries" not in out


def test_week_without_a_register_still_says_no_entries(lb, tmp_path, capsys) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"cab_register": str(tmp_path / "nope.csv")})
    )
    lb.cmd_week(argparse.Namespace(week="2026-W42"))
    assert "No entries for 2026-W42." in capsys.readouterr().out
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "cab_week or week_prints_the_cab or week_without_a_register"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
def cab_week_lines(
    week: str, register: dict[str, Any] | None, banner: str = ""
) -> list[str]:
    """The 'CAB this week' block from every valid register row. Empty when nothing happened."""
    if register is None:
        return []

    def in_week(d: dt.date | None) -> bool:
        return d is not None and iso_week(d.isoformat()) == week

    def label(r: dict[str, Any]) -> str:
        return ", ".join(r["keys"]) if r["keys"] else ""

    registered, sessions, deployed, pat_ends = [], {}, [], []
    unlinked = 0
    for r in register["rows"]:
        touched = False
        name = label(r)
        if in_week(r["reg"]):
            touched = True
            if name:
                registered.append(
                    name
                    + (" (date unverified)" if r["reg_note"] == "unverified" else "")
                )
        if in_week(r["cab"]):
            touched = True
            if name:
                sessions.setdefault(r["cab"], []).append(name)
        if in_week(r["real"]):
            touched = True
            if name:
                deployed.append(f"{name} ({r['real'].isoformat()})")
        if in_week(r["pat_end"]) and r["status"].lower() == "closed":
            touched = True
            if name:
                pat_ends.append(f"{name} ({r['pat_end'].isoformat()})")
        if touched and not name:
            unlinked += 1
    lines: list[str] = []
    if registered:
        lines.append(f"- Registered: {', '.join(registered)}")
    if sessions:
        parts = [
            f"{d.isoformat()} ({', '.join(names)})"
            for d, names in sorted(sessions.items())
        ]
        lines.append(f"- CAB sessions: {'; '.join(parts)}")
    if deployed:
        lines.append(f"- Deployed: {', '.join(deployed)}")
    if pat_ends:
        lines.append(f"- PAT windows ending: {', '.join(pat_ends)}")
    if unlinked:
        lines.append(f"- Unlinked rows: {unlinked}")
    if not lines:
        return []
    head = [banner, ""] if banner else []
    return head + ["### CAB this week", *lines]
```

`cmd_week`: replace the part after `by_ticket` is built with:

```python
    cfg = load_config()
    register, _ = load_register_for_run(cfg)
    banner = ""
    if register is not None:
        now, sessions = now_wib(), cab_sessions(cfg)
        if not register_fresh(register, now, sessions):
            banner = stale_banner(now, sessions)
    cab_lines = cab_week_lines(week, register, banner)
    if not by_ticket and not cab_lines:
        print(f"No entries for {week}.")
        return
    print(f"## Weekly report {week}\n")
    for ticket, rows in by_ticket.items():
        ...  # the existing per-ticket printing, unchanged
    if cab_lines:
        print("\n" + "\n".join(cab_lines))
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest; show diff; commit only on request (`✨ feat(claude): add the CAB this week block to the weekly summary`).

---

### Task 7: Config example, skill text, docs, mirror, verification, PR

**Files:**
- Modify: `CLAUDE/skills/logbook/config.example.json`, `CLAUDE/skills/logbook/SKILL.md`, `CLAUDE/commands/pipeline.md`, `CLAUDE/CLAUDE.md`, `docs/guidelines/DEV-WORKFLOW.md`
- Test: `tests/test_logbook.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_config_example_documents_the_cab_keys() -> None:
    cfg = json.loads((ROOT / "CLAUDE/skills/logbook/config.example.json").read_text())
    assert {
        "cab_register",
        "cab_sessions",
        "cab_max_lag_days",
        "cab_grace_days",
    } <= set(cfg)
    assert cfg["cab_sessions"] == {"days": ["Mon", "Wed"], "end": "15:00"}


def test_skill_text_describes_the_cab_register() -> None:
    text = (ROOT / "CLAUDE/skills/logbook/SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "## CAB register",
        "logbook.py cab",
        "cab_register",
        "Monday and Wednesday",
    ):
        assert needle in text
    assert "Last PAT Date" in text and "assumed done" in text
    assert "CAB register" in (ROOT / "CLAUDE/commands/pipeline.md").read_text(
        encoding="utf-8"
    )
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -q -k "config_example_documents or skill_text_describes"`
Expected: FAIL.

- [ ] **Step 3: Write the text**

`config.example.json`: add `"cab_register": "<path to the CAB register CSV; default: cab-register.csv in the Windows logbook folder>"`, `"cab_sessions": {"days": ["Mon", "Wed"], "end": "15:00"}`, `"cab_max_lag_days": 21`, `"cab_grace_days": 3` (keep the file valid JSON; `cab_register` as a placeholder string only).

`SKILL.md`: add a section `## CAB register` before `## Recheck`, with: what the file is (the Ops deployment task list, hand-filled copy, read-only); the update habit (the user updates it after each CAB session, Monday and Wednesday ending 15:00; a register older than the last session end is stale and its flags are hidden with a banner); `logbook.py cab [--ticket DA-n] [--show-unlinked]`; the status-to-stage table of spec section 4; PAT rules (`Last PAT Date` is the planned end; PAT is assumed done on that date unless an error signal exists: a `Rollback`, `CAB Ulang` or `Cancel` status, or a `Fixing` logbook row inside the window; the board proposes Done in one batch and Jira/logbook are written only after the user's OK); the flags ("not registered for CAB" after a grace period, "register ahead of Jira", "PAT done", "PAT window ended but ..."); the weekly "CAB this week" block; precedence (register owns dates, Jira owns status); configuration keys. No real names, links or ticket titles.

`pipeline.md`: add to step 3 that a `CAB register not updated since ...` banner means the register flags are hidden and the user should refresh the file after the last session; the "PAT done: propose Done" block is one batched proposal and each Jira transition still needs the user's OK.

`CLAUDE.md` (template): in the "Work Logbook" section add one bullet: the CAB register (`cab-register.csv` in the Windows logbook folder) is read by the helper; update it after each CAB session; `/logbook cab` shows it. `DEV-WORKFLOW.md`: add a short "CAB register" section with the status-to-stage table and the PAT rule. Use only the new status words.

- [ ] **Step 4: Run to verify, sweep, full verification**

Run:
`uv run pytest tests/test_logbook.py -q && uv run ruff format -q . && uv run ruff check . && uv run mypy . && uv run pytest -q`
`grep -rnE "\`In progress\`|\`PR to|\`Merged to|\`Released\`|Ready to Release" CLAUDE docs/guidelines | grep -v create-readme | grep -v logbook.py`
Expected: all green; the grep prints nothing.

- [ ] **Step 5: 3.9 and 3.12**

Run: `for v in 3.9 3.12; do uv run --no-project --python $v --with pytest python -m pytest tests/test_logbook.py -q -p no:cacheprovider 2>&1 | tail -1; done`
Expected: all pass on both.

- [ ] **Step 6: Checkpoint and PR**

Show `git status`; commit only on request (`📝 docs(claude): document the CAB register`). Open the PR to `dev` only when the user asks; the PR body ends with the Claude Code line. Propose a logbook row (`ticket` = `dev-workflow` or a new slug such as `cab-register`, `type` = `chore`; non-company work, so `Done` only after the merge to `master`).

---

### Task 8: Deploy to the live `~/.claude` (with the user)

Do this only after the PR is merged into `dev`. `~/.claude` is not a git repository, so the backup is the rollback.

- [ ] **Step 1: Back up**

```bash
stamp=$(date +%Y%m%d-%H%M%S); b=~/.claude/logbook/pre-cab-$stamp; mkdir -p "$b"
cp ~/.claude/skills/logbook/{logbook.py,SKILL.md} ~/.claude/logbook/config.json "$b"/
cp ~/.claude/CLAUDE.md ~/.claude/commands/pipeline.md "$b"/
ls "$b"
```

Expected: the five files are listed.

- [ ] **Step 2: Install**

```bash
cp CLAUDE/skills/logbook/logbook.py ~/.claude/skills/logbook/logbook.py
cp CLAUDE/commands/pipeline.md ~/.claude/commands/pipeline.md
diff <(git show HEAD~3:CLAUDE/skills/logbook/SKILL.md 2>/dev/null) ~/.claude/skills/logbook/SKILL.md | head
```

The live `SKILL.md` differs from the template by two example keys only; copy the template over it and restore those two lines the way the earlier deployment did (`--ticket DA-1876`, `rename <slug> DA-1234`). Apply the `CLAUDE.md` bullet from Task 7 to `~/.claude/CLAUDE.md` with the Edit tool (do not copy the template over it).

- [ ] **Step 3: First runs, checked by hand**

```bash
L="python3 $HOME/.claude/skills/logbook/logbook.py"
$L cab | head -40
$L cab --ticket <a ticket you know>
$L pipeline | head -60
$L check --since <last Monday>
$L week
```

Compare against the register and Jira by eye: stages, dates, the banner (the file's modification time against the last Monday or Wednesday 15:00), the PAT-done batch, and the "not registered" flags. Fix any mismatch in the helper with a new failing test first.

- [ ] **Step 4: Recovery (only if something is wrong)**

```bash
cp "$b"/logbook.py "$b"/SKILL.md ~/.claude/skills/logbook/ && cp "$b"/config.json ~/.claude/logbook/
cp "$b"/CLAUDE.md ~/.claude/CLAUDE.md && cp "$b"/pipeline.md ~/.claude/commands/pipeline.md
python3 ~/.claude/skills/logbook/logbook.py week
```

Expected: `week` runs again with the previous behavior.

---

## Self-Review

**Spec coverage**
- Section 2 (location, reading, headers, required/optional): Task 1. Section 3 (keys, current row, ambiguity, dates, mixed column, order check): Task 2. Section 4 (mapping, Cancel word) and 5 (precedence, PAT rules, error signals, staleness): Tasks 3 and 5. Section 6.0 interfaces: Tasks 1-6. 6.1: Task 4. 6.2: Task 5. 6.3: Task 6. 6.4: Task 5 (`cmd_check`). Section 7 config: Tasks 3 (`cab_sessions`, lag clamp), 5 (`cab_grace_days`), 7 (example). Section 8: Tasks 1, 6. Sections 9-10: tests in every task, Task 8.
- The uniqueness property, the +07:00 fixed offset, the future-date rule, `Closed Date` ignored, `NA` as confirmed, batched proposals and "Jira ahead" only in `cab`: covered by named tests.

**Placeholder scan:** no deferred code; every step has the test or implementation it needs.

**Type consistency:** `build_register` rows use the keys `n, status, pat_status, type, kategori, name, keys, reg, reg_note, cab, plan, real, pat_end`; `cab_info`, `cab_flags`, `cab_week_lines`, `register_quality` and `cmd_cab` read exactly those. `board_entry` keeps its earlier positional parameters and appends `cab, cab_fresh, not_registered`; `derive_board` and `render_board` only add defaulted parameters, so the existing tests keep working.

## Deviations recorded during execution

- `build_register` uses a module-level `_cell_date` instead of a nested helper (ruff B023).
- The batched "PAT done" block prints the entry's own `done_line` (the PAT flag), not `flags[0]`,
  because the repo-differs and Jira-versus-logbook flags can come first.
- `cab_decides` (the register decides about PAT) is true only when the current row's stage is
  `PAT` or `Done` and the register has a planned end or a confirmed `Status PAT`; otherwise the
  cached `pat_since` logic still runs.
- `cab_sessions` and the new `cab_grace_days` fall back to the defaults on malformed config.
- The "not registered for CAB" flag requires a `DA-` key (not any Jira-shaped key).
- `register_quality` also lists unknown statuses; Jira `Cancel` words (`CANCELLED`) are never aged.

