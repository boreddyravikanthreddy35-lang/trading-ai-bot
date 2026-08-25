-- ============================================================================
-- 002_production_invariants_and_custody.sql
-- Production Invariants, Idempotency, Custody & Reconciliation Schema
-- ============================================================================

-- ── IDEMPOTENCY KEYS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key            TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL,
  endpoint       TEXT NOT NULL,
  request_hash   TEXT,
  response_code  INTEGER,
  response_body  JSONB,
  status         TEXT DEFAULT 'PROCESSING', -- PROCESSING, COMPLETED, FAILED
  created_at     TIMESTAMPTZ DEFAULT now(),
  expires_at     TIMESTAMPTZ DEFAULT now() + interval '24 hours'
);

-- ── DEPOSIT ADDRESSES (Custodial Wallets) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS deposit_addresses (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT NOT NULL,
  asset         TEXT NOT NULL,
  network       TEXT NOT NULL,              -- ERC20, TRC20, BEP20, BTC, SOL
  address       TEXT NOT NULL,
  memo_tag      TEXT,
  is_active     BOOLEAN DEFAULT true,
  created_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, asset, network)
);

-- ── BLOCKCHAIN TRANSACTIONS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blockchain_transactions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tx_hash          TEXT NOT NULL UNIQUE,
  user_id          TEXT,
  direction        TEXT NOT NULL,           -- INCOMING, OUTGOING
  asset            TEXT NOT NULL,
  network          TEXT NOT NULL,
  amount           NUMERIC(28,8) NOT NULL,
  fee              NUMERIC(28,8) DEFAULT 0,
  from_address     TEXT,
  to_address       TEXT,
  confirmations    INTEGER DEFAULT 0,
  required_confs   INTEGER DEFAULT 12,
  status           TEXT DEFAULT 'CONFIRMING', -- PENDING, CONFIRMING, CONFIRMED, FAILED
  ledger_tx_id     TEXT,
  block_number     BIGINT,
  created_at       TIMESTAMPTZ DEFAULT now(),
  confirmed_at     TIMESTAMPTZ
);

-- ── CUSTODY VAULTS (Exchange / Reserve Holdings) ────────────────────────────
CREATE TABLE IF NOT EXISTS custody_vaults (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vault_name    TEXT NOT NULL,              -- HOT_WALLET, COLD_STORAGE, BINANCE_EXCHANGE, OPERATIONAL
  vault_type    TEXT NOT NULL,              -- HOT, COLD, EXCHANGE, RESERVE
  asset         TEXT NOT NULL,
  balance       NUMERIC(28,8) DEFAULT 0 CHECK (balance >= 0),
  address       TEXT,
  last_audited  TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(vault_name, asset)
);

-- ── RECONCILIATION RUNS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reconciliation_runs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ran_at              TIMESTAMPTZ DEFAULT now(),
  status              TEXT NOT NULL,         -- CLEAN, BREAKS_DETECTED, ERROR
  total_checks        INTEGER DEFAULT 0,
  passed_checks       INTEGER DEFAULT 0,
  breaks_count        INTEGER DEFAULT 0,
  total_liability_usd NUMERIC(28,8) DEFAULT 0,
  total_custody_usd   NUMERIC(28,8) DEFAULT 0,
  summary             JSONB,
  duration_ms         INTEGER DEFAULT 0
);

-- ── RECONCILIATION BREAKS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reconciliation_breaks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reconciliation_id   UUID REFERENCES reconciliation_runs(id),
  break_type          TEXT NOT NULL,         -- BALANCE_MISMATCH, UNBALANCED_LEDGER, ORPHAN_ORDER, CUSTODY_DEFICIT, POSITION_MISMATCH
  severity            TEXT DEFAULT 'HIGH',   -- LOW, MEDIUM, HIGH, CRITICAL
  asset               TEXT,
  user_id             TEXT,
  expected_value      NUMERIC(28,8),
  actual_value        NUMERIC(28,8),
  discrepancy         NUMERIC(28,8),
  details             JSONB,
  status              TEXT DEFAULT 'OPEN',   -- OPEN, ACKNOWLEDGED, RESOLVED
  resolved_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT now()
);

-- ── SYSTEM EVENTS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type  TEXT NOT NULL,
  actor_type  TEXT DEFAULT 'SYSTEM',         -- USER, AI_ENGINE, RISK_ENGINE, SETTLEMENT, RECONCILIATION
  actor_id    TEXT,
  entity_type TEXT,
  entity_id   TEXT,
  payload     JSONB,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- ── INDEXES ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_idempotency_user ON idempotency_keys(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deposit_addr_user ON deposit_addresses(user_id, asset);
CREATE INDEX IF NOT EXISTS idx_blockchain_tx_hash ON blockchain_transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_custody_vault_asset ON custody_vaults(vault_name, asset);
CREATE INDEX IF NOT EXISTS idx_recon_runs_date ON reconciliation_runs(ran_at DESC);
CREATE INDEX IF NOT EXISTS idx_recon_breaks_status ON reconciliation_breaks(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type, created_at DESC);
