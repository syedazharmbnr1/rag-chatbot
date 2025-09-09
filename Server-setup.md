Absolutely — here’s a complete, single `README.md` file with **all steps to set up the server and PostgreSQL through the Linux terminal**, including remote access and chatbot DB setup.

---

### 📄 `README.md`

````markdown
# 🖥️ Server & PostgreSQL Setup Guide (Ubuntu)

This guide explains how to set up a new Ubuntu server, install PostgreSQL, configure remote access, and initialize a chatbot database schema.

---

## ✅ Prerequisites

- Ubuntu server with sudo access
- Public IPv4 address
- SSH access (username + password or key)
- Your client IP (to allow remote DB access)

---

## 1️⃣ Connect to the Server

```bash
ssh your_user@your_server_ip
````

---

## 2️⃣ Install PostgreSQL

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install postgresql postgresql-contrib -y
```

---

## 3️⃣ Start and Enable PostgreSQL 16

```bash
sudo systemctl start postgresql@16-main
sudo systemctl enable postgresql@16-main
```

---

## 4️⃣ Configure PostgreSQL for Remote Access

### 🔧 Edit `postgresql.conf`

```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
```

Uncomment and set:

```ini
listen_addresses = '*'
```

> This allows PostgreSQL to listen on all IPs.

---

### 🔧 Edit `pg_hba.conf`

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add this line at the **end** to allow all IPs (temporary/dev):

```ini
host    all             all             0.0.0.0/0               md5
```

> For production, replace `0.0.0.0/0` with your specific IP range.

---

### 🔁 Restart PostgreSQL

```bash
sudo systemctl restart postgresql@16-main
```

---

## 5️⃣ Open Port 5432 in Firewall

```bash
sudo ufw allow 5432/tcp
sudo ufw reload
```

---

## 6️⃣ Create PostgreSQL User & Database

```bash
sudo -u postgres psql
```

Inside the prompt:

```sql
CREATE USER chatbot_user WITH PASSWORD 'secure_password';
CREATE DATABASE chatbot_database OWNER chatbot_user;
\q
```

---

## 7️⃣ Test External Connection (Optional)

On your **local machine**:

```bash
psql -h your_server_ip -U chatbot_user -d chatbot_database
```

---

## 8️⃣ Python Example Connection String

```python
DATABASE_URL = "postgresql://chatbot_user:secure_password@your_server_ip:5432/chatbot_database"
```

---

## 9️⃣ Initialize Chatbot Tables

Use Python code to create tables (e.g. `init_database()` function).

Alternatively, connect to DB and run SQL:

```sql
-- conversations
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    user_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sources
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES messages(id),
    source_document TEXT NOT NULL,
    page_number INTEGER,
    score REAL,
    kb_name TEXT
);

-- settings
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL
);

-- knowledge_bases
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_count INTEGER DEFAULT 0,
    embedding_model TEXT NOT NULL,
    chunking_strategy TEXT NOT NULL
);

-- documents
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id),
    filename TEXT NOT NULL,
    document_type TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ✅ Done!

You can now deploy and run your app using `DATABASE_URL` to connect to the live PostgreSQL instance.

---

## 🛡️ Recommended for Production

* Replace `0.0.0.0/0` in `pg_hba.conf` with your IP:

  ```ini
  host all all your.public.ip/32 md5
  ```
* Use SSL for PostgreSQL connection
* Disable remote access to `postgres` superuser

```

---

Let me know if you'd like a `.sh` script version of this too.
```
