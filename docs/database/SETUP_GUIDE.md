# Database Setup Guide

## Overview

This guide covers setting up databases for the cr-misc-function application using the DDL files organized in the `db/ddl/` folder. The application supports multiple database types: MSSQL, PostgreSQL, MySQL, Hive, Trino, and Alibaba ODPS.

## Quick Start

### 1. Choose Your Database Type

The application can work with any supported database. Select one or more based on your needs:

| Database | Location | Use Case |
| --- | --- | --- |
| MSSQL | `db/ddl/mssql/` | Enterprise environments, Windows servers |
| PostgreSQL | `db/ddl/postgres/` | Open-source, high performance, recommended for Linux |
| MySQL | `db/ddl/mysql/` | Web applications, cloud platforms |
| Hive | `db/ddl/hive/` | Big data analytics, Hadoop ecosystem |
| Trino | `db/ddl/trino/` | Distributed SQL queries across data sources |
| ODPS | `db/ddl/odps/` | Alibaba MaxCompute for cloud analytics |

### 2. Extract Relevant DDL

Copy DDL files for your chosen database type:

```bash
# For PostgreSQL
cp -r db/ddl/postgres/* /tmp/setup/

# For MSSQL
cp -r db/ddl/mssql/* /tmp/setup/

# For multiple databases
for db in postgres mysql; do
  cp -r db/ddl/$db/* /tmp/setup/
done
```

### 3. Execute DDL in Order

Most DDL files should be executed in this order:

1. `schema_initial.sql` - Create schemas/databases
2. `tables.sql` - Create tables and constraints
3. `indexes.sql` - Create indexes
4. `views.sql` - Create views (if applicable)
5. `stored_procedures.sql` or `functions.sql` - Create procedures/functions

---

## Database-Specific Setup

### PostgreSQL Setup

**Prerequisites**:

- PostgreSQL 12+ installed
- `psql` command-line client available

**Setup Steps**:

```bash
# 1. Connect to PostgreSQL as admin
psql -U postgres

# 2. Create application database
CREATE DATABASE cr_misc_function;
CREATE USER app_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE cr_misc_function TO app_user;

# 3. Exit psql
\q

# 4. Execute DDL files
psql -U app_user -d cr_misc_function -f db/ddl/postgres/schema_initial.sql
psql -U app_user -d cr_misc_function -f db/ddl/postgres/tables.sql
psql -U app_user -d cr_misc_function -f db/ddl/postgres/indexes.sql

# 5. Load seed data (optional)
psql -U app_user -d cr_misc_function -f db/seeds/development/reference_data_seed.sql
```

**Connection String for Application**:

```text
postgresql://app_user:your_secure_password@localhost:5432/cr_misc_function
```

### MySQL Setup

**Prerequisites**:

- MySQL 8.0+ or MariaDB 10.3+ installed
- `mysql` command-line client available

**Setup Steps**:

```bash
# 1. Connect to MySQL as root
mysql -u root -p

# 2. Create database and user
CREATE DATABASE cr_misc_function;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON cr_misc_function.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;

# 3. Exit MySQL
EXIT;

# 4. Execute DDL files
mysql -u app_user -p cr_misc_function < db/ddl/mysql/schema_initial.sql
mysql -u app_user -p cr_misc_function < db/ddl/mysql/tables.sql
mysql -u app_user -p cr_misc_function < db/ddl/mysql/indexes.sql

# 5. Load seed data (optional)
mysql -u app_user -p cr_misc_function < db/seeds/development/reference_data_seed.sql
```

**Connection String for Application**:

```text
mysql+pymysql://app_user:your_secure_password@localhost:3306/cr_misc_function
```

### MSSQL Setup

**Prerequisites**:

- SQL Server 2019+ installed
- SQL Server Management Studio (SSMS) or sqlcmd available

**Setup Steps**:

```bash
# 1. Using sqlcmd (command line)
sqlcmd -S localhost -U sa -P 'YourPassword123!'

# 2. Create database and user
CREATE DATABASE cr_misc_function;
GO

CREATE LOGIN app_user WITH PASSWORD = 'YourSecurePassword123!';
GO

USE cr_misc_function;
CREATE USER app_user FOR LOGIN app_user;
GRANT ALL TO app_user;
GO

# 3. Exit sqlcmd
EXIT

# 4. Execute DDL files
sqlcmd -S localhost -U app_user -P 'YourSecurePassword123!' -d cr_misc_function -i db\ddl\mssql\schema_initial.sql
sqlcmd -S localhost -U app_user -P 'YourSecurePassword123!' -d cr_misc_function -i db\ddl\mssql\tables.sql
sqlcmd -S localhost -U app_user -P 'YourSecurePassword123!' -d cr_misc_function -i db\ddl\mssql\indexes.sql
```

**Connection String for Application**:

```text
mssql+pyodbc://app_user:YourSecurePassword123!@localhost/cr_misc_function?driver=ODBC+Driver+17+for+SQL+Server
```

### Hive Setup

**Prerequisites**:

- Hadoop cluster and Hive installed
- Hive CLI or `hive` command available
- NameNode, ResourceManager, and Hive Metastore running

**Setup Steps**:

```bash
# 1. Execute Hive DDL
hive -f db/ddl/hive/tables.sql

# 2. Verify tables created
hive -e "SHOW TABLES;"

# 3. Load sample data
hive -f db/seeds/development/hive_sample_data.sql
```

**Connection String for Application**:

```text
hive://hiveserver2@localhost:10000/default
```

### Trino Setup

**Prerequisites**:

- Trino server installed and running
- Trino CLI installed (`trino` command)
- Connector for your data source configured (PostgreSQL, MySQL, etc.)

**Setup Steps**:

```bash
# 1. Connect to Trino
trino --server http://localhost:8080 --catalog postgres --schema public

# 2. Trino DDL is typically not needed for existing data sources
# Trino queries existing databases via connectors

# 3. Example query to verify connectivity
SELECT * FROM postgres.public.users LIMIT 5;
```

**Connection String for Application**:

```text
trino://trino_user@localhost:8080/postgres/public
```

### Alibaba ODPS Setup

**Prerequisites**:

- Alibaba Cloud account with MaxCompute enabled
- ODPS Python SDK installed (`pip install pyodps`)
- Project created in MaxCompute console

**Setup Steps**:

```python
# 1. Configure connection in Python
from odps import ODPS

odps = ODPS(
    'your_access_id',
    'your_access_key',
    'your_project_name',
    'http://service.aliyun.com/api'
)

# 2. Execute DDL
with open('db/ddl/odps/tables.sql') as f:
    sql = f.read()
    odps.execute_sql(sql)

# 3. Verify tables
for table in odps.list_tables():
    print(table.name)
```

**Connection String for Application**:

```text
odps://your_access_id:your_access_key@your_project_name
```

---

## Seed Data

### Loading Development Data

```bash
# PostgreSQL
psql -U app_user -d cr_misc_function -f db/seeds/development/reference_data_seed.sql

# MySQL
mysql -u app_user -p cr_misc_function < db/seeds/development/reference_data_seed.sql

# MSSQL
sqlcmd -S localhost -U app_user -P 'password' -d cr_misc_function -i db\seeds\development\reference_data_seed.sql
```

### Loading Staging Data

```bash
# Similar to development, but use staging folder
psql -U app_user -d cr_misc_function -f db/seeds/staging/reference_data_seed.sql
```

### Production Data Considerations

- Never commit production data to version control
- Use separate seed scripts for production reference data only
- Document data refresh procedures in `db/backups/backup_strategy.md`
- Maintain backups for disaster recovery

---

## Verification

### Verify PostgreSQL Setup

```bash
# Connect to database
psql -U app_user -d cr_misc_function

# List tables
\dt

# Check schema
\dn

# Run test query
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

### Verify MySQL Setup

```bash
# Connect to database
mysql -u app_user -p cr_misc_function

# List tables
SHOW TABLES;

# Run test query
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'cr_misc_function';
```

### Verify MSSQL Setup

```sql
-- Connect in SQL Server Management Studio
USE cr_misc_function;

-- List tables
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;

-- Check schema
SELECT name FROM sys.schemas;
```

---

## Troubleshooting

### Issue: DDL Syntax Error

**Cause**: Database-specific SQL syntax differences

**Solution**:

- Ensure you're using the correct DDL file for your database type
- Check database version matches DDL requirements
- Review file header comments for database-specific notes

### Issue: Permission Denied

**Cause**: User doesn't have sufficient privileges

**Solution**:

- Verify user was granted proper permissions
- For PostgreSQL: `GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;`
- For MySQL: `GRANT ALL PRIVILEGES ON cr_misc_function.* TO 'app_user'@'localhost';`
- For MSSQL: `GRANT ALTER, CREATE, DELETE, INSERT, SELECT, UPDATE TO app_user;`

### Issue: Connection Refused

**Cause**: Database server not running or network issue

**Solution**:

- Check database service is running
- Verify network connectivity to database host
- Check firewall rules allow database port
- Verify connection string has correct host and port

### Issue: Character Encoding Issues

**Cause**: Database doesn't use UTF-8

**Solution**:

- PostgreSQL: `CREATE DATABASE cr_misc_function ENCODING 'UTF8';`
- MySQL: `CREATE DATABASE cr_misc_function CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- MSSQL: Use nvarchar/nchar data types

---

## Next Steps

1. **Configure Application**: Update `.env` files with your database connection strings
2. **Run Migrations**: If needed, execute migration scripts from `db/migrations/`
3. **Load Seed Data**: Populate reference data using seed scripts
4. **Set Up Backups**: Configure backup procedures from `db/backups/`
5. **Monitor**: Set up monitoring and logging for database health

---

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Microsoft SQL Server Documentation](https://docs.microsoft.com/en-us/sql/sql-server/)
- [Apache Hive Documentation](https://hive.apache.org/)
- [Trino Documentation](https://trino.io/docs/)
- [Alibaba ODPS Documentation](https://www.alibabacloud.com/help/en/maxcompute/)
