# Deployment and Release Guide

## Overview

This guide provides step-by-step procedures for deploying the cr-misc-function application across environments (development, staging, production) and managing release artifacts.

## Release Artifact Structure

Each release is self-contained in the `releases/` folder with all necessary deployment materials:

```text
releases/v1.0.0/
├── ddl/                    # Database DDL for all supported databases
├── migrations/             # Migration scripts from previous version
├── scripts/                # Deployment scripts specific to this release
├── config/                 # Configuration templates
├── RELEASE_NOTES.md        # What's new, breaking changes, bug fixes
├── DEPLOYMENT.md           # Step-by-step deployment instructions
├── CHECKSUMS.txt           # SHA256 checksums for integrity verification
└── README.md               # Quick reference for this release
```

## Pre-Deployment Checklist

Before deploying any release, verify:

- [ ] Release version is current and documented
- [ ] All DDL files tested on staging environment
- [ ] Application code tested on staging environment
- [ ] Database backups are current
- [ ] Deployment window is approved and communicated
- [ ] Rollback procedure is documented and tested
- [ ] Monitoring and alerting are configured
- [ ] Team is notified and prepared for deployment
- [ ] Emergency contacts are available
- [ ] Maintenance window is scheduled (if needed)

## Deployment Workflow

### Phase 1: Pre-Deployment Validation

```bash
# 1. Run pre-deployment checks
./scripts/deployment/pre-deploy-checks.sh production

# 2. Verify connectivity to all systems
ping database_server
curl -s https://api_endpoint/health

# 3. Create backup
./scripts/deployment/backup.sh production

# 4. Verify backup integrity
./scripts/deployment/verify-backup.sh latest_backup
```

### Phase 2: Database Deployment

```bash
# 1. Execute DDL files (if schema changes)
cd releases/v1.0.0/

# For PostgreSQL
psql -U app_user -d cr_misc_function -f ddl/postgres/schema_initial.sql
psql -U app_user -d cr_misc_function -f ddl/postgres/tables.sql
psql -U app_user -d cr_misc_function -f ddl/postgres/indexes.sql

# For MySQL
mysql -u app_user -p cr_misc_function < ddl/mysql/schema_initial.sql
mysql -u app_user -p cr_misc_function < ddl/mysql/tables.sql

# For MSSQL
sqlcmd -S server -U app_user -P password -d cr_misc_function -i ddl\mssql\schema_initial.sql
sqlcmd -S server -U app_user -P password -d cr_misc_function -i ddl\mssql\tables.sql

# 2. Execute migrations (if applicable)
for file in migrations/*.sql; do
  echo "Running migration: $file"
  psql -U app_user -d cr_misc_function -f "$file"
done

# 3. Verify database changes
psql -U app_user -d cr_misc_function -c "SELECT version();"
```

### Phase 3: Application Deployment

```bash
# 1. Deploy application code
cd /opt/cr-misc-function
git fetch origin
git checkout v1.0.0

# 2. Install/update dependencies
pip install -r requirements.txt

# 3. Run application tests
pytest tests/

# 4. Update configuration if needed
cp releases/v1.0.0/config/.env.production /opt/cr-misc-function/.env

# 5. Restart application service
systemctl restart cr-misc-function
systemctl status cr-misc-function
```

### Phase 4: Post-Deployment Validation

```bash
# 1. Run post-deployment checks
./scripts/deployment/post-deploy-validation.sh production

# 2. Verify application health
curl -s http://localhost:8000/health | jq .

# 3. Run smoke tests
./scripts/deployment/smoke-tests.sh

# 4. Monitor error logs
tail -f /var/log/cr-misc-function/application.log

# 5. Verify database connectivity
python -c "from app.configs.config import create_strategy; s = create_strategy('postgres'); print('Connection OK')"

# 6. Check metrics/monitoring
# Review dashboards in monitoring system (Prometheus, Grafana, etc.)
```

## Deployment by Environment

### Development Deployment

**Frequency**: Can be deployed multiple times daily

**Procedure**:

```bash
# 1. Deploy to development
cd /opt/cr-misc-function-dev
git pull origin develop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python -m alembic upgrade head

# 4. Restart service
systemctl restart cr-misc-function-dev

# 5. Run tests
pytest tests/
```

**Rollback**: If development breaks, reset to last stable commit

```bash
git reset --hard HEAD~1
systemctl restart cr-misc-function-dev
```

### Staging Deployment

**Frequency**: Once per feature/release cycle, typically weekly

**Procedure**:

```bash
# 1. Create release candidate branch
git checkout -b rc/v1.0.0

# 2. Execute deployment (same as production, but to staging)
./scripts/deployment/deploy.sh v1.0.0 staging

# 3. Comprehensive testing
pytest tests/ --verbose
./scripts/deployment/integration-tests.sh staging
./scripts/deployment/performance-tests.sh staging

# 4. Get sign-off before production
# Review test results, obtain approval from team lead/QA manager

# 5. Tag release when approved
git tag v1.0.0
git push origin v1.0.0
```

### Production Deployment

**Frequency**: Controlled release schedule, typically monthly

**Prerequisites**:

- All tests pass on staging
- Release notes reviewed and approved
- Stakeholders notified
- Maintenance window scheduled

**Procedure**:

```bash
# 1. Start deployment maintenance window
echo "Maintenance: Application update in progress" > /var/www/maintenance.html

# 2. Full deployment process
./scripts/deployment/deploy.sh v1.0.0 production

# 3. Extensive post-deployment validation
./scripts/deployment/post-deploy-validation.sh production
./scripts/deployment/smoke-tests.sh production
./scripts/deployment/health-check.sh production

# 4. Monitor closely for 1 hour post-deployment
# Set extra alerting, have team on standby

# 5. Retire maintenance page
rm /var/www/maintenance.html

# 6. Post-deployment communication
# Send deployment completion notice to stakeholders
```

## Rollback Procedures

### Quick Rollback (Emergency)

Use when critical issues are discovered immediately post-deployment:

```bash
# 1. Execute rollback script
./scripts/deployment/rollback.sh v1.0.0

# 2. Verify rollback success
systemctl status cr-misc-function
curl -s http://localhost:8000/health | jq .

# 3. Notify team
# Send incident notification and begin root cause analysis
```

### Full Rollback (Database Changes)

If database schema changes need to be reverted:

```bash
# 1. Restore from backup
./scripts/deployment/restore-backup.sh latest_backup

# 2. Verify database integrity
psql -U app_user -d cr_misc_function -f verify_schema.sql

# 3. Redeploy previous application version
git checkout v0.9.0
pip install -r requirements.txt
systemctl restart cr-misc-function

# 4. Extensive post-deployment validation
./scripts/deployment/post-deploy-validation.sh production
```

## Release Artifact Management

### Creating a Release

```bash
# 1. Prepare release folder
mkdir releases/v1.1.0
cd releases/v1.1.0

# 2. Copy DDL files
cp -r ../../db/ddl ./

# 3. Copy migration scripts
cp -r ../../db/migrations/v1.1 ./migrations

# 4. Copy deployment scripts
cp ../../scripts/deployment/deploy.sh ./
cp ../../scripts/deployment/rollback.sh ./

# 5. Create release documentation
cat > RELEASE_NOTES.md << 'EOF'
# Release v1.1.0

## Date: $(date +%Y-%m-%d)

## Features
- Feature 1: Description
- Feature 2: Description

## Bug Fixes
- Bug 1: Fixed issue
- Bug 2: Fixed issue

## Database Changes
- Table X: Added column Y
- Table Z: Dropped column W

## Upgrade Instructions
1. Run DDL from ddl/ folder
2. Run migrations from migrations/ folder
3. Restart application

## Known Issues
- Known issue 1: Workaround
EOF

# 6. Generate checksums
sha256sum $(find . -type f) > CHECKSUMS.txt

# 7. Commit and tag
git add .
git commit -m "🎉 Release v1.1.0"
git tag v1.1.0
git push origin v1.1.0
```

### Validating Release Artifacts

```bash
# 1. Verify checksums
cd releases/v1.1.0
sha256sum -c CHECKSUMS.txt

# 2. Verify file permissions (scripts should be executable)
ls -la deploy.sh rollback.sh

# 3. Verify DDL syntax (for PostgreSQL)
pg_dump --no-password -d cr_misc_function --schema-only -f verify_schema.sql

# 4. Validate documentation
test -f RELEASE_NOTES.md && test -f DEPLOYMENT.md && echo "Documentation OK"
```

## Monitoring and Observability

### Key Metrics to Monitor

- **Application Response Time**: Alert if > 1000ms (configurable)
- **Error Rate**: Alert if > 1% of requests
- **Database Connection Pool**: Alert if > 80% utilization
- **Disk Space**: Alert if < 20% remaining
- **Memory Usage**: Alert if > 85% utilization
- **CPU Usage**: Alert if > 80% sustained

### Alerting Setup

Create alerting rules in your monitoring system:

```yaml
# Example Prometheus alert rules
groups:
  - name: cr-misc-function
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 1
        for: 5m
        annotations:
          summary: "Response time above threshold"
```

## Disaster Recovery

### Backup and Restore

**Regular Backups**:

```bash
# Daily backup (scheduled via cron)
0 2 * * * /opt/cr-misc-function/scripts/deployment/backup.sh production

# Verify backup integrity weekly
0 3 * * 0 /opt/cr-misc-function/scripts/deployment/verify-backup.sh latest_backup
```

**Restore Procedure**:

```bash
# 1. Stop application
systemctl stop cr-misc-function

# 2. Restore from backup
./scripts/deployment/restore-backup.sh backup_file.sql.gz

# 3. Verify database integrity
psql -U app_user -d cr_misc_function -c "SELECT COUNT(*) FROM information_schema.tables;"

# 4. Restart application
systemctl start cr-misc-function

# 5. Monitor for issues
tail -f /var/log/cr-misc-function/application.log
```

## Troubleshooting Deployments

### Issue: DDL Execution Fails

**Cause**: Syntax error or object already exists

**Solution**:

1. Review DDL file for errors
2. Check if objects already exist: `SELECT * FROM information_schema.tables;`
3. If re-deploying, drop and recreate, or use `CREATE IF NOT EXISTS`

### Issue: Application Won't Start

**Cause**: Configuration error, missing dependencies, or port in use

**Solution**:

```bash
# Check logs
tail -f /var/log/cr-misc-function/application.log

# Verify configuration
cat /opt/cr-misc-function/.env | grep DATABASE

# Check port availability
netstat -tulpn | grep 8000

# Verify dependencies
pip list | grep -E "sqlalchemy|psycopg2|pyodbc"
```

### Issue: Database Connection Fails

**Cause**: Wrong connection string, network issue, or wrong credentials

**Solution**:

```bash
# Test connection directly
psql -U app_user -h localhost -d cr_misc_function -c "SELECT 1;"

# Check firewall rules
iptables -L -n | grep 5432

# Verify credentials in .env file
grep DATABASE /opt/cr-misc-function/.env
```

## Post-Deployment Communication

### Sample Deployment Notification

```text
Subject: ✅ Production Deployment - v1.1.0 Completed Successfully

Team,

Release v1.1.0 has been successfully deployed to production on December 11, 2025 at 14:30 UTC.

## What's New
- Feature A: Improved database connection pooling
- Feature B: Added support for Trino data source
- Fix: Resolved issue with ODPS connections timing out

## Deployment Details
- Duration: 15 minutes
- Downtime: None (rolling update)
- Tests: All passed (152/152 passed)

## Monitoring
- Error rate: 0.01% (normal)
- Response time: 95th percentile at 240ms (normal)
- All alerts green

No issues detected. Normal operation confirmed.

## Next Steps
If you experience any issues, please contact: ops-team@example.com

Thank you,
Deployment Automation System
```

## References

- [Deployment Best Practices](https://12factor.net/)
- [Database Migration Tools](https://flywaydb.org/)
- [Blue-Green Deployments](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Monitoring and Observability](https://prometheus.io/)
