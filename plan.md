# plan.md

## 1. Objectives
- Prove the **core AI market analysis pipeline** works end-to-end with **real CoinGecko + Binance data** and returns **strict JSON signals** from **Claude Sonnet 4.5** and **Gemini 2.5 Pro**.
- Ship a V1 web app (FastAPI + MongoDB, React UI) that exposes: **dashboard + charts, AI signals, backtesting, paper trading, watchlists/alerts**, plus **Binance testnet hooks**.
- Add **email/password + Google OAuth** after core/V1 is stable (auth last to preserve testability).

## 2. Implementation Steps

### Phase 1 — Core Workflow POC (isolation, must pass before app)
**User stories**
1. As a user, I can run a script that fetches live prices/metadata from CoinGecko for a symbol.
2. As a user, I can fetch OHLCV klines from Binance for the same symbol/timeframe.
3. As a user, I can compute RSI/MACD/SMA/EMA from Binance candles.
4. As a user, I can request a trading signal from **Claude** and get valid JSON (action, confidence, reasoning, indicator summary).
5. As a user, I can request the same signal from **Gemini** and compare outputs side-by-side.

**Steps**
- Web search best practices/limits: CoinGecko rate limits, Binance klines params, symbol mapping (BTC ↔ BTCUSDT), LLM JSON enforcement patterns.
- Create `test_core.py` (no web server) that:
  - Pulls CoinGecko coin list → maps to Binance symbol.
  - Fetches: CoinGecko spot + market cap + 24h change; Binance OHLCV for (e.g.) 1h, last 500.
  - Computes indicators with pandas/numpy.
  - Builds a compact market context payload.
  - Calls Claude Sonnet 4.5 and Gemini 2.5 Pro via `emergentintegrations` using EMERGENT_LLM_KEY.
  - Enforces **strict JSON schema** (validate + re-ask on failure).
  - Prints a comparison report.
- Iterate until:
  - Data fetch is reliable (timeouts/retries/backoff).
  - JSON outputs validate consistently.
  - Prompts are stable and token-bounded.

**POC deliverables**
- `test_core.py` + `schemas.py` (pydantic models) + `market_data.py` + `indicators.py`.

---

### Phase 2 — V1 App Development (no auth; build around proven core)
**User stories**
1. As a user, I can open a dashboard that shows top coins, market overview, and top movers (real CoinGecko).
2. As a user, I can open a coin detail page with interactive price chart (candles/line) from Binance.
3. As a user, I can generate an AI signal for a coin choosing **Claude**, **Gemini**, or **Both**, and see structured output.
4. As a user, I can backtest SMA/RSI/MACD strategies over a date range and see PnL + trade log.
5. As a user, I can paper trade with a $10,000 starting balance, place buy/sell, and see holdings + PnL.

**Backend (FastAPI + MongoDB, all routes under `/api`)**
- Project structure: `app/main.py`, `app/api/*`, `app/services/*`, `app/models/*`.
- Core services (reuse POC code):
  - `CoinGeckoService` (prices, markets, metadata)
  - `BinanceMarketService` (klines, symbol helpers)
  - `IndicatorService` (RSI/MACD/SMA/EMA)
  - `SignalService` (LLM calls + JSON validation)
  - `BacktestService` (strategy runner + metrics)
  - `PaperBrokerService` (simulate fills, fees, positions)
  - `AlertService` (threshold alerts evaluated on refresh/poll)
- Mongo models/collections: users (later), portfolios, orders, trades, watchlists, alerts, signal_runs, backtest_runs.
- Key endpoints (examples):
  - `GET /api/market/overview` (CoinGecko markets/top movers)
  - `GET /api/market/klines?symbol=BTCUSDT&interval=1h&limit=500` (Binance)
  - `POST /api/ai/signal` (symbol, timeframe, model=claude|gemini|both)
  - `POST /api/backtest/run` (symbol, strategy params, range)
  - `GET/POST /api/paper/*` (portfolio, place order, history)
  - `GET/POST /api/watchlists/*`, `GET/POST /api/alerts/*`
  - `GET/POST /api/exchange/binance-testnet/*` (placeholder settings + connection test stub)
- Operational concerns: retries/timeouts, caching (in-memory TTL for market endpoints), input validation, consistent error payloads.

**Frontend (React + shadcn/ui + Recharts/lightweight-charts)**
- Env: `REACT_APP_BACKEND_URL` only.
- Pages:
  - Dashboard: top coins table, movers, sparkline mini charts.
  - Coin detail: candlestick/line chart + stats + “Generate AI Signal”.
  - AI Signals: compare Claude vs Gemini, render JSON into UI cards.
  - Backtesting: strategy form + results (equity curve, metrics, trades table).
  - Paper Trading: portfolio summary, order ticket, positions, trade history.
  - Watchlists & Alerts: manage list, thresholds, triggered state.
  - Settings: Binance testnet placeholder (stored server-side).
- UX requirements: loading/empty/error states everywhere; optimistic UI for paper trades; “copy JSON” + “explain differences” view for model comparison.

**Testing (end of Phase 2)**
- Run 1 full E2E pass:
  - Dashboard loads real data.
  - Coin chart renders from Binance.
  - Signal generation works for both models.
  - Backtest runs and returns stable metrics.
  - Paper trade updates portfolio correctly.
  - Alerts trigger when thresholds crossed (manual test by choosing tight thresholds).

---

### Phase 3 — Auth + Hardening + Polishing
**User stories**
1. As a user, I can create an account with email/password and securely log in.
2. As a user, I can log in with Google OAuth.
3. As a user, my portfolios/watchlists/alerts are private and tied to my account.
4. As a user, I can log out and my session is invalidated.
5. As a user, I can revisit and see my saved backtests and AI signal history.

**Steps**
- Email/password auth: bcrypt password hashing + JWT access tokens; refresh token optional for MVP.
- Google OAuth: integrate Emergent managed auth (or direct Google OAuth) + backend verification.
- Authorization middleware: protect user resources; migrate anonymous data (optional) → user.
- Add persistence for signal/backtest history per user.
- Add rate limiting + request logging; tighten CORS.
- End-of-phase E2E testing with authenticated flows.

---

### Phase 4 — Binance Testnet Execution (incremental activation)
**User stories**
1. As a user, I can enter Binance testnet keys and validate connectivity.
2. As a user, I can choose paper vs testnet mode.
3. As a user, I can place a small testnet order and see status updates.
4. As a user, I can view filled orders and positions from testnet.
5. As a user, I can disable keys and fall back to paper trading safely.

**Steps**
- Implement signed Binance testnet REST calls (create order, query order, account balances).
- Keep execution isolated behind an interface: `Broker = PaperBroker | BinanceTestnetBroker`.
- Add safety rails: max order size, allowlist symbols, confirmations.
- E2E tests with testnet (where feasible).

## 3. Next Actions
1. Implement and run **Phase 1 POC** (`test_core.py`) with strict JSON schema validation for both LLMs.
2. Lock down symbol mapping + indicator computations + prompt format until stable.
3. Once POC passes, scaffold backend routes and React pages (Phase 2) around the proven services.
4. Execute Phase 2 E2E test pass and fix all broken flows.
5. Ask for confirmation before starting Phase 3 auth (since it affects testability).

## 4. Success Criteria
- **POC**: For at least 3 symbols (e.g., BTC, ETH, SOL) and 2 timeframes, both Claude and Gemini return schema-valid JSON with action + confidence + reasoning; data is fetched only from CoinGecko/Binance.
- **V1 App**: Dashboard/charts load reliably; AI signal generation works; backtests produce consistent metrics; paper trading updates holdings/PnL correctly; watchlists/alerts function end-to-end.
- **Stability**: No mock data; consistent `/api` routing; only `REACT_APP_BACKEND_URL` and `MONGO_URL` env vars used; UI handles loading/empty/error states cleanly.
- **Readiness**: Binance testnet placeholder exists in V1; testnet execution can be added without refactoring core architecture.
