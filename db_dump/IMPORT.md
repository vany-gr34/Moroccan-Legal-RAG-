# Import PostgreSQL Database Dumps

This folder contains database dumps of the **Moroccan Legal RAG** PostgreSQL database.

## Available Dump Files

| File | Size | Description |
|------|------|-------------|
| `legal_rag_full.sql` | ~39 MB | **Full dump** — schema + data (all tables) |
| `legal_rag_schema.sql` | ~8 KB | **Schema-only** — table definitions, indexes, extensions (no data) |
| `legal_chunks_dump.sql` | ~39 MB | Legacy data dump (kept for compatibility) |

## Prerequisites

- [Docker](https://docs.docker.com/) installed
- PostgreSQL client (`psql`) installed on your host **OR** access to a running PostgreSQL container

---

## Option 1: Import via Docker (recommended)

If you are running the project with the existing `docker-compose.yaml`:

```bash
# 1. Make sure the PostgreSQL container is running
docker compose up -d postgres

# 2. Import the full dump (replaces existing data)
docker exec -i legal-rag-postgres psql -U legal_rag_user -d legal_rag < db_dump/legal_rag_full.sql

# Or import schema only (empty tables)
docker exec -i legal-rag-postgres psql -U legal_rag_user -d legal_rag < db_dump/legal_rag_schema.sql
```

### Fresh start (reset + import)

If you want to start from scratch:

```bash
# 1. Stop and delete the existing database volume
docker compose down -v

# 2. Start PostgreSQL fresh
docker compose up -d postgres

# 3. Wait for health check to pass, then import
sleep 5
docker exec -i legal-rag-postgres psql -U legal_rag_user -d legal_rag < db_dump/legal_rag_full.sql
```

---

## Option 2: Import via Host `psql`

If you have `psql` installed on your host and PostgreSQL is accessible:

```bash
# Default connection (from docker-compose defaults)
psql -h localhost -p 5432 -U legal_rag_user -d legal_rag < db_dump/legal_rag_full.sql
```

You will be prompted for the password (`legal_rag_pass` by default). To avoid the prompt, set `PGPASSWORD`:

```bash
PGPASSWORD=legal_rag_pass psql -h localhost -p 5432 -U legal_rag_user -d legal_rag < db_dump/legal_rag_full.sql
```

---

## Option 3: Import into a New Database

```bash
# Create a fresh database
createdb -h localhost -p 5432 -U legal_rag_user new_database_name

# Import into it
psql -h localhost -p 5432 -U legal_rag_user -d new_database_name < db_dump/legal_rag_full.sql
```

> **Note:** The `pgvector` extension must be available on the target PostgreSQL instance.

---

## Verifying the Import

After importing, you can verify the data:

```bash
# List tables
docker exec legal-rag-postgres psql -U legal_rag_user -d legal_rag -c "\dt"

# Count rows
docker exec legal-rag-postgres psql -U legal_rag_user -d legal_rag -c "SELECT COUNT(*) FROM legal_chunks;"

# Check extensions
docker exec legal-rag-postgres psql -U legal_rag_user -d legal_rag -c "\dx"
```

---

## How the Dump Was Created

The dumps were generated using `pg_dump` inside the running container:

```bash
# Full dump (schema + data)
docker exec legal-rag-postgres pg_dump -U legal_rag_user -d legal_rag --no-owner --no-privileges > db_dump/legal_rag_full.sql

# Schema only
docker exec legal-rag-postgres pg_dump -U legal_rag_user -d legal_rag --schema-only --no-owner --no-privileges > db_dump/legal_rag_schema.sql
```

Flags used:
- `--no-owner` — skip commands to set ownership (avoids errors if usernames differ)
- `--no-privileges` — do not dump privilege grants (portable across environments)
- `--schema-only` — dump only DDL (no data)
