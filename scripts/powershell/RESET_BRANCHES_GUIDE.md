---
description: 'Branch Reset Utility - Usage Guide and Best Practices'
---

# 🔧 Branch Reset Utility - Usage Guide

**Location**: `scripts/powershell/reset-branches.ps1`

Enhanced version with safety features: user confirmation, backup tags, logging, and dry-run mode.

---

## 📋 Features

✅ **User Confirmation** - Prevents accidental execution
✅ **Backup Tags** - Creates recovery points before reset
✅ **Detailed Logging** - Full audit trail of operations
✅ **Dry-Run Mode** - Preview changes without executing
✅ **Flexible Execution** - Multiple parameter options

---

## 🚀 Usage Examples

### **1. Preview Before Executing (Safest)**

```powershell
# Preview what would happen - NO changes made
.\reset-branches.ps1 -DryRun

# Output shows exactly what would execute
# [DRY RUN] git checkout master
# [DRY RUN] git reset --hard origin/master
# etc.
```

### **2. Normal Execution (With Confirmation)**

```powershell
# Requires user to type 'yes' to confirm
.\reset-branches.ps1

# Output:
# ⚠️  WARNING: This script will FORCE RESET branches!
# Type 'yes' to continue (or press Enter to cancel)
```

### **3. Skip Confirmation (For Automation)**

```powershell
# Bypass confirmation with -Force
# Still creates backup tags
.\reset-branches.ps1 -Force
```

### **4. Skip Backup Creation**

```powershell
# Useful if backup storage is limited
# NOT recommended - reduces recovery options
.\reset-branches.ps1 -NoBackup
```

### **5. Dry-Run + Skip Backups (Safe Preview)**

```powershell
# Preview without creating backup tags
.\reset-branches.ps1 -DryRun -NoBackup
```

---

## 📊 Branch Reset Flow

```text
master (origin/master) ──┐
                         ├──> dev (reset to origin/master)
                         │
                         └──> sit (reset to origin/dev)
```

**What happens:**

1. `master` ← `origin/master` (force reset)
2. `dev` ← `origin/master` (force reset)
3. `sit` ← `origin/dev` (force reset)

---

## 📁 Output & Logs

Logs are automatically saved to:

```text
scripts/powershell/logs/reset-branches-YYYYMMDD-HHMMSS.log
```

Example log structure:

```text
═══════════════════════════════════════════════════════════
Branch Reset Utility
═══════════════════════════════════════════════════════════

Creating backup tags...
  ✅ Created tag: backup-master-20250124-143022
  ✅ Created tag: backup-dev-20250124-143022
  ✅ Created tag: backup-sit-20250124-143022
Pushing backup tags to origin...
  ✅ Backup tags pushed to origin

Updating master branch...
✅ Master branch reset to origin/master
Pushing master to origin...
✅ Master branch pushed to origin

✅ All branches have been reset successfully!

📋 Log saved to: C:\...\logs\reset-branches-20250124-143022.log
```

---

## 🔄 Recovery from Backup Tags

If something goes wrong, recovery is simple:

```powershell
# List backup tags
git tag -l "backup-*"

# Output:
# backup-master-20250124-143022
# backup-dev-20250124-143022
# backup-sit-20250124-143022

# Restore a specific branch from backup
git checkout master
git reset --hard backup-master-20250124-143022
git push origin master --force
```

---

## ⚠️ Parameters Reference

| Parameter | Default | Purpose |
| ----------- | --------- | --------- |
| `-DryRun` | `$false` | Preview changes without executing |
| `-NoBackup` | `$false` | Skip backup tag creation |
| `-Force` | `$false` | Skip user confirmation prompt |

### **Parameter Combinations**

| Command | Behavior |
| --------- | ---------- |
| `.\reset-branches.ps1` | Normal mode + confirmation + backups |
| `.\reset-branches.ps1 -DryRun` | Preview only, no changes |
| `.\reset-branches.ps1 -Force` | Skip confirmation but create backups |
| `.\reset-branches.ps1 -DryRun -NoBackup` | Safe preview without backups |
| `.\reset-branches.ps1 -Force -NoBackup` | Fastest execution, no backups |

---

## 🛡️ Safety Best Practices

### ✅ Recommended Workflow

1. **Always preview first:**

   ```powershell
   .\reset-branches.ps1 -DryRun
   ```

2. **Review the output carefully** - Ensure branches exist and operations look correct

3. **Execute with confirmation:**

   ```powershell
   .\reset-branches.ps1
   # Type 'yes' to confirm
   ```

4. **Verify backup tags were created:**

   ```powershell
   git tag -l "backup-*"
   ```

5. **Verify branches were reset:**

   ```powershell
   git log --oneline master -1
   git log --oneline dev -1
   git log --oneline sit -1
   ```

### ❌ Avoid These Practices

- ❌ Running without previewing first
- ❌ Using `-Force -NoBackup` together in production
- ❌ Ignoring warnings about uncommitted changes
- ❌ Not checking backup tags were created
- ❌ Running without reading the confirmation prompt

---

## 🐛 Troubleshooting

### **"Failed to checkout master branch"**

- Issue: Branch doesn't exist locally
- Solution: Create the branch or check branch name spelling

### **"Failed to push master branch"**

- Issue: Remote conflicts or permission issues
- Solution: Check remote access, verify branch exists on origin

### **"Backup tags already exist"**

- Issue: Tags from previous run exist
- Solution: This is normal - tags are date-stamped and won't conflict

### **"Uncommitted changes will be discarded"**

- Issue: Local changes not committed
- Solution: Commit or stash changes before running

---

## 📈 When to Use This Script

✅ **Perfect for:**

- Automated synchronization of integration branches
- Resetting staging environments (dev, sit)
- CI/CD pipeline integration
- Nightly branch synchronization
- Manual branch cleanup

❌ **Not recommended for:**

- User feature branches (use merge/rebase instead)
- Critical production branches without extensive testing
- Environments where history matters

---

## 🔗 Integration with CI/CD

### **GitHub Actions Example**

```yaml
- name: Reset Integration Branches
  run: |
    cd scripts/powershell
    .\reset-branches.ps1 -Force
  shell: pwsh
```

### **Scheduled Execution (Windows Task Scheduler)**

```powershell
# Action: Start a program
# Program: powershell.exe
# Arguments: -File "C:\path\to\reset-branches.ps1" -Force
# Schedule: Daily at 2:00 AM
```

---

## 📞 Support & Questions

For issues or questions:

1. Check logs in `scripts/powershell/logs/`
2. Run with `-DryRun` to preview
3. Review branch names match your setup
4. Verify origin remote is configured: `git remote -v`

---

**Last Updated**: January 24, 2025
**Script Version**: 2.0 (Enhanced with safety features)
