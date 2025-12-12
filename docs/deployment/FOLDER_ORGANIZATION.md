# Database and Deployment Folder Organization

## Overview

This document describes the recommended folder structure for database-related materials (DDL, migrations, seeds), deployment scripts, configuration files, and release artifacts. This organization keeps platform-specific code separate from application code while maintaining clarity and reproducibility.

## Folder Structure

```text
project-root/
├── scripts/
│   ├── powershell/          # PowerShell utilities
│   ├── sql/                 # SQL scripts
│   ├── python/              # Python utility scripts
│   └── deployment/          # Deployment/release scripts
│
├── db/                      # Database-related materials
│   ├── ddl/                 # Data Definition Language (schemas, tables)
│   │   ├── mssql/           # SQL Server DDL
│   │   ├── postgres/        # PostgreSQL DDL
│   │   ├── mysql/           # MySQL DDL
│   │   ├── hive/            # Hive DDL
│   │   ├── odps/            # Alibaba ODPS DDL
│   │   └── trino/           # Trino DDL
│   │
│   ├── seeds/               # Seed/test data
│   │   ├── development/
│   │   ├── staging/
│   │   └── production/
│   │
│   ├── migrations/          # Database migrations
│   │   ├── v1.0/
│   │   └── v1.1/
│   │
│   └── backups/             # Database backup scripts/configs
│
├── config/
│   ├── cron/                # Cron job configurations
│   ├── deployment/          # Deployment configurations
│   └── environment/         # Environment-specific configs
│
├── releases/                # Release artifacts
│   ├── v1.0.0/
│   │   ├── ddl/
│   │   ├── scripts/
│   │   ├── migrations/
│   │   └── RELEASE_NOTES.md
│   └── v1.1.0/
│       ├── ddl/
│       └── scripts/
│
└── docs/                    # Documentation
    ├── deployment/
    ├── database/
    └── configuration/
```

## Folder Descriptions

### `scripts/sql/` - SQL Scripts

**Purpose**: Reusable SQL scripts for queries, maintenance, and data operations

**Structure**:

```text
scripts/sql/
├── maintenance/          # Index rebuild, statistics update, cleanup
├── reporting/            # Common report queries
├── admin/                # User management, permissions
└── data-operations/      # Bulk operations, imports, exports
```

**File Naming Convention**: `{entity}_{action}.sql`

- Examples:
  - `users_table_maintenance.sql`
  - `orders_report_monthly.sql`
  - `audit_permissions_setup.sql`
  - `staging_import_data.sql`

**Usage**:

- Include SQL scripts for common database maintenance tasks
- Store reusable report queries
- Document administrative procedures (user management, permissions)
- Archive bulk data operation scripts for reference

---

### `db/ddl/` - Data Definition Language

**Purpose**: Create and modify database objects (schemas, tables, indexes, constraints, views, stored procedures)

**Organization**: By database type to support multi-database deployment

```text
db/ddl/
├── mssql/
│   ├── schema_initial.sql
│   ├── tables.sql
│   ├── indexes.sql
│   ├── stored_procedures.sql
│   └── views.sql
├── postgres/
│   ├── schema_initial.sql
│   ├── tables.sql
│   ├── indexes.sql
│   └── functions.sql
├── mysql/
│   ├── schema_initial.sql
│   ├── tables.sql
│   └── indexes.sql
├── hive/
│   ├── tables.sql
│   └── partitions.sql
├── odps/
│   ├── schema_initial.sql
│   └── tables.sql
└── trino/
    └── views.sql
```

**File Naming Convention**: `{entity}_{action}.sql`

- Examples:
  - `users_table_create.sql`
  - `orders_index_create.sql`
  - `audit_trigger_create.sql`
  - `reports_view_create.sql`

**Best Practices**:

- Include version comments in files for tracking schema changes
- Add `-- Version: 1.0` at the top of each file
- Include timestamps: `-- Created: 2025-12-11`
- Add database-specific notes if needed
- Keep DDL idempotent where possible (use `CREATE OR REPLACE`, `IF NOT EXISTS`, etc.)

**Example File**:

```sql
-- Schema initialization for PostgreSQL
-- Version: 1.0
-- Created: 2025-12-11
-- Database: PostgreSQL 14+

CREATE SCHEMA IF NOT EXISTS app_schema;

CREATE TABLE IF NOT EXISTS app_schema.users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON app_schema.users(email);
```

---

### `db/seeds/` - Seed and Reference Data

**Purpose**: Test data, reference data, and lookup tables for different environments

**Organization**: By environment

```
db/seeds/
├── development/
│   ├── users_seed.sql
│   ├── roles_seed.sql
│   └── permissions_seed.sql
├── staging/
│   ├── users_seed.sql
│   └── reference_data_seed.sql
└── production/
    └── reference_data_seed.csv
```

**File Formats**:

- `.sql` - Insert statements for database-specific formats
- `.csv` - Portable format for bulk imports
- `.json` - Structured data for complex seed data

**Best Practices**:

- Keep seed data separate by environment
- Use non-sensitive test data in development/staging
- Never include production data in version control
- Document data sources and refresh procedures
- Make seed operations idempotent (use `UPSERT` or `ON CONFLICT`)

**Example Seed File**:

```sql
-- roles_seed.sql for development environment
-- Seed reference data for user roles

INSERT INTO roles (role_id, role_name, description) VALUES
(1, 'admin', 'Administrator with full access'),
(2, 'manager', 'Manager with team oversight'),
(3, 'user', 'Standard user with read/write access')
ON CONFLICT (role_id) DO NOTHING;
```

---

### `db/migrations/` - Schema Versioning

**Purpose**: Track incremental schema changes with version history

**Organization**: By version

```
db/migrations/
├── v1.0/
│   ├── 001_initial_schema.sql
│   ├── 002_add_user_roles.sql
│   └── 003_create_indexes.sql
├── v1.1/
│   ├── 004_add_audit_tables.sql
│   └── 005_alter_users_table.sql
└── v2.0/
    ├── 006_redesign_schema.sql
    └── 007_migrate_data.sql
```

**File Naming Convention**: `{sequence}_{description}.sql`

- Sequence: Zero-padded number (001, 002, 003...)
- Description: Lowercase with underscores (add_user_roles, migrate_data)
- Examples:
  - `001_initial_schema.sql`
  - `002_add_audit_tables.sql`
  - `003_alter_users_table.sql`

**Best Practices**:

- One change per file (single responsibility)
- Make migrations reversible (include rollback logic or separate rollback files)
- Include data migration if schema changes require it
- Test migrations on staging before production
- Document breaking changes clearly in file header

**Example Migration File**:

```sql
-- Migration: 002_add_audit_tables.sql
-- Version: v1.1
-- Created: 2025-12-11
-- Description: Add audit tables for tracking data changes
-- Rollback: DROP TABLE IF EXISTS audit_log; DROP TRIGGER IF EXISTS audit_trigger ON users;

CREATE TABLE audit_log (
    audit_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_table ON audit_log(table_name);
```

---

### `db/backups/` - Backup Configuration and Scripts

**Purpose**: Backup strategy documentation and automated backup procedures

**Contents**:

```
db/backups/
├── backup_strategy.md          # Overall backup plan
├── backup_schedule.sh          # Linux/Mac backup automation
├── backup_schedule.ps1         # Windows backup automation
├── restore_procedure.md        # Step-by-step restoration guide
└── backup_retention.config     # Backup retention policy
```

**Files**:

- `backup_strategy.md` - Backup plan, frequency, retention policy
- `backup_schedule.sh` - Cron-based backup automation for Unix systems
- `backup_schedule.ps1` - PowerShell scheduled backup for Windows
- `restore_procedure.md` - How to restore from backup, disaster recovery
- `backup_retention.config` - Archive strategy and cleanup rules

**Documentation Example** (backup_strategy.md):

```markdown
# Backup Strategy

## Schedule
- Development: Daily, kept for 7 days
- Staging: Daily, kept for 30 days
- Production: Twice daily (morning, evening), kept for 90 days

## Retention Policy
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

## Storage
- Local backup: `/backups/` on database server
- Offsite backup: S3 bucket `company-db-backups`
- Encryption: AES-256

## Testing
- Monthly restore test to verify backup integrity
- Alternate restoration site for disaster recovery
```

---

### `scripts/deployment/` - Deployment Automation

**Purpose**: Automate release and deployment procedures

**Contents**:

```
scripts/deployment/
├── deploy.sh                   # Main deployment script (Unix)
├── deploy.ps1                  # Main deployment script (Windows)
├── pre-deploy-checks.sh        # Health checks before deployment
├── post-deploy-validation.sh   # Post-deployment verification
├── rollback.sh                 # Rollback procedure
└── deployment-checklist.md     # Manual verification steps
```

**File Examples**:

**deploy.sh**:

```bash
#!/bin/bash
# Deployment script for Unix systems
# Usage: ./deploy.sh v1.0.0 production

VERSION=$1
ENVIRONMENT=$2

echo "Deploying version $VERSION to $ENVIRONMENT..."

# Run pre-deployment checks
./pre-deploy-checks.sh $ENVIRONMENT

# Execute database migrations
psql -f db/migrations/v${VERSION}/001_*.sql

# Restart application services
systemctl restart app-service

# Run post-deployment validation
./post-deploy-validation.sh $ENVIRONMENT

echo "Deployment of $VERSION to $ENVIRONMENT completed!"
```

**deployment-checklist.md**:

```markdown
# Deployment Checklist

- [ ] Database backups completed
- [ ] Pre-deployment health checks passed
- [ ] All migrations have been tested on staging
- [ ] Application code tested in staging environment
- [ ] Deployment window approved and communicated
- [ ] Rollback procedure verified and available
- [ ] Monitoring and alerting configured
- [ ] Post-deployment validation passed
```

---

### `config/cron/` - Cron Job Configurations

**Purpose**: Define scheduled database and application maintenance tasks

**Contents**:

```
config/cron/
├── crontab.txt                 # Cron schedule definitions
├── cron_jobs.yaml              # Structured job definitions
├── scheduled_tasks.json        # Windows task scheduler exports
└── maintenance_procedures.md   # Documentation of each job
```

**File Examples**:

**crontab.txt**:

```cron
# Cron job schedule for cr-misc-function
# Minutes | Hour | Day of Month | Month | Day of Week | Command

# Data synchronization every 6 hours
0 */6 * * * /usr/local/bin/sync_data.py >> /var/log/sync_data.log 2>&1

# Daily cleanup at 2 AM
0 2 * * * /usr/local/bin/cleanup.sh >> /var/log/cleanup.log 2>&1

# Weekly backup every Sunday at midnight
0 0 * * 0 /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# Monthly statistics collection on first day at 3 AM
0 3 1 * * /usr/local/bin/collect_stats.py >> /var/log/stats.log 2>&1
```

**cron_jobs.yaml**:

```yaml
jobs:
  - name: "sync_data"
    schedule: "0 */6 * * *"
    command: "/usr/local/bin/sync_data.py"
    description: "Synchronize data across databases every 6 hours"
    notifications: "notify-on-failure"
    
  - name: "cleanup"
    schedule: "0 2 * * *"
    command: "/usr/local/bin/cleanup.sh"
    description: "Daily cleanup of temporary data"
    notifications: "none"
```

---

### `config/environment/` - Environment-Specific Configuration

**Purpose**: Store environment-specific settings for different deployment environments

**Contents**:

```
config/environment/
├── development.env             # Development environment
├── staging.env                 # Staging/QA environment
├── production.env              # Production environment
├── connection-strings.yaml     # Database connection templates
└── .env.template               # Template for team reference
```

**Best Practices**:

- Use `.env.template` as a reference for required variables
- Never commit actual `.env` files with secrets
- Use separate files per environment
- Document all available variables

**Example .env.template**:

```env
# Database Configuration
DATABASE_MSSQL_HOST=localhost
DATABASE_MSSQL_PORT=1433
DATABASE_MSSQL_USER=sa
DATABASE_MSSQL_PASSWORD=your_password_here
DATABASE_MSSQL_DATABASE=app_db

DATABASE_POSTGRES_HOST=localhost
DATABASE_POSTGRES_PORT=5432
DATABASE_POSTGRES_USER=postgres
DATABASE_POSTGRES_PASSWORD=your_password_here
DATABASE_POSTGRES_DATABASE=app_db

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG_MODE=true
```

---

### `releases/` - Release Artifacts

**Purpose**: Self-contained release packages with all necessary deployment materials

**Structure**: Each version gets its own folder

```
releases/
├── v1.0.0/
│   ├── ddl/
│   │   ├── mssql/
│   │   ├── postgres/
│   │   └── mysql/
│   ├── migrations/
│   ├── scripts/
│   ├── config/
│   ├── RELEASE_NOTES.md
│   ├── DEPLOYMENT.md
│   ├── CHECKSUMS.txt
│   └── README.md
└── v1.1.0/
    ├── ddl/
    ├── migrations/
    ├── RELEASE_NOTES.md
    └── DEPLOYMENT.md
```

**Release Package Contents**:

**RELEASE_NOTES.md**:

```markdown
# Release v1.0.0 - Initial Release

## Release Date
December 11, 2025

## Features
- Multi-database connection abstraction
- Support for MSSQL, PostgreSQL, MySQL, Hive, Trino, ODPS
- Connection pooling and configuration management

## Breaking Changes
None - initial release

## Database Changes
- New schema created with initial DDL
- 5 core tables: connections, queries, logs, config, audit

## Upgrade Instructions
1. Deploy new application code
2. Run DDL from `ddl/` folder for your database type
3. Run seed data from `seeds/production/`
4. Run post-deployment validation
```

**DEPLOYMENT.md**:

```markdown
# Deployment Instructions for v1.0.0

## Prerequisites
- Python 3.11+
- Database access for DDL execution
- Backup of existing database (if applicable)

## Step-by-Step Deployment

1. **Pre-Deployment Checks**
   ```bash
   ./pre-deploy-checks.sh production
   ```

2. **Database Preparation**

   ```bash
   psql -f releases/v1.0.0/ddl/postgres/schema_initial.sql
   psql -f releases/v1.0.0/ddl/postgres/tables.sql
   psql -f releases/v1.0.0/seeds/production/reference_data_seed.sql
   ```

3. **Application Deployment**

   ```bash
   pip install -r requirements.txt
   systemctl restart app-service
   ```

4. **Post-Deployment Validation**

   ```bash
   ./post-deploy-validation.sh production
   ```

## Rollback

If deployment fails, run:

```bash
./rollback.sh v1.0.0
```

```

**CHECKSUMS.txt**:
```

SHA256 Checksums for Release v1.0.0

ddl/mssql/schema_initial.sql: a1b2c3d4e5f6...
ddl/mssql/tables.sql: f6e5d4c3b2a1...
ddl/postgres/schema_initial.sql: 1a2b3c4d5e6f...
seeds/production/reference_data_seed.sql: 6f5e4d3c2b1a...

```

---

## Git Management

### .gitignore Configuration

Add these patterns to `.gitignore`:
```gitignore
# Database backups (too large, sensitive)
db/backups/*.bak
db/backups/*.sql.gz
db/backups/*.dump
db/backups/*.backup

# Generated migration files
db/migrations/**/*.generated.sql

# Environment-specific configs with secrets
config/environment/*.local.env
config/environment/*.secrets.*
config/environment/production.env
config/environment/*.secrets.yaml

# Temporary script outputs
scripts/**/*.log
scripts/**/*.tmp
scripts/**/*.out

# OS-specific files
.DS_Store
Thumbs.db
```

### Commit Strategy

**What TO Commit**:

- ✅ DDL files (schema definitions)
- ✅ Migration scripts (versioned)
- ✅ Seed data templates (non-sensitive data only)
- ✅ Script templates
- ✅ Configuration templates (`.template`, `.example`)
- ✅ Release notes and documentation
- ✅ Deployment procedures
- ✅ Cron job definitions

**What NOT to Commit**:

- ❌ Actual backups (`.bak`, `.dump` files)
- ❌ Environment-specific secrets
- ❌ Production database dumps
- ❌ Generated logs or temporary files
- ❌ Production `.env` files
- ❌ Sensitive reference data

---

## Usage Examples

### Deploying a New Version

```bash
# 1. Create release folder
mkdir releases/v1.1.0
cp -r db/ddl releases/v1.1.0/

# 2. Generate migration scripts
cp db/migrations/v1.1/ releases/v1.1.0/migrations/

# 3. Copy deployment scripts
cp scripts/deployment/deploy.sh releases/v1.1.0/

# 4. Create release notes
# Edit releases/v1.1.0/RELEASE_NOTES.md

# 5. Generate checksums
sha256sum releases/v1.1.0/**/* > releases/v1.1.0/CHECKSUMS.txt

# 6. Commit release
git add releases/v1.1.0/
git commit -m "🎉 Release v1.1.0"
git tag v1.1.0
```

### Running Database Migrations

```bash
# For specific database type
psql -f db/migrations/v1.1/001_*.sql

# For all migrations in version
for file in db/migrations/v1.1/*.sql; do
  mysql -u root -p < "$file"
done
```

### Setting Up Cron Jobs

```bash
# Load cron jobs from configuration
crontab config/cron/crontab.txt

# Verify jobs are scheduled
crontab -l
```

---

## References

- [Keep a Changelog](https://keepachangelog.com/) - Changelog format
- [Flyway Database Migrations](https://flywaydb.org/) - Migration tools
- [Liquibase Schema Versioning](https://www.liquibase.org/) - Alternative migration tool
- Database-specific documentation for DDL syntax
