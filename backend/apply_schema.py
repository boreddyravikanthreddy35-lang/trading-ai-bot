"""
apply_schema.py — Applies the SignalForge SQL schema to Supabase.
Run once: python apply_schema.py
"""
import os
import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
    sys.exit(1)

print(f"Connecting to: {SUPABASE_URL}")

# Each table as a separate CREATE statement
TABLES = [
    # users
    """CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT,
    password_hash TEXT,
    provider      TEXT DEFAULT 'email',
    picture       TEXT,
    created_at    TEXT
)""",

    # signal_runs
    """CREATE TABLE IF NOT EXISTS signal_runs (
    id           TEXT PRIMARY KEY,
    user_id      TEXT,
    symbol       TEXT,
    timeframe    TEXT,
    model        TEXT,
    kline_source TEXT,
    indicators   JSONB,
    coin_meta    JSONB,
    results      JSONB,
    created_at   TEXT
)""",

    # bots
    """CREATE TABLE IF NOT EXISTS bots (
    id               TEXT PRIMARY KEY,
    user_id          TEXT,
    name             TEXT,
    symbol           TEXT,
    timeframe        TEXT,
    model            TEXT,
    interval_minutes INTEGER,
    size_usd         FLOAT8,
    min_confidence   FLOAT8,
    allow_actions    JSONB,
    use_testnet      BOOLEAN DEFAULT FALSE,
    max_daily_loss   FLOAT8,
    active           BOOLEAN DEFAULT FALSE,
    created_at       TEXT,
    updated_at       TEXT
)""",

    # bot_runs
    """CREATE TABLE IF NOT EXISTS bot_runs (
    id          TEXT PRIMARY KEY,
    bot_id      TEXT,
    user_id     TEXT,
    symbol      TEXT,
    timeframe   TEXT,
    model       TEXT,
    created_at  TEXT,
    status      TEXT,
    error       TEXT,
    ai_raw      TEXT,
    signal      JSONB,
    indicators  JSONB,
    skip_reason TEXT,
    execution   JSONB
)""",

    # trades
    """CREATE TABLE IF NOT EXISTS trades (
    id            TEXT PRIMARY KEY,
    user_id       TEXT,
    symbol        TEXT,
    side          TEXT,
    quantity      FLOAT8,
    price         FLOAT8,
    fee           FLOAT8,
    realized_pnl  FLOAT8,
    cash_after    FLOAT8,
    created_at    TEXT,
    source        TEXT,
    testnet_order JSONB
)""",

    # portfolios
    """CREATE TABLE IF NOT EXISTS portfolios (
    user_id    TEXT PRIMARY KEY,
    cash       FLOAT8,
    created_at TEXT
)""",

    # positions
    """CREATE TABLE IF NOT EXISTS positions (
    user_id   TEXT,
    symbol    TEXT,
    quantity  FLOAT8,
    avg_price FLOAT8,
    PRIMARY KEY (user_id, symbol)
)""",

    # watchlists
    """CREATE TABLE IF NOT EXISTS watchlists (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    name       TEXT,
    symbols    JSONB,
    created_at TEXT
)""",

    # alerts
    """CREATE TABLE IF NOT EXISTS alerts (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,
    symbol          TEXT,
    condition       TEXT,
    threshold       FLOAT8,
    triggered       BOOLEAN DEFAULT FALSE,
    triggered_at    TEXT,
    triggered_price FLOAT8,
    created_at      TEXT
)""",

    # notifications
    """CREATE TABLE IF NOT EXISTS notifications (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    kind       TEXT,
    title      TEXT,
    body       TEXT,
    payload    JSONB,
    read       BOOLEAN DEFAULT FALSE,
    read_at    TEXT,
    created_at TEXT
)""",

    # subscriptions
    """CREATE TABLE IF NOT EXISTS subscriptions (
    user_id           TEXT PRIMARY KEY,
    plan_id           TEXT DEFAULT 'free',
    activated_at      TEXT,
    expires_at        TEXT,
    latest_session_id TEXT,
    updated_at        TEXT
)""",

    # payment_transactions
    """CREATE TABLE IF NOT EXISTS payment_transactions (
    id                      TEXT PRIMARY KEY,
    session_id              TEXT UNIQUE,
    user_id                 TEXT,
    plan_id                 TEXT,
    amount                  FLOAT8,
    currency                TEXT,
    status                  TEXT,
    payment_status          TEXT,
    metadata                JSONB,
    created_at              TEXT,
    updated_at              TEXT,
    applied_to_subscription BOOLEAN DEFAULT FALSE,
    applied_at              TEXT,
    amount_total            FLOAT8,
    webhook_event           TEXT
)""",

    # strategy_presets
    """CREATE TABLE IF NOT EXISTS strategy_presets (
    id           TEXT PRIMARY KEY,
    user_id      TEXT,
    name         TEXT,
    strategy     TEXT,
    interval     TEXT,
    candle_limit INTEGER,
    initial_cash FLOAT8,
    fee_rate     FLOAT8,
    fast         INTEGER,
    slow         INTEGER,
    rsi_period   INTEGER,
    oversold     FLOAT8,
    overbought   FLOAT8,
    created_at   TEXT
)""",

    # exchange_settings
    """CREATE TABLE IF NOT EXISTS exchange_settings (
    user_id    TEXT,
    exchange   TEXT,
    enabled    BOOLEAN DEFAULT FALSE,
    api_key    TEXT,
    api_secret TEXT,
    PRIMARY KEY (user_id, exchange)
)""",

    # chat_conversations
    """CREATE TABLE IF NOT EXISTS chat_conversations (
    id         TEXT PRIMARY KEY,
    signal_id  TEXT,
    user_id    TEXT,
    messages   JSONB,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE (signal_id, user_id)
)""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_email          ON users (email)",
    "CREATE INDEX IF NOT EXISTS idx_signal_runs_user     ON signal_runs (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_bots_user            ON bots (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_bots_active          ON bots (active)",
    "CREATE INDEX IF NOT EXISTS idx_bot_runs_bot         ON bot_runs (bot_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_trades_user_created  ON trades (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_trades_user_source   ON trades (user_id, source, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_triggered     ON alerts (triggered)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_user          ON alerts (user_id, triggered)",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user   ON notifications (user_id, read, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_payment_session      ON payment_transactions (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_payment_user         ON payment_transactions (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_presets_user         ON strategy_presets (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_watchlists_user      ON watchlists (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_signal_user     ON chat_conversations (signal_id, user_id)",
]

def apply_via_rpc():
    """Apply schema using Supabase's pg-meta SQL endpoint."""
    import httpx
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_KEY,
    }

    all_statements = TABLES + INDEXES
    passed, failed = 0, 0

    for stmt in all_statements:
        name = stmt.strip().split("\n")[0][:60]
        try:
            r = httpx.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"sql": stmt},
                timeout=15,
            )
            if r.status_code in (200, 201, 204):
                print(f"  ✅ {name}")
                passed += 1
            else:
                # Try pg-meta endpoint
                r2 = httpx.post(
                    f"{SUPABASE_URL}/pg-meta/v0/query",
                    headers=headers,
                    json={"query": stmt},
                    timeout=15,
                )
                if r2.status_code in (200, 201, 204):
                    print(f"  ✅ {name}")
                    passed += 1
                else:
                    print(f"  ⚠️  {name} → {r2.status_code}: {r2.text[:120]}")
                    failed += 1
        except Exception as e:
            print(f"  ❌ {name} → {e}")
            failed += 1

    return passed, failed


def apply_via_direct_postgres():
    """Apply schema via direct PostgreSQL connection (requires psycopg2)."""
    try:
        import psycopg2
    except ImportError:
        return None, "psycopg2 not installed"

    # Supabase direct connection string
    db_url = (
        f"postgresql://postgres.{SUPABASE_URL.split('//')[1].split('.')[0]}"
        f":{SUPABASE_SERVICE_KEY}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    )
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        passed, failed = 0, 0
        for stmt in TABLES + INDEXES:
            name = stmt.strip().split("\n")[0][:60]
            try:
                cur.execute(stmt)
                print(f"  ✅ {name}")
                passed += 1
            except Exception as e:
                print(f"  ⚠️  {name} → {e}")
                failed += 1
        cur.close()
        conn.close()
        return passed, failed
    except Exception as e:
        return None, str(e)


if __name__ == "__main__":
    import sys
    # Force UTF-8 output on Windows
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n>>> Applying SignalForge schema to Supabase...")
    print("=" * 60)

    passed, failed = apply_via_rpc()

    print("=" * 60)
    print(f"PASSED: {passed}   FAILED: {failed}")

    if failed > 0:
        print("\nSome statements could not be applied via REST API.")
        print("ACTION REQUIRED: Run backend/supabase_schema.sql manually in:")
        print("  Supabase Dashboard -> SQL Editor -> New Query -> paste -> Run")
    else:
        print("\nAll tables and indexes created successfully!")
