# 📦 DDL File Naming Convention

## 🔍 Current Issue

There is inconsistency in how DDL files are named:

- `DA-1421/ddl/Obligor_Exposure_Realtime.sql` → only object name
- `DA-1495/ddl/CREATE-TABLE-Obligor_Detail.sql` → mixed format (operation + type + name)

👉 This makes deployment order, intent, and consistency harder to maintain.

---

## ✅ Recommended Convention

### **Format**

```text
{sequence}{operation}{object_type}_{object_name}.sql
```

### **Example Structure**

```text
release/DA-1495/ddl/
├── 001_create_table_obligor_detail.sql
├── 002_create_index_obligor_detail_idx_obligorid.sql
├── 003_add_constraint_obligor_detail_fk_customer.sql
└── README.md # (optional: deployment notes)
```

---

## 🧩 Naming Components

| Component | Description | Example |
| ----------------- | ----------------- | ----------------- |
| `sequence` | Execution order (zero-padded) | `001`, `002` |
| `operation` | Action performed | `create`, `alter`, `add`, `drop` |
| `object_type` | Type of database object | `table`, `index`, `view`, `constraint` |
| `object_name` | Target object (clear and descriptive) | `obligor_detail` |

---

## 📌 Guidelines

### ✅ Do

- Use **lowercase snake_case** consistently
- Include **operation** and **object type** for clarity
- Use **sequential numbering** for ordered execution
- Keep names **descriptive and explicit**
- Ensure filenames reflect **actual intent of the script**

### ✅ Example Naming

```text
001_create_table_obligor_detail.sql
002_create_index_obligor_detail_idx_obligorid.sql
003_add_column_obligor_detail_asset_value.sql
004_create_view_obligor_exposure_summary.sql
005_grant_permissions_obligor_tables.sql
```

---

### ❌ Avoid

- Mixed casing or formats

```text
CREATE-TABLE-Obligor_Detail.sql
```

- Missing operation/type

```text
obligor_detail.sql
```

- Generic or unclear names

```text
update1.sql
fix.sql
script_final.sql
```

---

## 🔄 Migration Example

```text
OLD: CREATE-TABLE-Obligor_Detail.sql
NEW: 001_create_table_obligor_detail.sql
```

### Benefits

- ✔ Clear execution order
- ✔ Self-documenting filenames
- ✔ Easier deployment automation
- ✔ Consistent across all tickets/releases

---

## 💡 Optional: README per Ticket

Each `ddl/` folder may include:

```text
README.md
```

Suggested contents:

- Deployment order (if non-linear)
- Special instructions
- Rollback notes
- Dependencies between scripts

---

## 🚀 Summary

Adopting this convention ensures:

- Consistency across all releases
- Better readability and maintainability
- Safer and more predictable deployments
