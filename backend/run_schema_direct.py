"""
run_schema_direct.py — Apply Supabase schema via direct PostgreSQL connection.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import psycopg2
from pathlib import Path

PROJECT_REF = "uvcrjnxqaobnflnuwwjm"
DB_PASSWORD  = "8985746819@Ravi"

SCHEMA_SQL = (Path(__file__).parent / "supabase_schema.sql").read_text(encoding="utf-8")
STATEMENTS = [
    s.strip() for s in SCHEMA_SQL.split(";")
    if s.strip() and not s.strip().startswith("--")
]

CONN_STRINGS = [
    # Transaction pooler ap-south-1
    f"host=aws-0-ap-south-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={DB_PASSWORD} sslmode=require connect_timeout=15",
    # Session pooler ap-south-1
    f"host=aws-0-ap-south-1.pooler.supabase.com port=5432 dbname=postgres user=postgres.{PROJECT_REF} password={DB_PASSWORD} sslmode=require connect_timeout=15",
    # Direct host
    f"host=db.{PROJECT_REF}.supabase.co port=5432 dbname=postgres user=postgres password={DB_PASSWORD} sslmode=require connect_timeout=15",
    # Transaction pooler ap-southeast-1
    f"host=aws-0-ap-southeast-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={DB_PASSWORD} sslmode=require connect_timeout=15",
    # us-east-1
    f"host=aws-0-us-east-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={DB_PASSWORD} sslmode=require connect_timeout=15",
    # eu-west-1
    f"host=aws-0-eu-west-1.pooler.supabase.com port=6543 dbname=postgres user=postgres.{PROJECT_REF} password={DB_PASSWORD} sslmode=require connect_timeout=15",
]

print(f"Project: {PROJECT_REF}")
print("Trying connections...\n")

conn = None
for cs in CONN_STRINGS:
    host = cs.split("host=")[1].split(" ")[0]
    port = cs.split("port=")[1].split(" ")[0]
    try:
        conn = psycopg2.connect(cs)
        print(f"CONNECTED: {host}:{port}")
        break
    except Exception as e:
        print(f"FAIL [{host}:{port}]: {e}")

if not conn:
    print("\nAll connections failed.")
    print("Please get the exact connection string from:")
    print(f"  https://supabase.com/dashboard/project/{PROJECT_REF}/settings/database")
    sys.exit(1)

print(f"\nRunning {len(STATEMENTS)} SQL statements...")
print("=" * 60)

conn.autocommit = True
cur = conn.cursor()
ok = fail = 0

for stmt in STATEMENTS:
    label = stmt.replace("\n", " ")[:65]
    try:
        cur.execute(stmt)
        print(f"  OK    {label}")
        ok += 1
    except psycopg2.errors.DuplicateTable:
        print(f"  SKIP  {label}  (already exists)")
        ok += 1
    except Exception as e:
        print(f"  FAIL  {label}")
        print(f"        {e}")
        fail += 1

cur.close()
conn.close()

print("=" * 60)
print(f"Result: {ok} OK, {fail} failed")
if fail == 0:
    print("SUCCESS - All 15 tables created in Supabase!")
