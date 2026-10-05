# 📘 Access Registry Guidelines

## 🧱 Column Definitions

---

### 🔹 `name`

**Format:**

```text
env.platform.service.resource[.qualifier][.old]
```

**Rules:**

- Auto-generated (DO NOT type manually)
- Lowercase, dot-separated
- `.old` is appended **only if `status = deprecated`**

**Example:**

```text
prod.acs.kafka.bootstrap
prod.acs.kafka.bootstrap.old
dev.onprem.mssql.af_rules.app
```

---

### 🔹 `env`

**Purpose:** Environment identifier

**Allowed values:**

```text
dev
sit
stg
prod
```

---

### 🔹 `platform`

**Purpose:** Where the service is hosted

**Allowed values:**

```text
acs
gcp
aws
onprem
local
github
```

---

### 🔹 `service`

**Purpose:** Technology / system type

**Examples:**

```text
kafka
postgres
mysql
mssql
hive
odps
trino
hologres
oss
ssh
grafana
prometheus
elasticsearch
vault
cicd
apigee
git
registry
```

---

### 🔹 `resource`

**Purpose:** Main target of the connection

**Rules:**

- Use **actual system identifier**
- Free text but **must follow snake_case**
- Must NOT be empty

**Examples:**

```text
af_rules
customer
bootstrap
cluster
instance
da_dev
raw_data_prod
```

**Notes:**

- For DB → use **database/schema name**
- For SSH → use **server name**
- For Kafka → use **cluster / bootstrap**
- For Grafana → use **instance**

---

### 🔹 `qualifier`

**Purpose:** Describe **usage / role / variation**

**Rules:**

- Optional
- Snake_case
- Short and meaningful
- Should NOT duplicate `resource`

**Examples:**

```text
app
readonly
etl
test
tuning
login
oauth
signature
key
password
```

**Do NOT use:**

```text
username ❌
tool name (pgadmin, dbeaver) ❌
vague terms (misc, stuff) ❌
```

---

### 🔹 `status`

**Purpose:** Lifecycle state

**Allowed values:**

```text
active
inactive
deprecated
unknown
```

**Meaning:**

- `active` → usable
- `inactive` → temporarily unusable
- `deprecated` → replaced / should not be used
- `unknown` → not verified yet

---

### 🔹 `host_domain`

**Purpose:** Primary hostname or web/API/UI domain (including protocol)

**Examples:**

```text
kafka.prod.internal
pg.dev.local
https://api.example.com
http://grafana.prod.local
https://oauth-provider.external/token
```

---

### 🔹 `host_ip`

**Purpose:** Fallback IP address

**Examples:**

```text
10.1.2.3
```

---

### 🔹 `port`

**Purpose:** Connection port

**Rules:**

- Numeric only
- One port per row

---

### 🔹 `username`

**Purpose:** Login user

**Examples:**

```text
admin
readonly_user
ubuntu
```

---

### 🔹 `secret_ref`

**Purpose:** Reference to secret storage location (no raw secrets here)

**Examples:**

```text
vault://prod/postgres/af_rules
vault://dev/ssh/da_dev/key
vault://prod/api/oauth_password
```

**Notes:**

- Can contain plaintext passwords/keys OR reference where they're stored in a secret manager (e.g. Vault, AWS Secrets Manager)
- For production: prefer secret manager references
- For dev/non-prod: can store credentials directly if sheet access is controlled
- Ensure this registry is properly secured and access-controlled

---

### 🔹 `connection_string`

**Purpose:** Helper field for `.env` usage

**Examples:**

```text
10.1.2.3:32400,10.1.2.3:32401
```

**Notes:**

- Generated (not manual)
- Used for Kafka / multi-port systems

---

### 🔹 `notes`

**Purpose:** Free text

**Use for:**
explanation
special config
issue description

**Do NOT use for:**

```text
structured data ❌
credentials ❌
```

---

## ⚖️ Core Rules

---

### ✅ 1. One Row = One Connection

A row represents:

```text
host + port + username + credential
```

---

### ✅ 2. Create New Row If

- different username
- different credential
- different host
- different port
- different auth method (password vs key)

---

### ❌ Do NOT Create New Row If

- only different tool (pgAdmin, DBeaver, etc.)

---

### ✅ 3. Naming Responsibility

| Field | Meaning |
| ----------- | --------------------- |
| service | what system |
| resource | what you connect to |
| qualifier | why / how used |

---

### ✅ 4. Resource vs Qualifier

```text
resource = af_rules (WHAT)
qualifier = app (WHY)
```

---

### ❌ Wrong

```text
resource = db
qualifier = af_rules ❌
```

---

### ✅ 5. Status Handling

- Only `deprecated` affects name (`.old`)
- Others do NOT affect naming

---

### ✅ 6. Multiple Ports

- One row per port
- Use `connection_string` to aggregate

---

### ✅ 7. SSH Special Case

- Different key/password → different row
- Use qualifier:

```text
key
password
```

---

### ✅ 8. API / Token / Signature

Use qualifier for auth type:

```text
oauth
signature
token
```

---

## 🏁 Final Principles

- Keep structure **simple and consistent**
- Prefer **meaning over cleverness**
- Optimize for:
  - readability
  - searchability
  - maintainability
