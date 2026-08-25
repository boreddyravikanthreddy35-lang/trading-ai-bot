-- ================================================================
-- SignalForge — Supabase (PostgreSQL) Schema
-- Run this entire script in: Supabase Dashboard → SQL Editor → New Query
-- ================================================================

-- ── Users ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT,
    password_hash TEXT,
    provider     TEXT DEFAULT 'email',
    picture      TEXT,
    created_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ── Signal Runs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signal_runs (
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
);
CREATE INDEX IF NOT EXISTS idx_signal_runs_user_created ON signal_runs (user_id, created_at DESC);

-- ── Bots ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bots (
    id               TEXT PRIMARY KEY,
    user_id          TEXT,
    name             TEXT,
    symbol           TEXT,
    timeframe        TEXT,
    model            TEXT,
    interval_minutes INTEGER,
    size_usd         FLOAT,
    min_confidence   FLOAT,
    allow_actions    JSONB,
    use_testnet      BOOLEAN DEFAULT FALSE,
    max_daily_loss   FLOAT,
    active           BOOLEAN DEFAULT FALSE,
    created_at       TEXT,
    updated_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_bots_user    ON bots (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bots_active  ON bots (active);
CREATE INDEX IF NOT EXISTS idx_bots_id      ON bots (id);

-- ── Bot Runs ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_runs (
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
);
CREATE INDEX IF NOT EXISTS idx_bot_runs_bot_created ON bot_runs (bot_id, created_at DESC);

-- ── Trades ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
    id            TEXT PRIMARY KEY,
    user_id       TEXT,
    symbol        TEXT,
    side          TEXT,
    quantity      FLOAT,
    price         FLOAT,
    fee           FLOAT,
    realized_pnl  FLOAT,
    cash_after    FLOAT,
    created_at    TEXT,
    source        TEXT,
    testnet_order JSONB
);
CREATE INDEX IF NOT EXISTS idx_trades_user_created ON trades (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_user_source  ON trades (user_id, source, created_at);

-- ── Portfolios ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolios (
    user_id    TEXT PRIMARY KEY,
    cash       FLOAT,
    created_at TEXT
);

-- ── Positions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS positions (
    user_id   TEXT,
    symbol    TEXT,
    quantity  FLOAT,
    avg_price FLOAT,
    PRIMARY KEY (user_id, symbol)
);

-- ── Watchlists ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlists (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    name       TEXT,
    symbols    JSONB,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists (user_id);

-- ── Alerts ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id               TEXT PRIMARY KEY,
    user_id          TEXT,
    symbol           TEXT,
    condition        TEXT,
    threshold        FLOAT,
    triggered        BOOLEAN DEFAULT FALSE,
    triggered_at     TEXT,
    triggered_price  FLOAT,
    created_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered  ON alerts (triggered);
CREATE INDEX IF NOT EXISTS idx_alerts_user       ON alerts (user_id, triggered);

-- ── Notifications ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    kind       TEXT,
    title      TEXT,
    body       TEXT,
    payload    JSONB,
    read       BOOLEAN DEFAULT FALSE,
    read_at    TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, read, created_at DESC);

-- ── Subscriptions ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id           TEXT PRIMARY KEY,
    plan_id           TEXT DEFAULT 'free',
    activated_at      TEXT,
    expires_at        TEXT,
    latest_session_id TEXT,
    updated_at        TEXT
);

-- ── Payment Transactions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payment_transactions (
    id                      TEXT PRIMARY KEY,
    session_id              TEXT UNIQUE,
    user_id                 TEXT,
    plan_id                 TEXT,
    amount                  FLOAT,
    currency                TEXT,
    status                  TEXT,
    payment_status          TEXT,
    metadata                JSONB,
    created_at              TEXT,
    updated_at              TEXT,
    applied_to_subscription BOOLEAN DEFAULT FALSE,
    applied_at              TEXT,
    amount_total            FLOAT,
    webhook_event           TEXT
);
CREATE INDEX IF NOT EXISTS idx_payment_session ON payment_transactions (session_id);
CREATE INDEX IF NOT EXISTS idx_payment_user    ON payment_transactions (user_id, created_at DESC);

-- ── Strategy Presets ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategy_presets (
    id           TEXT PRIMARY KEY,
    user_id      TEXT,
    name         TEXT,
    strategy     TEXT,
    interval     TEXT,
    "limit"      INTEGER,
    initial_cash FLOAT,
    fee_rate     FLOAT,
    fast         INTEGER,
    slow         INTEGER,
    rsi_period   INTEGER,
    oversold     FLOAT,
    overbought   FLOAT,
    created_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_presets_user ON strategy_presets (user_id, created_at DESC);

-- ── Exchange Settings ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exchange_settings (
    user_id    TEXT,
    exchange   TEXT,
    enabled    BOOLEAN DEFAULT FALSE,
    api_key    TEXT,
    api_secret TEXT,
    PRIMARY KEY (user_id, exchange)
);

-- ── Chat Conversations ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_conversations (
    id         TEXT PRIMARY KEY,
    signal_id  TEXT,
    user_id    TEXT,
    messages   JSONB,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE (signal_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_chat_signal_user ON chat_conversations (signal_id, user_id);

-- ================================================================
-- Done! All 15 tables created.
-- ================================================================
