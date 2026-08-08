"""
Comprehensive backend API test suite for SignalForge AI Crypto Trading Platform.
Tests all endpoints: health, auth, market, AI signals, backtest, paper trading, watchlists, alerts, settings.
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://market-analyst-ai-21.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_email = f"test_{datetime.now().strftime('%H%M%S')}@signalforge.dev"
        self.test_password = "TestPass123!"
        
        # Store IDs for cleanup
        self.watchlist_id = None
        self.alert_id = None

    def log(self, emoji, message):
        print(f"{emoji} {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        self.log("🔍", f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, params=params, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=req_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log("✅", f"PASSED - Status: {response.status_code}")
                try:
                    return True, response.json()
                except Exception:
                    return True, {}
            else:
                self.log("❌", f"FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log("📄", f"Response: {response.text[:200]}")
                except Exception:
                    pass
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200] if response.text else ""
                })
                return False, {}

        except Exception as e:
            self.log("❌", f"FAILED - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}

    # ═══════════════════════════════════════════════════════════════════════
    # HEALTH & AUTH TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_health(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_signup(self):
        """Test user signup"""
        success, response = self.run_test(
            "Auth Signup",
            "POST",
            "auth/signup",
            200,
            data={"email": self.test_email, "password": self.test_password, "name": "Test User"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user', {}).get('id')
            self.log("🔑", f"Token acquired: {self.token[:20]}...")
            return True
        return False

    def test_signup_duplicate(self):
        """Test duplicate email signup"""
        return self.run_test(
            "Auth Signup Duplicate",
            "POST",
            "auth/signup",
            400,
            data={"email": self.test_email, "password": self.test_password}
        )

    def test_login(self):
        """Test user login"""
        success, response = self.run_test(
            "Auth Login",
            "POST",
            "auth/login",
            200,
            data={"email": self.test_email, "password": self.test_password}
        )
        if success and 'token' in response:
            self.token = response['token']
            return True
        return False

    def test_login_wrong_password(self):
        """Test login with wrong password"""
        return self.run_test(
            "Auth Login Wrong Password",
            "POST",
            "auth/login",
            401,
            data={"email": self.test_email, "password": "WrongPassword123!"}
        )

    def test_me_authenticated(self):
        """Test /me endpoint with token"""
        return self.run_test("Auth Me (authenticated)", "GET", "auth/me", 200)

    def test_me_unauthenticated(self):
        """Test /me endpoint without token"""
        old_token = self.token
        self.token = None
        result = self.run_test("Auth Me (unauthenticated)", "GET", "auth/me", 401)
        self.token = old_token
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # MARKET DATA TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_market_overview(self):
        """Test market overview endpoint"""
        success, response = self.run_test(
            "Market Overview",
            "GET",
            "market/overview",
            200,
            params={"per_page": 15}
        )
        if success:
            coins = response.get('coins', [])
            self.log("📊", f"Retrieved {len(coins)} coins")
            if len(coins) > 0:
                self.log("💰", f"First coin: {coins[0].get('name', 'N/A')} - ${coins[0].get('current_price', 0)}")
        return success

    def test_market_coin_detail(self):
        """Test coin detail endpoint"""
        success, response = self.run_test(
            "Market Coin Detail (bitcoin)",
            "GET",
            "market/coin/bitcoin",
            200
        )
        if success:
            self.log("📈", f"Bitcoin: ${response.get('current_price', 'N/A')}")
        return success

    def test_market_klines(self):
        """Test klines endpoint with indicators"""
        success, response = self.run_test(
            "Market Klines (BTCUSDT)",
            "GET",
            "market/klines",
            200,
            params={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "limit": 200,
                "with_indicators": "true"
            }
        )
        if success:
            candles = response.get('candles', [])
            indicators = response.get('indicators', {})
            indicator_series = response.get('indicator_series', {})
            self.log("📊", f"Retrieved {len(candles)} candles")
            self.log("📊", f"Indicators: {list(indicators.keys())}")
            self.log("📊", f"Indicator series: {list(indicator_series.keys())}")
        return success

    def test_market_movers_gainers(self):
        """Test top gainers endpoint"""
        success, response = self.run_test(
            "Market Movers (gainers)",
            "GET",
            "market/movers",
            200,
            params={"direction": "gainers", "limit": 5}
        )
        if success:
            coins = response.get('coins', [])
            self.log("🚀", f"Top {len(coins)} gainers retrieved")
        return success

    def test_market_movers_losers(self):
        """Test top losers endpoint"""
        success, response = self.run_test(
            "Market Movers (losers)",
            "GET",
            "market/movers",
            200,
            params={"direction": "losers", "limit": 5}
        )
        return success

    # ═══════════════════════════════════════════════════════════════════════
    # AI SIGNAL TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_ai_signal_claude(self):
        """Test AI signal generation with Claude"""
        self.log("⏳", "Generating Claude signal (may take 10-15 seconds)...")
        success, response = self.run_test(
            "AI Signal (Claude)",
            "POST",
            "ai/signal",
            200,
            data={"symbol": "BTCUSDT", "timeframe": "1h", "model": "claude"}
        )
        if success:
            # Store signal_id for chat tests
            if 'id' in response:
                self.signal_id = response['id']
                self.log("📊", f"Stored signal_id for chat tests: {self.signal_id}")
            results = response.get('results', [])
            if results:
                signal = results[0]
                self.log("🤖", f"Claude signal: {signal.get('action')} | Confidence: {signal.get('confidence')}% | Risk: {signal.get('risk_level')}")
                self.log("💡", f"Reasoning: {signal.get('reasoning', '')[:100]}...")
        return success

    def test_ai_signal_gemini(self):
        """Test AI signal generation with Gemini"""
        self.log("⏳", "Generating Gemini signal (may take 10-15 seconds)...")
        success, response = self.run_test(
            "AI Signal (Gemini)",
            "POST",
            "ai/signal",
            200,
            data={"symbol": "ETHUSDT", "timeframe": "1h", "model": "gemini"}
        )
        if success:
            results = response.get('results', [])
            if results:
                signal = results[0]
                self.log("🤖", f"Gemini signal: {signal.get('action')} | Confidence: {signal.get('confidence')}%")
        return success

    def test_ai_signal_both(self):
        """Test AI signal generation with both models"""
        self.log("⏳", "Generating signals from both models (may take 20-30 seconds)...")
        success, response = self.run_test(
            "AI Signal (Both)",
            "POST",
            "ai/signal",
            200,
            data={"symbol": "SOLUSDT", "timeframe": "1h", "model": "both"}
        )
        if success:
            results = response.get('results', [])
            self.log("🤖", f"Received {len(results)} signals (expected 2)")
            if len(results) == 2:
                self.log("✅", "Both Claude and Gemini signals received")
            for r in results:
                self.log("📊", f"  {r.get('model_used', 'unknown')}: {r.get('action')} ({r.get('confidence')}%)")
        return success

    def test_ai_history(self):
        """Test AI signal history"""
        success, response = self.run_test(
            "AI History",
            "GET",
            "ai/history",
            200
        )
        if success:
            signals = response.get('signals', [])
            self.log("📜", f"Retrieved {len(signals)} historical signals")
        return success

    # ═══════════════════════════════════════════════════════════════════════
    # BACKTEST TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_backtest_sma(self):
        """Test SMA crossover backtest"""
        self.log("⏳", "Running SMA backtest (may take a few seconds)...")
        success, response = self.run_test(
            "Backtest SMA Crossover",
            "POST",
            "backtest/run",
            200,
            data={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "strategy": "sma_crossover",
                "limit": 300,
                "initial_cash": 10000,
                "fast": 10,
                "slow": 30
            }
        )
        if success:
            result = response.get('result', {})
            metrics = result.get('metrics', {})
            self.log("📊", f"SMA Backtest: Total Return: {metrics.get('total_return_pct', 0):.2f}% | Trades: {metrics.get('total_trades', 0)}")
        return success

    def test_backtest_rsi(self):
        """Test RSI backtest"""
        self.log("⏳", "Running RSI backtest...")
        success, response = self.run_test(
            "Backtest RSI",
            "POST",
            "backtest/run",
            200,
            data={
                "symbol": "ETHUSDT",
                "interval": "1h",
                "strategy": "rsi",
                "limit": 300,
                "initial_cash": 10000
            }
        )
        if success:
            result = response.get('result', {})
            metrics = result.get('metrics', {})
            self.log("📊", f"RSI Backtest: Total Return: {metrics.get('total_return_pct', 0):.2f}%")
        return success

    def test_backtest_macd(self):
        """Test MACD backtest"""
        self.log("⏳", "Running MACD backtest...")
        success, response = self.run_test(
            "Backtest MACD",
            "POST",
            "backtest/run",
            200,
            data={
                "symbol": "BTCUSDT",
                "interval": "4h",
                "strategy": "macd",
                "limit": 200,
                "initial_cash": 10000
            }
        )
        return success

    # ═══════════════════════════════════════════════════════════════════════
    # PAPER TRADING TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_paper_portfolio_fresh(self):
        """Test fresh paper portfolio"""
        success, response = self.run_test(
            "Paper Portfolio (fresh)",
            "GET",
            "paper/portfolio",
            200
        )
        if success:
            cash = response.get('cash', 0)
            equity = response.get('equity', 0)
            self.log("💰", f"Portfolio: Cash=${cash:,.2f} | Equity=${equity:,.2f}")
        return success

    def test_paper_order_buy(self):
        """Test paper trading BUY order"""
        success, response = self.run_test(
            "Paper Order BUY",
            "POST",
            "paper/order",
            200,
            data={"symbol": "BTCUSDT", "side": "BUY", "quote_amount": 1000}
        )
        if success:
            self.log("💵", f"BUY order executed: {response.get('quantity', 0):.6f} BTC @ ${response.get('price', 0):,.2f}")
            self.log("💰", f"Cash after: ${response.get('cash_after', 0):,.2f}")
        return success

    def test_paper_portfolio_after_buy(self):
        """Test portfolio after BUY"""
        success, response = self.run_test(
            "Paper Portfolio (after BUY)",
            "GET",
            "paper/portfolio",
            200
        )
        if success:
            holdings = response.get('holdings', [])
            self.log("📊", f"Holdings: {len(holdings)} positions")
            for h in holdings:
                self.log("💼", f"  {h['symbol']}: {h['quantity']:.6f} @ ${h['avg_price']:,.2f}")
        return success

    def test_paper_order_sell(self):
        """Test paper trading SELL order"""
        # First get current holdings
        success, portfolio = self.run_test(
            "Paper Portfolio (before SELL)",
            "GET",
            "paper/portfolio",
            200
        )
        if not success:
            return False
        
        holdings = portfolio.get('holdings', [])
        btc_holding = next((h for h in holdings if h['symbol'] == 'BTCUSDT'), None)
        if not btc_holding:
            self.log("⚠️", "No BTCUSDT position to sell, skipping SELL test")
            return True
        
        # Sell half
        sell_qty = btc_holding['quantity'] * 0.5
        success, response = self.run_test(
            "Paper Order SELL",
            "POST",
            "paper/order",
            200,
            data={"symbol": "BTCUSDT", "side": "SELL", "quantity": sell_qty}
        )
        if success:
            self.log("💵", f"SELL order executed: {response.get('quantity', 0):.6f} BTC")
            self.log("💰", f"Realized PnL: ${response.get('realized_pnl', 0):,.2f}")
        return success

    def test_paper_order_insufficient_cash(self):
        """Test paper order with insufficient cash"""
        return self.run_test(
            "Paper Order (insufficient cash)",
            "POST",
            "paper/order",
            400,
            data={"symbol": "BTCUSDT", "side": "BUY", "quote_amount": 999999999}
        )

    def test_paper_trades(self):
        """Test paper trade history"""
        success, response = self.run_test(
            "Paper Trades History",
            "GET",
            "paper/trades",
            200
        )
        if success:
            trades = response.get('trades', [])
            self.log("📜", f"Retrieved {len(trades)} trades")
        return success

    def test_paper_reset(self):
        """Test paper portfolio reset"""
        success, response = self.run_test(
            "Paper Portfolio Reset",
            "POST",
            "paper/reset",
            200
        )
        if success:
            self.log("🔄", f"Portfolio reset to ${response.get('cash', 0):,.2f}")
        return success

    # ═══════════════════════════════════════════════════════════════════════
    # WATCHLIST TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_watchlist_create(self):
        """Test watchlist creation"""
        success, response = self.run_test(
            "Watchlist Create",
            "POST",
            "watch/lists",
            200,
            data={"name": "Favorites", "symbols": ["BTCUSDT", "ETHUSDT"]}
        )
        if success:
            self.watchlist_id = response.get('id')
            self.log("📋", f"Watchlist created: {response.get('name')} (ID: {self.watchlist_id})")
        return success

    def test_watchlist_list(self):
        """Test watchlist listing with live prices"""
        success, response = self.run_test(
            "Watchlist List",
            "GET",
            "watch/lists",
            200
        )
        if success:
            watchlists = response.get('watchlists', [])
            self.log("📋", f"Retrieved {len(watchlists)} watchlists")
            for w in watchlists:
                self.log("📊", f"  {w.get('name')}: {len(w.get('symbols', []))} symbols")
        return success

    def test_watchlist_update(self):
        """Test watchlist update"""
        if not self.watchlist_id:
            self.log("⚠️", "No watchlist ID, skipping update test")
            return True
        
        success, response = self.run_test(
            "Watchlist Update",
            "PATCH",
            f"watch/lists/{self.watchlist_id}",
            200,
            data={"symbols": ["BTCUSDT", "SOLUSDT"]}
        )
        if success:
            self.log("✏️", f"Watchlist updated: {response.get('symbols')}")
        return success

    def test_watchlist_delete(self):
        """Test watchlist deletion"""
        if not self.watchlist_id:
            self.log("⚠️", "No watchlist ID, skipping delete test")
            return True
        
        return self.run_test(
            "Watchlist Delete",
            "DELETE",
            f"watch/lists/{self.watchlist_id}",
            200
        )

    # ═══════════════════════════════════════════════════════════════════════
    # ALERT TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_alert_create(self):
        """Test alert creation"""
        success, response = self.run_test(
            "Alert Create",
            "POST",
            "watch/alerts",
            200,
            data={"symbol": "BTCUSDT", "condition": "above", "threshold": 1}
        )
        if success:
            self.alert_id = response.get('id')
            self.log("🔔", f"Alert created: {response.get('symbol')} {response.get('condition')} ${response.get('threshold')}")
        return success

    def test_alert_list(self):
        """Test alert listing"""
        success, response = self.run_test(
            "Alert List",
            "GET",
            "watch/alerts",
            200
        )
        if success:
            alerts = response.get('alerts', [])
            self.log("🔔", f"Retrieved {len(alerts)} alerts")
        return success

    def test_alert_check(self):
        """Test alert checking"""
        success, response = self.run_test(
            "Alert Check",
            "POST",
            "watch/alerts/check",
            200
        )
        if success:
            triggered = response.get('triggered', [])
            checked = response.get('checked', 0)
            self.log("🔔", f"Checked {checked} alerts, {len(triggered)} triggered")
        return success

    def test_alert_delete(self):
        """Test alert deletion"""
        if not self.alert_id:
            self.log("⚠️", "No alert ID, skipping delete test")
            return True
        
        return self.run_test(
            "Alert Delete",
            "DELETE",
            f"watch/alerts/{self.alert_id}",
            200
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SETTINGS TESTS
    # ═══════════════════════════════════════════════════════════════════════

    def test_settings_binance_save(self):
        """Test saving Binance testnet settings"""
        success, response = self.run_test(
            "Settings Binance Save",
            "POST",
            "settings/exchange/binance-testnet",
            200,
            data={
                "api_key": "test_api_key_12345678",
                "api_secret": "test_api_secret_12345678",
                "enabled": True
            }
        )
        if success:
            self.log("🔑", f"Binance settings saved: {response.get('api_key_masked')}")
        return success

    def test_settings_binance_get(self):
        """Test getting Binance testnet settings"""
        success, response = self.run_test(
            "Settings Binance Get",
            "GET",
            "settings/exchange/binance-testnet",
            200
        )
        if success:
            self.log("🔑", f"Binance configured: {response.get('configured')} | Enabled: {response.get('enabled')}")
        return success

    def test_settings_binance_delete(self):
        """Test deleting Binance testnet settings"""
        return self.run_test(
            "Settings Binance Delete",
            "DELETE",
            "settings/exchange/binance-testnet",
            200
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: CHAT ANALYST TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_chat_send_message(self):
        """Test sending a chat message about a signal"""
        if not hasattr(self, 'signal_id') or not self.signal_id:
            self.log("⚠️", "Skipping chat test - no signal_id available")
            return False, {}
        
        success, response = self.run_test(
            "Chat - Send Message",
            "POST",
            f"chat/{self.signal_id}/message",
            200,
            data={"signal_id": self.signal_id, "model": "claude", "message": "Why did you pick this action?"}
        )
        return success, response
    
    def test_chat_get_conversation(self):
        """Test getting chat conversation"""
        if not hasattr(self, 'signal_id') or not self.signal_id:
            self.log("⚠️", "Skipping chat get test - no signal_id available")
            return False, {}
        
        success, response = self.run_test(
            "Chat - Get Conversation",
            "GET",
            f"chat/{self.signal_id}",
            200
        )
        return success, response

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: NOTIFICATIONS TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_notifications_list(self):
        """Test listing notifications"""
        success, response = self.run_test(
            "Notifications - List",
            "GET",
            "notifications",
            200
        )
        if success and 'notifications' in response:
            self.log("📊", f"Found {len(response['notifications'])} notifications, {response.get('unread_count', 0)} unread")
        return success, response
    
    def test_notifications_mark_read(self):
        """Test marking all notifications as read"""
        success, response = self.run_test(
            "Notifications - Mark All Read",
            "POST",
            "notifications/mark-read",
            200
        )
        return success, response

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: STRATEGY PRESETS TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_presets_create(self):
        """Test creating a strategy preset"""
        success, response = self.run_test(
            "Presets - Create",
            "POST",
            "presets",
            200,
            data={
                "name": "SMA-fast",
                "strategy": "sma_crossover",
                "interval": "1h",
                "limit": 300,
                "initial_cash": 10000,
                "fee_rate": 0.001,
                "fast": 10,
                "slow": 30
            }
        )
        if success and 'id' in response:
            self.preset_id = response['id']
            self.log("📊", f"Created preset with ID: {self.preset_id}")
        return success, response
    
    def test_presets_list(self):
        """Test listing presets"""
        success, response = self.run_test(
            "Presets - List",
            "GET",
            "presets",
            200
        )
        if success and 'presets' in response:
            self.log("📊", f"Found {len(response['presets'])} presets")
        return success, response
    
    def test_presets_update(self):
        """Test updating a preset"""
        if not hasattr(self, 'preset_id') or not self.preset_id:
            self.log("⚠️", "Skipping preset update - no preset_id available")
            return False, {}
        
        success, response = self.run_test(
            "Presets - Update",
            "PATCH",
            f"presets/{self.preset_id}",
            200,
            data={"name": "SMA-fast-updated", "fast": 12}
        )
        return success, response
    
    def test_presets_delete(self):
        """Test deleting a preset"""
        if not hasattr(self, 'preset_id') or not self.preset_id:
            self.log("⚠️", "Skipping preset delete - no preset_id available")
            return False, {}
        
        success, response = self.run_test(
            "Presets - Delete",
            "DELETE",
            f"presets/{self.preset_id}",
            200
        )
        return success, response

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: AI BOTS TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_bots_create(self):
        """Test creating an AI bot"""
        success, response = self.run_test(
            "Bots - Create",
            "POST",
            "bots",
            200,
            data={
                "name": "Test bot",
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "model": "claude",
                "interval_minutes": 60,
                "size_usd": 100,
                "min_confidence": 0.6,
                "allow_actions": ["BUY", "SELL"],
                "active": False,
                "use_testnet": False
            }
        )
        if success and 'id' in response:
            self.bot_id = response['id']
            self.log("📊", f"Created bot with ID: {self.bot_id}")
        return success, response
    
    def test_bots_list(self):
        """Test listing bots"""
        success, response = self.run_test(
            "Bots - List",
            "GET",
            "bots",
            200
        )
        if success and 'bots' in response:
            self.log("📊", f"Found {len(response['bots'])} bots")
        return success, response
    
    def test_bots_manual_run(self):
        """Test manual bot run"""
        if not hasattr(self, 'bot_id') or not self.bot_id:
            self.log("⚠️", "Skipping bot run - no bot_id available")
            return False, {}
        
        self.log("⏳", "Running bot (this may take 10-15 seconds for AI call)...")
        success, response = self.run_test(
            "Bots - Manual Run",
            "POST",
            f"bots/{self.bot_id}/run",
            200
        )
        if success:
            status = response.get('status', 'unknown')
            self.log("📊", f"Bot run status: {status}")
            if status == 'skipped':
                self.log("📊", f"Skip reason: {response.get('skip_reason', 'N/A')}")
        return success, response
    
    def test_bots_run_history(self):
        """Test getting bot run history"""
        if not hasattr(self, 'bot_id') or not self.bot_id:
            self.log("⚠️", "Skipping bot history - no bot_id available")
            return False, {}
        
        success, response = self.run_test(
            "Bots - Run History",
            "GET",
            f"bots/{self.bot_id}/runs",
            200
        )
        if success and 'runs' in response:
            self.log("📊", f"Found {len(response['runs'])} bot runs")
        return success, response
    
    def test_bots_update(self):
        """Test updating a bot (toggle active)"""
        if not hasattr(self, 'bot_id') or not self.bot_id:
            self.log("⚠️", "Skipping bot update - no bot_id available")
            return False, {}
        
        success, response = self.run_test(
            "Bots - Update (toggle active)",
            "PATCH",
            f"bots/{self.bot_id}",
            200,
            data={"active": True}
        )
        return success, response
    
    def test_bots_delete(self):
        """Test deleting a bot"""
        if not hasattr(self, 'bot_id') or not self.bot_id:
            self.log("⚠️", "Skipping bot delete - no bot_id available")
            return False, {}
        
        success, response = self.run_test(
            "Bots - Delete",
            "DELETE",
            f"bots/{self.bot_id}",
            200
        )
        return success, response

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: BINANCE TESTNET SETTINGS TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_settings_binance_testnet_save(self):
        """Test saving Binance testnet keys"""
        success, response = self.run_test(
            "Settings - Save Binance Testnet Keys",
            "POST",
            "settings/exchange/binance-testnet",
            200,
            data={
                "api_key": "dummy_test_key_12345678",
                "api_secret": "dummy_test_secret_12345678",
                "enabled": True
            }
        )
        return success, response
    
    def test_settings_binance_testnet_test(self):
        """Test Binance testnet connection (expect geo_restricted)"""
        self.log("⏳", "Testing testnet connection (expect geo_restricted status)...")
        success, response = self.run_test(
            "Settings - Test Binance Testnet Connection",
            "POST",
            "settings/exchange/binance-testnet/test",
            200
        )
        if success:
            status = response.get('status', 'unknown')
            self.log("📊", f"Testnet status: {status}")
            if status == 'geo_restricted':
                self.log("✅", "Geo-restriction detected as expected")
            elif status == 'error':
                self.log("📊", f"Error: {response.get('error', 'N/A')}")
        return success, response
    
    def test_paper_order_testnet_flag(self):
        """Test paper order with testnet flag (expect 503 geo-restricted)"""
        self.log("⏳", "Testing paper order with testnet flag (expect 503)...")
        # This should return 503 because testnet is geo-restricted
        success, response = self.run_test(
            "Paper - Order with Testnet Flag",
            "POST",
            "paper/order",
            503,  # Expect 503 due to geo-restriction
            data={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quote_amount": 50,
                "use_testnet": True
            }
        )
        return success, response

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN TEST RUNNER
    # ═══════════════════════════════════════════════════════════════════════

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("🚀", "=" * 70)
        self.log("🚀", "SignalForge Backend API Test Suite")
        self.log("🚀", "=" * 70)
        
        # Health & Auth
        self.log("\n📋", "=== HEALTH & AUTH TESTS ===")
        self.test_health()
        self.test_signup()
        self.test_signup_duplicate()
        self.test_login()
        self.test_login_wrong_password()
        self.test_me_authenticated()
        self.test_me_unauthenticated()
        
        # Market Data
        self.log("\n📋", "=== MARKET DATA TESTS ===")
        self.test_market_overview()
        self.test_market_coin_detail()
        self.test_market_klines()
        self.test_market_movers_gainers()
        self.test_market_movers_losers()
        
        # AI Signals (these take longer)
        self.log("\n📋", "=== AI SIGNAL TESTS ===")
        self.test_ai_signal_claude()
        self.test_ai_signal_gemini()
        self.test_ai_signal_both()
        self.test_ai_history()
        
        # Backtest
        self.log("\n📋", "=== BACKTEST TESTS ===")
        self.test_backtest_sma()
        self.test_backtest_rsi()
        self.test_backtest_macd()
        
        # Paper Trading
        self.log("\n📋", "=== PAPER TRADING TESTS ===")
        self.test_paper_portfolio_fresh()
        self.test_paper_order_buy()
        self.test_paper_portfolio_after_buy()
        self.test_paper_order_sell()
        self.test_paper_order_insufficient_cash()
        self.test_paper_trades()
        self.test_paper_reset()
        
        # Watchlists
        self.log("\n📋", "=== WATCHLIST TESTS ===")
        self.test_watchlist_create()
        self.test_watchlist_list()
        self.test_watchlist_update()
        self.test_watchlist_delete()
        
        # Alerts
        self.log("\n📋", "=== ALERT TESTS ===")
        self.test_alert_create()
        self.test_alert_list()
        self.test_alert_check()
        self.test_alert_delete()
        
        # Settings
        self.log("\n📋", "=== SETTINGS TESTS ===")
        self.test_settings_binance_save()
        self.test_settings_binance_get()
        self.test_settings_binance_delete()
        
        # Phase 3: Chat Analyst
        self.log("\n📋", "=== PHASE 3: CHAT ANALYST TESTS ===")
        self.test_chat_send_message()
        self.test_chat_get_conversation()
        
        # Phase 3: Notifications
        self.log("\n📋", "=== PHASE 3: NOTIFICATIONS TESTS ===")
        self.test_notifications_list()
        self.test_notifications_mark_read()
        
        # Phase 3: Strategy Presets
        self.log("\n📋", "=== PHASE 3: STRATEGY PRESETS TESTS ===")
        self.test_presets_create()
        self.test_presets_list()
        self.test_presets_update()
        self.test_presets_delete()
        
        # Phase 3: AI Bots
        self.log("\n📋", "=== PHASE 3: AI BOTS TESTS ===")
        self.test_bots_create()
        self.test_bots_list()
        self.test_bots_manual_run()
        self.test_bots_run_history()
        self.test_bots_update()
        self.test_bots_delete()
        
        # Phase 3: Binance Testnet
        self.log("\n📋", "=== PHASE 3: BINANCE TESTNET TESTS ===")
        self.test_settings_binance_testnet_save()
        self.test_settings_binance_testnet_test()
        self.test_paper_order_testnet_flag()
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 70, "")
        self.log("📊", "TEST SUMMARY")
        self.log("=" * 70, "")
        self.log("✅", f"Tests Passed: {self.tests_passed}/{self.tests_run}")
        self.log("❌", f"Tests Failed: {len(self.failed_tests)}/{self.tests_run}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log("📈", f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌", "FAILED TESTS:")
            for fail in self.failed_tests:
                self.log("  ❌", f"{fail.get('test', 'Unknown')} - {fail.get('endpoint', '')}")
                if 'error' in fail:
                    self.log("     ", f"Error: {fail['error']}")
                else:
                    self.log("     ", f"Expected {fail.get('expected')}, got {fail.get('actual')}")
        
        self.log("\n" + "=" * 70, "")
        
        return 0 if len(self.failed_tests) == 0 else 1


def main():
    tester = APITester()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
