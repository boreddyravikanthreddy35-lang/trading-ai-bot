"""Create the missing backtest_runs table in Supabase."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SQL = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    id           TEXT PRIMARY KEY,
    user_id      TEXT,
    symbol       TEXT,
    interval     TEXT,
    candle_limit INTEGER,
    strategy     TEXT,
    initial_cash FLOAT8,
    fee_rate     FLOAT8,
    kline_source TEXT,
    result       JSONB,
    created_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user ON backtest_runs (user_id, created_at DESC);
"""

print("Please run this SQL in Supabase SQL Editor:")
print("https://supabase.com/dashboard/project/uvcrjnxqaobnflnuwwjm/sql/new")
print()
print(SQL)
