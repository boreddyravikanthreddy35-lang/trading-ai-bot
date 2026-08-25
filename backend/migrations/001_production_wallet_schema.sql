-- ============================================================================
-- 001_production_wallet_schema.sql
-- Production-grade double-entry ledger wallet for AI Crypto Trading Platform
-- Run in Supabase dashboard → SQL Editor
-- ============================================================================

CREATE TABLE IF NOT EXISTS assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL UNIQUE,
  name TEXT,
  asset_type TEXT DEFAULT 'CRYPTO',
  decimals INTEGER DEFAULT 8,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO assets (symbol, name, asset_type, decimals) VALUES
  ('USDT','Tether USD','CRYPTO',2),('BTC','Bitcoin','CRYPTO',8),
  ('ETH','Ethereum','CRYPTO',8),('SOL','Solana','CRYPTO',8),
  ('BNB','Binance Coin','CRYPTO',8),('ADA','Cardano','CRYPTO',8),
  ('DOGE','Dogecoin','CRYPTO',8),('XRP','XRP','CRYPTO',8),
  ('PEPE','Pepe','CRYPTO',8),('AVAX','Avalanche','CRYPTO',8),
  ('LINK','Chainlink','CRYPTO',8),('MATIC','Polygon','CRYPTO',8),
  ('SHIB','Shiba Inu','CRYPTO',8)
ON CONFLICT (symbol) DO NOTHING;

CREATE TABLE IF NOT EXISTS wallets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  wallet_type TEXT DEFAULT 'SPOT',
  status TEXT DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, wallet_type)
);

CREATE TABLE IF NOT EXISTS accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  status TEXT DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(wallet_id, asset)
);

CREATE TABLE IF NOT EXISTS wallet_balances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id),
  user_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  available NUMERIC(28,8) DEFAULT 0 CHECK (available >= 0),
  locked NUMERIC(28,8) DEFAULT 0 CHECK (locked >= 0),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(wallet_id, asset)
);

CREATE TABLE IF NOT EXISTS ledger_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  type TEXT NOT NULL,
  reference_type TEXT,
  reference_id TEXT,
  status TEXT DEFAULT 'PENDING',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ledger_transaction_id UUID NOT NULL REFERENCES ledger_transactions(id),
  wallet_id UUID NOT NULL REFERENCES wallets(id),
  account_id UUID REFERENCES accounts(id),
  asset TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('DEBIT','CREDIT')),
  amount NUMERIC(28,8) NOT NULL CHECK (amount > 0),
  balance_after NUMERIC(28,8),
  entry_purpose TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS balance_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  wallet_id UUID NOT NULL REFERENCES wallets(id),
  snapshot_at TIMESTAMPTZ DEFAULT now(),
  balances JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
  order_type TEXT DEFAULT 'MARKET',
  quantity NUMERIC(28,8),
  price NUMERIC(28,8),
  quote_amount NUMERIC(28,8),
  status TEXT DEFAULT 'NEW',
  filled_quantity NUMERIC(28,8) DEFAULT 0,
  filled_quote NUMERIC(28,8) DEFAULT 0,
  average_fill_price NUMERIC(28,8),
  source TEXT DEFAULT 'AI_AUTO',
  ai_decision_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  user_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  price NUMERIC(28,8) NOT NULL,
  quantity NUMERIC(28,8) NOT NULL,
  quote_amount NUMERIC(28,8) NOT NULL,
  fee NUMERIC(28,8) DEFAULT 0,
  fee_asset TEXT DEFAULT 'USDT',
  ledger_transaction_id TEXT,
  executed_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  quantity NUMERIC(28,8) DEFAULT 0,
  average_entry_price NUMERIC(28,8) DEFAULT 0,
  current_price NUMERIC(28,8) DEFAULT 0,
  unrealized_pnl NUMERIC(28,8) DEFAULT 0,
  realized_pnl NUMERIC(28,8) DEFAULT 0,
  total_invested NUMERIC(28,8) DEFAULT 0,
  status TEXT DEFAULT 'OPEN',
  opened_at TIMESTAMPTZ DEFAULT now(),
  closed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, symbol)
);

CREATE TABLE IF NOT EXISTS ai_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  decision TEXT NOT NULL,
  confidence NUMERIC(5,2),
  score INTEGER,
  market_regime TEXT,
  entry_price NUMERIC(28,8),
  target_price NUMERIC(28,8),
  stop_loss NUMERIC(28,8),
  risk_reward NUMERIC(8,4),
  risk_score NUMERIC(5,2),
  risk_verdict TEXT,
  risk_rejection_reason TEXT,
  strategy TEXT DEFAULT 'AI_AUTO',
  model_version TEXT DEFAULT 'v1.0',
  reason TEXT,
  order_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deposits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  wallet_id UUID NOT NULL REFERENCES wallets(id),
  asset TEXT NOT NULL,
  amount NUMERIC(28,8) NOT NULL CHECK (amount > 0),
  fee NUMERIC(28,8) DEFAULT 0,
  net_amount NUMERIC(28,8),
  status TEXT DEFAULT 'PENDING',
  simulated BOOLEAN DEFAULT true,
  tx_hash TEXT,
  ledger_transaction_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  confirmed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS withdrawals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  wallet_id UUID NOT NULL REFERENCES wallets(id),
  asset TEXT NOT NULL,
  amount NUMERIC(28,8) NOT NULL CHECK (amount > 0),
  fee NUMERIC(28,8) DEFAULT 0,
  net_amount NUMERIC(28,8),
  destination_address TEXT,
  status TEXT DEFAULT 'PENDING',
  tx_hash TEXT,
  ledger_transaction_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  event_type TEXT NOT NULL,
  entity_type TEXT,
  entity_id TEXT,
  payload JSONB,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_balances_user ON wallet_balances(user_id, asset);
CREATE INDEX IF NOT EXISTS idx_ledger_tx_user ON ledger_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_tx ON ledger_entries(ledger_transaction_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_events_order ON order_events(order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_executions_order ON executions(order_id);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_user ON ai_decisions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deposits_user ON deposits(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
