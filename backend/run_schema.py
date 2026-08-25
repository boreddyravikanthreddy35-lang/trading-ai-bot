"""
run_schema.py — Connect directly to Supabase PostgreSQL and apply schema.
Tries multiple connection string formats automatically.
"""
import sys
import os

# Force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Extract project ref from URL  e.g. uvcrjnxqaobnflnuwwjm
PROJECT_REF = SUPABASE_URL.replace("https://", "").split(".")[0]
print(f"Project ref: {PROJECT_REF}")

# Read the SQL schema
SCHEMA_FILE = Path(__file__).parent / "supabase_schema.sql"
schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

# Split into individual statements (split on semicolons)
statements = [s.strip() for s in schema_sql.split(";") if s.strip() and not s.strip().startswith("--")]

# Connection strings to try (Supabase regions for India)
CONN_STRINGS = [
    # Transaction pooler - ap-south-1 (Mumbai)
    f"host=aws-0-ap-south-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={SUPABASE_SERVICE_KEY} sslmode=require connect_timeout=10",
    # Session pooler - ap-south-1
    f"host=aws-0-ap-south-1.pooler.supabase.com port=5432 dbname=postgres user=postgres.{PROJECT_REF} password={SUPABASE_SERVICE_KEY} sslmode=require connect_timeout=10",
    # Direct connection
    f"host=db.{PROJECT_REF}.supabase.co port=5432 dbname=postgres user=postgres password={SUPABASE_SERVICE_KEY} sslmode=require connect_timeout=10",
    # Transaction pooler - ap-southeast-1 (Singapore)
    f"host=aws-0-ap-southeast-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={SUPABASE_SERVICE_KEY} sslmode=require connect_timeout=10",
    # us-east-1
    f"host=aws-0-us-east-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={SUPABASE_SERVICE_KEY} sslmode=require connect_timeout=10",
]

import psycopg2

def try_connect(conn_str: str):
    """Try to connect and return connection, or None on failure."""
    try:
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        short = conn_str.split("host=")[1].split(" ")[0] if "host=" in conn_str else conn_str[:40]
        print(f"  FAIL [{short}]: {e}")
        return None

print("\nTrying PostgreSQL connections to Supabase...")
print("=" * 60)

conn = None
for cs in CONN_STRINGS:
    conn = try_connect(cs)
    if conn:
        host = cs.split("host=")[1].split(" ")[0]
        print(f"  CONNECTED via: {host}")
        break

if not conn:
    print("\nAll connection attempts failed.")
    print("The service role key cannot be used as a DB password.")
    print("\nTo apply the schema, you need one of:")
    print("  1. Your Supabase DB password (Settings > Database > Connection string)")
    print("  2. Run the SQL manually:")
    print(f"     https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
    sys.exit(1)

print("\nApplying schema...")
print("=" * 60)

conn.autocommit = True
cur = conn.cursor()
passed = 0
failed = 0

for stmt in statements:
    # Get a short description for logging
    first_line = stmt.split("\n")[0][:70].strip()
    try:
        cur.execute(stmt)
        print(f"  OK  {first_line}")
        passed += 1
    except psycopg2.errors.DuplicateTable:
        print(f"  EXISTS  {first_line}")
        passed += 1
    except Exception as e:
        print(f"  FAIL  {first_line}")
        print(f"        -> {e}")
        failed += 1

cur.close()
conn.close()

print("=" * 60)
print(f"DONE: {passed} OK, {failed} failed")
if failed == 0:
    print("All 15 tables and indexes created in Supabase!")
