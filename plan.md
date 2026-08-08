# plan.md (UPDATED)

## 1. Objectives
- ✅ **Validate the core AI market analysis pipeline** end-to-end using **real market data** and produce **strict JSON trading signals** from:
  - **Claude Sonnet 4.5** (Anthropic)
  - **Gemini 2.5 Pro** (Google)
- ✅ **Ship a complete V1 web app** (FastAPI + MongoDB, React + shadcn/ui) that includes:
  - Live market dashboard + charts
  - AI trading signals (Claude/Gemini/Both comparison)
  - Backtesting (SMA crossover, RSI, MACD)
  - Portfolio tracker + paper trading simulator ($10,000 start)
  - Watchlists + price alerts
  - Settings panel with **Binance testnet placeholder**
- ✅ **Authentication included in V1** (implemented earlier than originally planned):
  - Email/password (bcrypt + JWT)
  - Google OAuth via **Emergent Managed Auth** session flow (`auth.emergentagent.com` → `/oauth/callback`)
- 🔜 Optional next steps: production hardening, scalability, and Binance testnet execution.

> **Environment note:** Binance/Bybit public endpoints are geo-blocked in this environment. The platform uses **CoinGecko** for market overview and a **cascading OHLCV fallback** where **Kraken is primary** (with KuCoin also supported). This is already implemented and tested.

---

## 2. Implementation Steps

### Phase 1 — Core Workflow POC (isolation, must pass before app)
**Status: ✅ COMPLETE**

**User stories (fulfilled)**
1. ✅ Fetch live prices/metadata from CoinGecko.
2. ✅ Fetch OHLCV candles (klines) reliably even when Binance is unavailable.
3. ✅ Compute RSI/MACD/SMA/EMA with pandas/numpy.
4. ✅ Generate a strict-JSON trading signal from **Claude Sonnet 4.5**.
5. ✅ Generate a strict-JSON trading signal from **Gemini 2.5 Pro** and compare.

**What changed from original plan**
- Binance klines are geo-blocked (HTTP 451). The POC and the app now use:
  - CoinGecko for market overview/metadata
  - **Kraken** (primary) + **KuCoin** (fallback) for klines
  - Binance/Bybit remain in code as potential sources but are skipped automatically when blocked.

**Deliverables (completed)**
- ✅ `/app/backend/test_core.py`
  - CoinGecko market data
  - OHLCV klines via cascading sources
  - Indicator computation
  - Claude + Gemini signal generation with strict JSON validation

---

### Phase 2 — V1 App Development (full product)
**Status: ✅ COMPLETE + E2E TESTED**

**User stories (fulfilled)**
1. ✅ Dashboard shows top coins, market overview, and movers (CoinGecko).
2. ✅ Coin detail pages show interactive candlestick charts with overlays (lightweight-charts) from Kraken/KuCoin.
3. ✅ AI signals can be generated using **Claude**, **Gemini**, or **Both** with structured outputs.
4. ✅ Backtesting engine supports SMA crossover, RSI mean reversion, MACD crossover; shows equity curve + metrics + trades.
5. ✅ Paper trading includes a $10,000 portfolio, buy/sell simulation, holdings + PnL + trade history.
6. ✅ Watchlists  alerts are fully functional.
7. ✅ Settings include Binance testnet placeholder storage.
8. ✅ Authentication is implemented (email/password + Google OAuth) and protects all private resources.

**Backend (FastAPI + MongoDB, all routes under `/api`) — implemented**
- Services implemented:
  - `services/market_data.py` (CoinGecko + cascading exchange klines/tickers, TTL caching)
  - `services/indicators.py` (RSI/MACD/SMA/EMA, plus overlay series)
  - `services/ai_signals.py` (Claude/Gemini signal generation, JSON schema enforcement)
  - `services/backtest.py` (strategies + metrics)
  - `services/auth.py` (JWT + bcrypt)
- API routers implemented:
  - `api/market.py` (overview, coin detail, klines, movers, symbols)
  - `api/ai.py` (signal generation + history)
  - `api/backtest.py` (run + history)
  - `api/paper.py` (portfolio, order, trades, reset)
  - `api/watch.py` (watchlists + alerts + alert evaluation)
  - `api/auth_routes.py` (signup/login/me + Google OAuth session completion)
  - `api/settings.py` (Binance testnet placeholder)

**Frontend (React + shadcn/ui + lightweight-charts + Recharts) — implemented**
- App shell + navigation + protected routes
- Pages implemented:
  - `/landing`
  - `/login`, `/signup`, `/oauth/callback`
  - `/dashboard`
  - `/coin/:symbol`
  - `/signals`
  - `/backtest`
  - `/paper-trading`
  - `/watchlists`
  - `/alerts`
  - `/settings`
- UX requirements met:
  - Loading/empty/error states
  - Model comparison rendering
  - Copy-to-clipboard key levels
  - Toasts via Sonner
  - Dark mode default with upgraded tokens/typography per design guidelines

**Testing (completed)**
- ✅ Backend: **38/38 passed** (iteration_1)
- ✅ Frontend: **9/9 passed** after fixes (iteration_2)

**Fixes implemented from testing iteration_1**
1. ✅ Paper Trading BUY button unclickable → removed Radix Tabs overlay by using plain buttons.
2. ✅ Sign out didn’t redirect → `window.location.replace('/landing')`.
3. ✅ 401 handling hardening → `RequireAuth` checks both `user` and presence of `sf_token`.

---

### Phase 3 — Hardening + Polishing (optional)
**Status: ⏭️ OPTIONAL / NEXT**

**Goals**
- Operational resilience, better performance, and production readiness.

**User stories**
1. As a user, I have a safer, more stable experience under rate limits and network errors.
2. As a user, my data is protected with stronger auth/session practices.
3. As an operator, I have observability: logs/metrics and rate limiting.

**Suggested steps**
- Security
  - Add refresh tokens + rotation (optional)
  - Encrypt sensitive exchange secrets at rest
  - Add rate limiting (per IP + per user) for AI and market endpoints
- Reliability
  - Expand caching strategy (Redis optional)
  - Background jobs for alert checks (Celery/APS scheduler)
- UX polish
  - Add strategy presets and saving
  - Add export (CSV) for backtest trade logs
  - Add more symbols + robust symbol mapping

---

### Phase 4 — Binance Testnet Execution (incremental activation, optional)
**Status: ⏭️ OPTIONAL / NEXT**

**User stories**
1. As a user, I can add Binance testnet keys and validate connectivity.
2. As a user, I can choose paper vs testnet execution mode.
3. As a user, I can place testnet orders and see fills/status.
4. As a user, I can disable keys and fall back to paper trading.

**Suggested steps**
- Implement signed Binance testnet REST endpoints:
  - account balances
  - create order
  - query order
  - user data stream (optional)
- Broker abstraction:
  - `Broker = PaperBroker | BinanceTestnetBroker`
- Safety rails:
  - max order sizes, symbol allowlist, confirmation modal
- E2E tests with testnet (where feasible)

---

## 3. Next Actions
1. ✅ V1 is ready for hands-on user testing (landing → signup/login → dashboard → signals → paper trading).
2. (Optional) Prioritize Phase 3 hardening items depending on expected traffic and release intent.
3. (Optional) Implement Phase 4 Binance testnet execution with safety rails.

---

## 4. Success Criteria
- ✅ **POC**
  - For BTC/ETH/SOL, both Claude and Gemini return schema-valid JSON signals.
  - Market data is real and robust to exchange geo-blocks via cascading OHLCV sources.
- ✅ **V1 App**
  - Dashboard/charts load reliably.
  - AI signals work for Claude/Gemini/Both with reasoning + confidence.
  - Backtests return stable metrics and a trade log.
  - Paper trading updates holdings/PnL correctly.
  - Watchlists and alerts function end-to-end.
  - Auth (email/password + Google OAuth) is implemented and enforced.
- ✅ **Quality**
  - Backend tests: 38/38 passed.
  - Frontend tests: 9/9 passed after fixes.
- ✅ **Readiness**
  - Binance testnet settings placeholder exists; execution can be implemented without major refactor.
