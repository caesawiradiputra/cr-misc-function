# Create README

Create or update the project's `README.md` following project documentation standards.

## Target: $ARGUMENTS

If `$ARGUMENTS` specifies a project or focus area, apply that context. Otherwise, analyze the current project.

---

## Before Starting

1. **Check if README.md exists** in the project root:

   ```powershell
   Test-Path "README.md"
   Get-Content "README.md"
   ```

   - If exists → review and update (preserve relevant sections, add new ones for new features)
   - If not → create from scratch

2. **Analyze project structure**:

   ```powershell
   Get-ChildItem -Recurse -Filter "*.py" | Select-Object -First 20
   Get-Content "pyproject.toml"
   ```

---

## Organization Rules

### Single Source of Truth

- The **only** README.md lives in the **project root**
- Never create README.md files in subdirectories
- Move all other `.md` files to `docs/` folder structure

### docs/ Folder Structure

```text
docs/
├── guides/       - Usage guides and tutorials
├── architecture/ - Architecture and design docs
├── changelog/    - Release notes and version history
├── examples/     - Code examples and demonstrations
└── api/          - API reference (if applicable)
```

---

## README Content Structure

Include these sections in order:

1. **Title and Description** — Clear project name + one-sentence description
2. **Features** — Key capabilities as bullet list (3-7 items)
3. **Quick Start** — Installation and basic usage with code examples
4. **Requirements** — System requirements and dependencies
5. **Installation** — Detailed steps (if needed beyond quick start)
6. **Usage** — Usage examples and common scenarios
7. **Configuration** — Options and environment variables (if applicable)
8. **Architecture** — High-level overview (link to `docs/architecture/` for details)
9. **Contributing** — Link to `CONTRIBUTING.md` if it exists
10. **Further Reading** — Links to `docs/` folder
11. **License** — License info with link to `LICENSE` file

### Further Reading Section Example

```markdown
## Further Reading

- [Architecture Guide](docs/architecture/README.md) - System design and patterns
- [Usage Guide](docs/guides/README.md) - Comprehensive usage instructions
- [Examples](docs/examples/README.md) - Code examples
- [Changelog](docs/changelog/CHANGELOG.md) - Version history
```

---

## Markdown Standards

### Code Blocks — Always Specify Language

```markdown
```python
def example(): ...
```

```powershell
uv sync
```

```sql
SELECT * FROM orders;
```

```text

Never use bare ` ``` ` without a language identifier.

### Blank Lines

Add blank lines before and after: code blocks, lists, blockquotes, headings.

### Heading Hierarchy

- `#` H1 (title only — one per file)
- `##` H2 (major sections)
- `###` H3 (subsections)
- Do not skip levels (no H1 directly to H3)

### Lists

- Consistent markers: `-` for unordered, `1.` for ordered
- Blank line before first item and after last item when following text
- Indent nested lists with 2 spaces

### Links

- Use inline links: `[text](url)`
- Relative links use forward slashes: `docs/architecture/README.md`
- Descriptive link text (not "click here")

### Line Length

Keep lines under 120 characters for readability.

### Tables

```markdown
| Feature | Status | Description |
| --- | --- | --- |
| Feature A | ✅ | Fully implemented |
| Feature B | 🔄 | In progress |
```

---

## Quality Checklist

Before finishing:

- [ ] Only one README.md exists (in root directory)
- [ ] All code blocks have language identifiers
- [ ] Blank lines surround code blocks, lists, and headings
- [ ] Headings follow hierarchy (no skipped levels)
- [ ] All links are valid and use forward slashes
- [ ] Lines are under 120 characters
- [ ] Tables properly aligned with header separators
- [ ] Documentation links point to `docs/` subfolder
- [ ] Content is current and accurate for project state
- [ ] Passes markdown linting (no formatting errors)
