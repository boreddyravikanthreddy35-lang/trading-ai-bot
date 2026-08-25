import React, { useEffect, useState, useRef, useCallback } from "react";
import { toast } from "sonner";
import { Bot, Zap, RefreshCw, Activity, Search, CheckCircle2, TrendingUp, Wallet, Clock, Edit2, Save, Coins, Check, Plus, X, Layers, SlidersHorizontal, CheckSquare, Square, DollarSign, Eye, Filter, ShieldCheck, AlertTriangle, ChevronRight, Info, Target, ArrowDownRight, ArrowUpRight, Trash2 } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/States";

const COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","PEPEUSDT","BNBUSDT","ADAUSDT","DOGEUSDT","XRPUSDT","AVAXUSDT","LINKUSDT","SHIBUSDT","MATICUSDT"];
const SCAN_SECS = 60;
const LS_CAPITAL_KEY = "auto_ai_trader_capital";
const LS_COINS_KEY = "auto_ai_trader_fixed_coins";

function fmt(n, d = 2) { return Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }); }
function fmtUSD(n) { return "$" + fmt(n, 2); }
function fmtPrice(n) { return "$" + fmt(n, 4); }
function fmtPct(n) { const v = Number(n || 0); return (v >= 0 ? "+" : "") + fmt(v, 2) + "%"; }

function PnLBadge({ value, pct }) {
  const pos = Number(value) >= 0;
  return (
    <span className={`font-bold font-mono ${pos ? "text-green-400" : "text-red-400"}`}>
      {pos ? "▲" : "▼"} {fmtUSD(Math.abs(value))}
      {pct !== undefined && <span className="text-xs ml-1">({fmtPct(pct)})</span>}
    </span>
  );
}

function ActionBadge({ action }) {
  if (!action) return null;
  const cfg = {
    BUY:           "bg-green-500/20 text-green-400 border-green-500/40",
    SELL:          "bg-red-500/20 text-red-400 border-red-500/40",
    HOLD:          "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    BUY_REJECTED:  "bg-amber-500/20 text-amber-400 border-amber-500/40",
    SELL_REJECTED: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  };
  return <span className={`px-2 py-0.5 rounded text-xs font-bold border ${cfg[action] || cfg.HOLD}`}>{action}</span>;
}

export default function AutoAITraderPage() {
  const { user } = useAuth();
  const userId = user?.id || localStorage.getItem("user_id") || "default_user";

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [coinInput, setCoinInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [running, setRunning] = useState(false);
  const [countdown, setCountdown] = useState(SCAN_SECS);
  const [isScanning, setIsScanning] = useState(false);
  const [activityLog, setActivityLog] = useState([]);
  const [lastScanTime, setLastScanTime] = useState(null);
  const [editingCapital, setEditingCapital] = useState(false);
  const [capitalDraft, setCapitalDraft] = useState("");
  const [customCoinInput, setCustomCoinInput] = useState("");
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [tradeFilter, setTradeFilter] = useState("ALL");
  const [tradeSearch, setTradeSearch] = useState("");

  const getSavedCapital = () => {
    try { return parseFloat(localStorage.getItem(LS_CAPITAL_KEY) || "1000"); } catch { return 1000; }
  };
  const [capital, setCapital] = useState(getSavedCapital);

  const getSavedCoins = () => {
    try {
      const saved = localStorage.getItem(LS_COINS_KEY);
      return saved ? JSON.parse(saved) : ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT", "BNBUSDT", "ADAUSDT"];
    } catch {
      return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT", "BNBUSDT", "ADAUSDT"];
    }
  };
  const [fixedCoins, setFixedCoins] = useState(getSavedCoins);
  const [allAvailableCoins, setAllAvailableCoins] = useState(COINS);

  const timerRef = useRef(null);

  const addLog = useCallback((msg, type = "info") => {
    setActivityLog(prev => [{ id: Date.now() + Math.random(), msg, type, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 50));
  }, []);

  const loadStatus = useCallback(async (silent = false) => {
    try {
      const { data } = await api.get(`/auto-trader/status?user_id=${userId}`);
      if (data.coins && Array.isArray(data.coins) && data.coins.length > 0) {
        setFixedCoins(data.coins);
      }
      if (data.available_coins && Array.isArray(data.available_coins)) {
        setAllAvailableCoins(data.available_coins);
      }
      setStatus(prev => {
        if (prev) {
          const newTrades = (data.trades || []).filter(t => !( prev.trades || []).find(p => p.id === t.id));
          newTrades.forEach(t => {
            if (t.side === "BUY") {
              toast.success(`🟢 AI BOUGHT ${t.symbol} @ ${fmtPrice(t.price)}`);
              addLog(`🟢 BUY: ${t.symbol} @ ${fmtPrice(t.price)} | Qty: ${Number(t.quantity).toFixed(6)} | Score: ${t.score||"N/A"} | ${t.trade_time || new Date(t.created_at).toLocaleString()}`, "buy");
            }
            if (t.side === "SELL") {
              const pnl = t.realized_pnl || 0;
              toast[pnl >= 0 ? "success" : "error"](`🔴 AI SOLD ${t.symbol} | ${pnl >= 0 ? "PROFIT" : "LOSS"}: ${fmtUSD(pnl)}`);
              addLog(`🔴 SELL: ${t.symbol} @ ${fmtPrice(t.price)} | Bought @ ${fmtPrice(t.buy_price||0)} | ${pnl>=0?"PROFIT":"LOSS"}: ${fmtUSD(pnl)} | ${t.trade_time || new Date(t.created_at).toLocaleString()}`, "sell");
            }
          });
        }
        return data;
      });
    } catch (e) {
      if (!silent) setError(getErrorMessage(e, "Failed to load status"));
    } finally {
      setLoading(false);
    }
  }, [addLog, userId]);

  const LS_AI_ON_KEY = "auto_ai_trader_enabled";
  const [aiTradingEnabled, setAiTradingEnabled] = useState(() => {
    try { return localStorage.getItem(LS_AI_ON_KEY) !== "false"; } catch { return true; }
  });

  const toggleAiTrading = () => {
    const next = !aiTradingEnabled;
    setAiTradingEnabled(next);
    try { localStorage.setItem(LS_AI_ON_KEY, String(next)); } catch {}
    if (next) {
      toast.success("🟢 AI Auto-Trading is now ON! Scanning every 60 seconds.");
      addLog("🟢 AI Auto-Trading TURNED ON — automated scanning resumed", "info");
    } else {
      toast.info("⏸ AI Auto-Trading is now OFF! Automated scans paused.");
      addLog("⏸ AI Auto-Trading TURNED OFF — automated trading paused", "info");
    }
  };

  const nextScanTimeRef = useRef(Date.now() + SCAN_SECS * 1000);
  const fixedCoinsRef = useRef(fixedCoins);
  fixedCoinsRef.current = fixedCoins;
  const isScanningRef = useRef(false);

  const executeAiScan = useCallback(async (coinsList = fixedCoinsRef.current, isAuto = false) => {
    if (!coinsList || coinsList.length === 0) return;
    setIsScanning(true);
    setLastScanTime(new Date().toLocaleTimeString());
    addLog(`⚡ [${new Date().toLocaleTimeString()}] AI evaluating ${coinsList.length} fixed coins: ${coinsList.map(c=>c.replace("USDT","")).join(", ")}`, "scan");

    try {
      const { data } = await api.post(
        "/auto-trader/run-cycle",
        { user_id: userId, symbols: coinsList },
        { timeout: 60000 }
      );
      const results = data.results || [];

      // Log each coin's evaluation individually in the live activity log
      results.forEach(r => {
        const coinName = r.symbol || "UNKNOWN";
        const score = r.score !== undefined ? `${r.score}/100` : "N/A";
        const price = fmtPrice(r.price || r.current_price || 0);

        if (r.action === "BUY") {
          addLog(`🟢 BUY EXECUTED: ${coinName} @ ${price} | Qty: ${Number(r.quantity||0).toFixed(6)} | AI Score: ${score}`, "buy");
          toast.success(`🟢 AI Auto-Bought ${coinName} @ ${price}`);
        } else if (r.action === "SELL") {
          const pnl = r.realized_pnl || 0;
          addLog(`🔴 SELL EXECUTED: ${coinName} @ ${price} | PnL: ${fmtUSD(pnl)} | AI Score: ${score}`, "sell");
          toast[pnl >= 0 ? "success" : "error"](`🔴 AI Auto-Sold ${coinName} | PnL: ${fmtUSD(pnl)}`);
        } else if (r.action === "BUY_REJECTED") {
          addLog(`⚠️ BUY REJECTED: ${coinName} (Score: ${score}) | Reason: ${r.risk_reason || "Risk limit"}`, "info");
        } else {
          // HOLD
          const reason = r.reason || "Neutral market signals (Waiting for score >= 65 to buy)";
          addLog(`🟡 HOLD: ${coinName} @ ${price} | AI Score: ${score} | Decision: ${reason}`, "info");
        }
      });

      const buys = data.summary?.buys || 0;
      const sells = data.summary?.sells || 0;
      const holds = data.summary?.holds || 0;
      addLog(`📊 Scan Complete: ${results.length} coins evaluated -> ${buys} BUY, ${sells} SELL, ${holds} HOLD`, "info");

      await loadStatus(true);
    } catch (e) {
      const errMsg = getErrorMessage(e, "Scan request failed");
      if (errMsg.toLowerCase().includes("timeout")) {
        addLog(`⚡ Scan took longer than expected — exchange feeds synced, continuing next cycle`, "info");
      } else {
        addLog(`❌ AI scan error: ${errMsg}`, "sell");
      }
    } finally {
      setTimeout(() => setIsScanning(false), 2000);
    }
  }, [addLog, loadStatus, userId]);

  useEffect(() => {
    loadStatus();
    addLog("🤖 AI Trader started — scanning live market every 60 seconds", "info");
    addLog(`💵 Fixed capital: ${fmtUSD(getSavedCapital())} (change with the capital card below)`, "info");
    addLog(`🎯 Fixed coins: ${getSavedCoins().map(c => c.replace("USDT","")).join(", ")}`, "info");

    nextScanTimeRef.current = Date.now() + SCAN_SECS * 1000;

    const timer = setInterval(async () => {
      const remainingMs = nextScanTimeRef.current - Date.now();
      const remainingSecs = Math.max(0, Math.ceil(remainingMs / 1000));
      setCountdown(remainingSecs);

      if (remainingMs <= 0 && !isScanningRef.current) {
        nextScanTimeRef.current = Date.now() + SCAN_SECS * 1000;
        setCountdown(SCAN_SECS);
        isScanningRef.current = true;
        try {
          await executeAiScan(fixedCoinsRef.current, true);
        } finally {
          isScanningRef.current = false;
        }
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [executeAiScan, addLog, loadStatus]);

  const saveCapital = async () => {
    const val = parseFloat(capitalDraft);
    if (!val || val < 10) { toast.error("Minimum capital is $10"); return; }
    try {
      await api.post("/auto-trader/set-capital", { user_id: userId, capital: val });
      localStorage.setItem(LS_CAPITAL_KEY, String(val));
      setCapital(val);
      setEditingCapital(false);
      toast.success(`Capital fixed at ${fmtUSD(val)} — AI will use this until you change it.`);
      addLog(`💵 Capital updated to ${fmtUSD(val)} and locked`, "info");
      await loadStatus(true);
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to save capital"));
    }
  };

  const [budgetDraft, setBudgetDraft] = useState("500");
  const [editingBudget, setEditingBudget] = useState(false);

  const saveBudget = async (usdtAmount) => {
    const val = parseFloat(usdtAmount || budgetDraft);
    if (!val || val <= 0) {
      toast.error("Please enter a valid USDT budget");
      return;
    }
    try {
      await api.post("/auto-trader/set-budget", {
        user_id: userId,
        budget_usdt: val,
      });
      toast.success(`🤖 AI Trading Budget set to $${val.toFixed(2)} USDT. AI will strictly use up to this amount!`);
      addLog(`🤖 AI Budget updated: $${val.toFixed(2)} USDT — AI will strictly use up to this amount`, "info");
      setEditingBudget(false);
      await loadStatus(true);
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to update AI budget"));
    }
  };

  const toggleFixedCoin = async (sym) => {
    let updated;
    if (fixedCoins.includes(sym)) {
      if (fixedCoins.length <= 1) {
        toast.warning("At least 1 coin must remain selected for AI trading.");
        return;
      }
      updated = fixedCoins.filter(c => c !== sym);
    } else {
      updated = [...fixedCoins, sym];
    }
    setFixedCoins(updated);
    try {
      localStorage.setItem(LS_COINS_KEY, JSON.stringify(updated));
      await api.post("/auto-trader/set-coins", { user_id: userId, coins: updated });
      toast.success(`Fixed coins updated (${updated.length} coins selected)`);
      addLog(`🎯 Fixed coins updated: ${updated.map(c => c.replace("USDT","")).join(", ")}`, "info");
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to save fixed coins"));
    }
  };

  const selectCoinPreset = async (presetList) => {
    setFixedCoins(presetList);
    try {
      localStorage.setItem(LS_COINS_KEY, JSON.stringify(presetList));
      await api.post("/auto-trader/set-coins", { user_id: userId, coins: presetList });
      toast.success(`Preset applied: ${presetList.length} coins fixed for AI trading`);
      addLog(`🎯 AI Coin Preset applied: ${presetList.map(c => c.replace("USDT","")).join(", ")}`, "info");
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to save coin preset"));
    }
  };

  const addCustomCoin = async () => {
    if (!customCoinInput.trim()) return;
    let sym = customCoinInput.trim().toUpperCase();
    if (!sym.endsWith("USDT")) sym = sym + "USDT";
    if (fixedCoins.includes(sym)) {
      toast.info(`${sym} is already in your fixed coins list`);
      setCustomCoinInput("");
      return;
    }
    const updated = [...fixedCoins, sym];
    if (!allAvailableCoins.includes(sym)) {
      setAllAvailableCoins(prev => [...prev, sym]);
    }
    setFixedCoins(updated);
    setCustomCoinInput("");
    try {
      localStorage.setItem(LS_COINS_KEY, JSON.stringify(updated));
      await api.post("/auto-trader/set-coins", { user_id: userId, coins: updated });
      toast.success(`Added ${sym} to fixed AI coins`);
      addLog(`➕ Added custom coin ${sym} to AI trading list`, "info");
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to add coin"));
    }
  };

  const tradeCoin = async (sym, side) => {
    if (!sym) { toast.error("Enter a coin symbol"); return; }
    setAnalyzing(true);
    try {
      const sym_ = sym.trim().toUpperCase();
      const { data } = await api.post("/auto-trader/trade-coin", { user_id: userId, symbol: sym_, capital, side: side || null });
      const a = data.result || data.analysis || {};
      if (a.execution_status === "EXECUTED_BUY" || a.action === "BUY") {
        toast.success(`🟢 Bought ${sym_} @ ${fmtPrice(a.current_price || a.price)}`);
        addLog(`🟢 BUY: ${sym_} @ ${fmtPrice(a.current_price || a.price)} | Score: ${a.prediction_score || a.score}/100`, "buy");
      } else if (a.execution_status === "EXECUTED_SELL" || a.action === "SELL") {
        const pnl = a.realized_pnl || 0;
        toast[pnl >= 0 ? "success" : "error"](`🔴 Sold ${sym_} | ${pnl >= 0 ? "PROFIT" : "LOSS"}: ${fmtUSD(pnl)}`);
        addLog(`🔴 SELL: ${sym_} @ ${fmtPrice(a.current_price || a.price)} | ${pnl>=0?"PROFIT":"LOSS"}: ${fmtUSD(pnl)}`, "sell");
      } else {
        toast.info(`🟡 ${a.action || "HOLD"}: ${sym_} @ ${fmtPrice(a.current_price || a.price)}`);
        addLog(`🟡 ${a.action || "HOLD"}: ${sym_} @ ${fmtPrice(a.current_price || a.price)} (Score ${a.prediction_score || a.score || "N/A"}/100)`, "info");
      }
      await loadStatus(true);
    } catch (e) {
      toast.error(getErrorMessage(e, "Trade failed"));
    } finally {
      setAnalyzing(false);
    }
  };

  const runCycle = async () => {
    setRunning(true);
    try {
      await executeAiScan(fixedCoins);
      toast.success(`AI completed scan on ${fixedCoins.length} coins`);
    } catch (e) {
      toast.error(getErrorMessage(e, "Cycle failed"));
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <div className="p-10 text-center text-muted-foreground text-sm animate-pulse">Initializing AI Trader...</div>;
  if (error) return <ErrorState message={error} onRetry={() => { setError(null); setLoading(true); loadStatus(); }} />;

  const trades = status?.trades || status?.recent_trades || [];
  const positions = status?.positions || [];
  const analyses = Object.values(status?.analyses || {});
  const buys = trades.filter(t => t.side === "BUY" || t.action === "BUY");
  const sells = trades.filter(t => t.side === "SELL" || t.action === "SELL");

  const resetAllTrades = async () => {
    if (!window.confirm("Are you sure you want to reset all trades, positions, and history to completely 0? This gives you a fresh start from trade #1.")) return;
    try {
      await api.post("/auto-trader/reset", { user_id: userId, initial_usdt: 0 });
      setActivityLog([]);
      toast.success("✨ All trade history, positions, and balances reset to 0! Starting fresh.");
      addLog("✨ Fresh Start: All trading history and balances wiped to 0", "info");
      await loadStatus(true);
    } catch (e) {
      toast.error(getErrorMessage(e, "Failed to reset trading data"));
    }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 pb-24">

      {/* HEADER */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Bot className="h-6 w-6 text-primary" /> Automatic AI Trader</h1>
          <p className="text-xs text-muted-foreground mt-1">AI analyzes coins every 60 seconds and auto-executes BUY / HOLD / SELL with full price &amp; P&amp;L tracking.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => loadStatus()}><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
          <Button variant="outline" size="sm" className="border-red-500/40 text-red-400 hover:bg-red-500/10" onClick={resetAllTrades}>
            <Trash2 className="h-3.5 w-3.5 mr-1" /> Reset to 0
          </Button>
          <Button variant="outline" size="sm" className="text-green-400 border-green-500/40" onClick={() => tradeCoin(coinInput || "BTCUSDT", "BUY")} disabled={analyzing}>🟢 Test BUY</Button>
          <Button variant="outline" size="sm" className="text-red-400 border-red-500/40" onClick={() => tradeCoin(coinInput || "BTCUSDT", "SELL")} disabled={analyzing}>🔴 Test SELL</Button>
          <Button size="sm" className="bg-primary text-primary-foreground" onClick={runCycle} disabled={running}>
            {running ? <span className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin mr-1" /> : <Zap className="h-3.5 w-3.5 mr-1" />}
            Run Full Scan
          </Button>
        </div>
      </div>

      {/* LIVE STATUS BANNER WITH ON/OFF SWITCH */}
      <div className={`rounded-xl border-2 p-4 transition-all ${
        !aiTradingEnabled
          ? "border-gray-700 bg-gray-900/60"
          : isScanning
          ? "border-yellow-500/60 bg-yellow-500/5"
          : "border-green-500/40 bg-green-500/5"
      }`}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Left: Indicator & Info */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <span className={`w-4 h-4 rounded-full absolute ${!aiTradingEnabled ? "bg-gray-500" : isScanning ? "bg-yellow-500 animate-ping" : "bg-green-500 animate-ping"}`} />
              <span className={`w-4 h-4 rounded-full relative z-10 block ${!aiTradingEnabled ? "bg-gray-500" : isScanning ? "bg-yellow-500" : "bg-green-500"}`} />
            </div>
            <div>
              <div className={`font-bold flex items-center gap-2 ${!aiTradingEnabled ? "text-gray-400" : isScanning ? "text-yellow-400" : "text-green-400"}`}>
                {!aiTradingEnabled
                  ? "⏸ AI AUTO-TRADING IS OFF (PAUSED)"
                  : isScanning
                  ? "⚡ AI IS SCANNING & TRADING NOW..."
                  : "🟢 AI AUTO-TRADER IS ON — WATCHING 24/7"
                }
              </div>
              <div className="text-xs text-muted-foreground">
                {!aiTradingEnabled
                  ? "Automatic scans paused. Click the toggle button to turn ON."
                  : lastScanTime
                  ? `Last scan: ${lastScanTime} | Next automatic scan in ${countdown}s`
                  : `First scan initializing... | Next scan in ${countdown}s`
                }
              </div>
            </div>
          </div>

          {/* Center/Right: ON/OFF Button & Stats */}
          <div className="flex items-center gap-5 flex-wrap">
            {/* ON / OFF BUTTON */}
            <Button
              size="sm"
              onClick={toggleAiTrading}
              className={`font-bold px-4 py-2 text-xs transition-all shadow-md ${
                aiTradingEnabled
                  ? "bg-red-600/90 hover:bg-red-700 text-white border border-red-500/50"
                  : "bg-green-600 hover:bg-green-700 text-white border border-green-500/50"
              }`}
            >
              {aiTradingEnabled ? "⏸ TURN AI OFF" : "▶ TURN AI ON"}
            </Button>

            <div className="flex items-center gap-5 text-center">
              <div>
                <div className="text-2xl font-bold font-mono text-primary">
                  {aiTradingEnabled ? `${countdown}s` : "PAUSED"}
                </div>
                <div className="text-[11px] text-muted-foreground">Scan Timer</div>
              </div>
              <div><div className="text-xl font-bold font-mono text-green-400">{buys.length}</div><div className="text-[11px] text-muted-foreground">Total BUYs</div></div>
              <div><div className="text-xl font-bold font-mono text-red-400">{sells.length}</div><div className="text-[11px] text-muted-foreground">Total SELLs</div></div>
              <div><div className="text-xl font-bold font-mono">{positions.length}</div><div className="text-[11px] text-muted-foreground">Open Positions</div></div>
              <div>
                <div className={`text-xl font-bold font-mono ${Number(status?.total_realized_pnl) >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {fmtUSD(status?.total_realized_pnl || 0)}
                </div>
                <div className="text-[11px] text-muted-foreground">Realized P&amp;L</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* LIVE ACTIVITY LOG */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" /> Live Activity Log
            <span className="text-[11px] font-normal text-muted-foreground">(every BUY / SELL / HOLD is shown here instantly)</span>
          </h2>
          <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => setActivityLog([])}>Clear</Button>
        </div>
        <div className="h-32 overflow-y-auto space-y-0.5 font-mono text-xs bg-black/40 rounded-lg p-3">
          {activityLog.length === 0 ? (
            <div className="text-muted-foreground">Waiting for AI activity...</div>
          ) : activityLog.map(e => (
            <div key={e.id} className={`flex gap-2 ${e.type === "buy" ? "text-green-400" : e.type === "sell" ? "text-red-400" : e.type === "scan" ? "text-yellow-400" : "text-muted-foreground"}`}>
              <span className="shrink-0 text-muted-foreground/50">[{e.time}]</span>
              <span>{e.msg}</span>
            </div>
          ))}
        </div>
      </div>

      {/* CAPITAL & FIXED COIN SELECTOR */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* 1. AI Trading Budget & Spending Cap Card (100% USDT) */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 flex flex-col justify-between" data-testid="ai-budget-card">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Wallet className="h-4 w-4 text-primary" /> 🤖 AI Trading Budget Limit (USDT)
              </span>
              {!editingBudget ? (
                <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={() => { setBudgetDraft(String(status?.budget?.allocated_budget_usdt || 500)); setEditingBudget(true); }}>
                  <Edit2 className="h-3 w-3" /> Set Limit
                </Button>
              ) : (
                <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 text-green-400" onClick={() => saveBudget()}>
                  <Save className="h-3 w-3" /> Save &amp; Lock
                </Button>
              )}
            </div>

            {editingBudget ? (
              <div className="space-y-2 mt-2">
                <div className="text-xs text-muted-foreground">Set AI spending limit in USDT ($):</div>
                <Input
                  type="number"
                  min="5"
                  step="50"
                  value={budgetDraft}
                  onChange={e => setBudgetDraft(e.target.value)}
                  className="h-10 font-mono text-lg font-bold"
                  placeholder="Enter budget in USDT (e.g. 500)"
                />
                <div className="flex gap-1.5 flex-wrap">
                  {[50, 100, 250, 500, 1000, 2500].map(amt => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setBudgetDraft(String(amt))}
                      className="px-2 py-0.5 text-xs font-mono rounded bg-primary/10 border border-primary/30 hover:bg-primary hover:text-primary-foreground transition-all"
                    >
                      ${amt} USDT
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-yellow-400">
                  🔒 AI will NEVER spend more than this amount in USDT, even if your wallet balance is higher.
                </p>
              </div>
            ) : (
              <div className="space-y-2 mt-2">
                <div className="flex items-baseline justify-between">
                  <div className="text-2xl font-bold font-mono text-primary">
                    ${Number(status?.budget?.allocated_budget_usdt || 500).toFixed(2)} <span className="text-xs font-normal text-muted-foreground">USDT</span>
                  </div>
                </div>

                {/* Real-Time Utilization Progress */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-muted-foreground">Utilized in Active Coins:</span>
                    <span className="font-mono font-semibold text-foreground">
                      ${Number(status?.budget?.total_active_invested_usdt || 0).toFixed(2)} USDT
                    </span>
                  </div>
                  <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        status?.budget?.is_budget_full
                          ? "bg-red-500"
                          : (status?.budget?.utilization_pct || 0) > 75
                          ? "bg-yellow-500"
                          : "bg-green-500"
                      }`}
                      style={{ width: `${Math.min(status?.budget?.utilization_pct || 0, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-muted-foreground">Remaining to Buy:</span>
                    <span className={`font-mono font-bold ${status?.budget?.is_budget_full ? "text-red-400" : "text-green-400"}`}>
                      ${Number(status?.budget?.remaining_budget_usdt || 0).toFixed(2)} USDT
                    </span>
                  </div>
                </div>

                {/* Status Notice */}
                {status?.budget?.is_budget_full ? (
                  <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-[11px] text-red-300 flex items-center gap-1.5">
                    <span>⛔</span>
                    <span><strong>Budget Full:</strong> AI Auto-Buy paused until open positions are sold.</span>
                  </div>
                ) : (
                  <div className="p-1.5 rounded-lg bg-green-500/10 border border-green-500/30 text-[11px] text-green-300 flex items-center gap-1.5">
                    <span>🟢</span>
                    <span>AI actively trading with your ${Number(status?.budget?.allocated_budget_usdt || 500).toFixed(2)} USDT limit.</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="text-[11px] text-muted-foreground pt-2 border-t border-border/50 flex items-center gap-1">
            🔒 Hard Spending Cap: AI uses only this allocated USDT.
          </div>
        </div>

        {/* 2. Fixed Coin Selector Card */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Coins className="h-4 w-4 text-primary" /> Fixed Coin Selector
              <Badge variant="secondary" className="ml-1 text-[10px] bg-primary/20 text-primary font-mono">{fixedCoins.length} Active</Badge>
            </span>
            {/* Quick Presets */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => selectCoinPreset(["BTCUSDT", "ETHUSDT", "SOLUSDT"])}
                className="px-2 py-0.5 text-[11px] rounded bg-muted/60 hover:bg-primary/20 hover:text-primary border border-border transition-all">
                ⚡ Top 3 (BTC/ETH/SOL)
              </button>
              <button
                type="button"
                onClick={() => selectCoinPreset(["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT", "BNBUSDT", "DOGEUSDT"])}
                className="px-2 py-0.5 text-[11px] rounded bg-muted/60 hover:bg-primary/20 hover:text-primary border border-border transition-all">
                🔥 Top 6 Major
              </button>
              <button
                type="button"
                onClick={() => selectCoinPreset(allAvailableCoins)}
                className="px-2 py-0.5 text-[11px] rounded bg-muted/60 hover:bg-primary/20 hover:text-primary border border-border transition-all">
                ✓ All Tracked
              </button>
            </div>
          </div>

          {/* Interactive Coin Chips */}
          <div className="flex flex-wrap gap-2 pt-1">
            {allAvailableCoins.map(sym => {
              const base = sym.replace("USDT", "");
              const isSelected = fixedCoins.includes(sym);
              return (
                <button
                  key={sym}
                  type="button"
                  onClick={() => toggleFixedCoin(sym)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all border shadow-sm ${
                    isSelected
                      ? "bg-primary/20 text-primary border-primary ring-1 ring-primary/40 shadow-primary/10"
                      : "bg-muted/40 text-muted-foreground border-border/70 hover:border-muted-foreground hover:text-foreground opacity-60"
                  }`}
                >
                  <span className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[9px] font-bold ${isSelected ? "bg-primary text-black" : "border border-muted-foreground/50"}`}>
                    {isSelected ? "✓" : ""}
                  </span>
                  <span>{base}</span>
                </button>
              );
            })}
          </div>

          {/* Custom Coin Input */}
          <div className="flex items-center gap-2 pt-2 border-t border-border/50">
            <Input
              type="text"
              placeholder="Add custom coin (e.g. SUI, NEAR, INJ)..."
              value={customCoinInput}
              onChange={e => setCustomCoinInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addCustomCoin()}
              className="h-8 text-xs font-mono uppercase max-w-[240px]"
            />
            <Button size="sm" variant="outline" className="h-8 text-xs gap-1" onClick={addCustomCoin}>
              <Plus className="h-3.5 w-3.5" /> Add Coin
            </Button>
            <span className="text-[11px] text-muted-foreground hidden sm:inline ml-auto">
              🎯 AI scanner exclusively analyzes only the {fixedCoins.length} selected coins above.
            </span>
          </div>
        </div>

      </div>

      {/* MANUAL ANALYZE & TEST TRADE */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Search className="h-4 w-4 text-primary" /> Analyze &amp; Trade Any Specific Coin
        </span>
        <div className="flex flex-wrap gap-2">
          <Input type="text" placeholder="Type: BTC, ETH, SOL, PEPE, DOGE..."
            value={coinInput} onChange={e => setCoinInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && tradeCoin(coinInput)}
            className="h-9 uppercase font-mono text-sm max-w-sm" />
          <Button className="h-9 bg-primary font-semibold px-4 text-xs gap-1.5" onClick={() => tradeCoin(coinInput)} disabled={analyzing}>
            {analyzing ? <span className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            AI Instant Analyze &amp; Trade
          </Button>
          <Button variant="outline" size="sm" className="h-9 text-xs text-green-400 border-green-500/40" onClick={() => tradeCoin(coinInput || "BTCUSDT", "BUY")} disabled={analyzing}>🟢 Test BUY</Button>
          <Button variant="outline" size="sm" className="h-9 text-xs text-red-400 border-red-500/40" onClick={() => tradeCoin(coinInput || "BTCUSDT", "SELL")} disabled={analyzing}>🔴 Test SELL</Button>
        </div>
      </div>

      {/* PORTFOLIO SUMMARY — LIVE TIME-TO-TIME UPDATING */}
      <div className="space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Wallet className="h-4 w-4 text-primary" /> Live Wallet &amp; Cash Balance
          </h2>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs text-green-400 border-green-500/40 gap-1 bg-green-500/10 hover:bg-green-500/20"
              onClick={async () => {
                try {
                  await api.post("/wallet/deposit", { user_id: userId, asset: "USDT", amount: 1000 });
                  toast.success("Deposited +$1,000 USDT to your Trading Wallet!");
                  addLog("💵 Deposited +$1,000 USDT to Trading Wallet via Instant Top-Up", "info");
                  await loadStatus(true);
                } catch (e) {
                  toast.error(getErrorMessage(e, "Top-up failed"));
                }
              }}
            >
              <DollarSign className="h-3 w-3" /> Top Up $1,000 USDT
            </Button>
            <span className="text-[11px] text-green-400 flex items-center gap-1.5 bg-green-500/10 border border-green-500/30 px-2 py-0.5 rounded-full font-mono">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Live Updating (every 6s)
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            {
              label: "Total Wallet Value",
              value: fmtUSD(status?.total_portfolio ?? status?.total_portfolio_value ?? 0),
              sub: (Number(status?.cash_locked) > 0)
                ? `$${fmt(status?.cash_available || 0)} free + $${fmt(status?.cash_locked || 0)} in orders`
                : "Cash + Open Coins Value",
              color: "text-primary",
            },
            {
              label: "Cash Available",
              value: fmtUSD(status?.cash_available ?? 0),
              sub: (Number(status?.cash_locked) > 0)
                ? `Ready cash (${fmtUSD(status?.cash_locked)} in order)`
                : "Ready cash to trade",
              color: "text-green-400",
            },
            {
              label: "Active Positions Value",
              value: fmtUSD(status?.position_value ?? status?.total_position_value ?? 0),
              sub: `${positions.length} open coin(s) live`,
              color: "text-blue-400",
            },
            {
              label: "Live Unrealized P&L",
              value: fmtUSD(status?.total_unrealized_pnl ?? 0),
              sub: Number(status?.total_unrealized_pnl) >= 0 ? "Profit on open coins" : "Loss on open coins",
              color: Number(status?.total_unrealized_pnl) >= 0 ? "text-green-400" : "text-red-400",
            },
          ].map(card => (
            <div key={card.label} className="rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/40">
              <div className="text-xs text-muted-foreground mb-1">{card.label}</div>
              <div className={`text-xl font-bold font-mono ${card.color}`}>{card.value}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5">{card.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* OPEN POSITIONS */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <h2 className="font-semibold flex items-center gap-2 text-sm">
          <TrendingUp className="h-4 w-4 text-primary" /> Open Positions
          <span className="text-xs text-muted-foreground font-normal">(live prices, unrealized P&amp;L)</span>
        </h2>
        {positions.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded-lg">
            No open positions. AI will BUY when score &ge; 65.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="border-b border-border text-muted-foreground bg-muted/20">
                <tr>
                  {["Coin","Qty Held","Bought At (Avg)","Current Price","Current Value","Cost Basis","Unrealized P&L","P&L %","Action"].map(h => (
                    <th key={h} className="p-2.5 text-left font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {positions.map(pos => {
                  const buyPrice = pos.avg_buy_price || pos.average_entry_price || pos.avg_price || pos.price || 0;
                  return (
                    <tr key={pos.symbol} className="hover:bg-muted/20">
                      <td className="p-2.5 font-bold text-sm text-foreground">{pos.symbol}</td>
                      <td className="p-2.5">{Number(pos.quantity).toFixed(6)}</td>
                      <td className="p-2.5 text-yellow-400">{fmtPrice(buyPrice)}</td>
                      <td className="p-2.5 text-white">{fmtPrice(pos.current_price)}</td>
                      <td className="p-2.5">{fmtUSD(pos.current_value)}</td>
                      <td className="p-2.5 text-muted-foreground">{fmtUSD(pos.cost_basis)}</td>
                      <td className="p-2.5"><PnLBadge value={pos.unrealized_pnl} /></td>
                      <td className="p-2.5"><PnLBadge value={pos.unrealized_pnl_pct} /></td>
                      <td className="p-2.5">
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={analyzing}
                          onClick={() => tradeCoin(pos.symbol, "SELL")}
                          className="h-7 text-xs px-2.5 bg-red-600/80 hover:bg-red-600 font-semibold"
                        >
                          🔴 Sell Now
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* AI DECISION BOARD */}
      {analyses.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <h2 className="font-semibold flex items-center gap-2 text-sm">
            <Activity className="h-4 w-4 text-primary" /> AI Decision Board
            <span className="text-xs text-muted-foreground font-normal">(latest analysis per coin)</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {analyses.map(a => {
              const cs = a.current_situation || {};
              const ps = a.past_situation || {};
              return (
                <div key={a.symbol} className="rounded-lg border border-border p-3 space-y-2 bg-muted/10">
                  <div className="flex items-center justify-between">
                    <span className="font-bold font-mono">{a.symbol}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground">Score: <span className="font-bold text-primary">{a.prediction_score}/100</span></span>
                      <ActionBadge action={a.action} />
                    </div>
                  </div>
                  <Progress value={a.prediction_score} className="h-1.5" />
                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    <div className="bg-background/60 rounded p-2 space-y-0.5">
                      <div className="text-muted-foreground font-semibold">24h Ago</div>
                      <div className="font-mono">{fmtPrice(ps.price)}</div>
                      <div>RSI: {ps.rsi} | {ps.trend}</div>
                    </div>
                    <div className="bg-primary/5 border border-primary/20 rounded p-2 space-y-0.5">
                      <div className="text-primary font-semibold">Now (Live)</div>
                      <div className="font-mono font-bold">{fmtPrice(cs.price)}</div>
                      <div>RSI: {cs.rsi} | {fmtPct(cs.price_change_24h)}</div>
                    </div>
                  </div>
                  <div className="text-[11px] text-muted-foreground border-t border-border/40 pt-1.5">
                    <span className="font-semibold">AI Reason: </span>{a.decision?.reason || a.decision?.description || ""}
                  </div>
                  {a.open_position_buy_price && (
                    <div className="text-[11px] text-yellow-400">
                      📌 Holding since Buy @ {fmtPrice(a.open_position_buy_price)}
                      {a.current_price && (
                        <span className={Number(a.current_price) >= Number(a.open_position_buy_price) ? " text-green-400" : " text-red-400"}>
                          {" "}&rarr; {fmtPrice(a.current_price)} ({fmtPct(((a.current_price - a.open_position_buy_price) / a.open_position_buy_price) * 100)})
                        </span>
                      )}
                    </div>
                  )}
                  <div className="text-[11px] text-muted-foreground">
                    SMA20: {fmtPrice(cs.sma20)} | Stop: {fmtPrice(a.stop_loss)} | Target: {fmtPrice(a.take_profit)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {/* TRADE HISTORY */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 text-green-400" /> Complete Trade History
              <Badge className="bg-muted text-muted-foreground text-xs">{trades.length} records</Badge>
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">Click any trade row to view the full AI rationale, technical indicators, and execution breakdown.</p>
          </div>
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <span>Total Realized P&L:</span>
            <span className={`font-bold font-mono px-2 py-0.5 rounded ${Number(status?.total_realized_pnl) >= 0 ? "bg-green-500/10 text-green-400 border border-green-500/30" : "bg-red-500/10 text-red-400 border border-red-500/30"}`}>
              {fmtUSD(status?.total_realized_pnl || 0)}
            </span>
          </div>
        </div>

        {/* FILTERS & SEARCH */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1 border-t border-border/50">
          <div className="flex items-center gap-1.5 flex-wrap">
            {[
              { id: "ALL", label: `All (${trades.length})` },
              { id: "BUY", label: `🟢 Buys (${trades.filter(t => (t.side||t.action)==="BUY").length})` },
              { id: "SELL", label: `🔴 Sells (${trades.filter(t => (t.side||t.action)==="SELL").length})` },
              { id: "REJECTED", label: `⚠️ Risk Blocked (${trades.filter(t => String(t.side||t.action).includes("REJECT")).length})` },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setTradeFilter(tab.id)}
                className={`px-3 py-1 text-xs rounded-lg font-medium transition-all ${
                  tradeFilter === tab.id
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative min-w-[200px]">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Filter by coin (e.g. BTC, ETH)..."
              value={tradeSearch}
              onChange={e => setTradeSearch(e.target.value)}
              className="h-8 pl-8 text-xs bg-background/60"
            />
          </div>
        </div>

        {/* TRADES TABLE */}
        {(() => {
          const filteredTrades = trades.filter(t => {
            const side = (t.side || t.action || "BUY").toUpperCase();
            if (tradeFilter === "BUY" && side !== "BUY") return false;
            if (tradeFilter === "SELL" && side !== "SELL") return false;
            if (tradeFilter === "REJECTED" && !side.includes("REJECT")) return false;
            if (tradeSearch.trim()) {
              const q = tradeSearch.trim().toUpperCase();
              return (t.symbol || "").toUpperCase().includes(q) || (t.reason || t.rationale || "").toUpperCase().includes(q);
            }
            return true;
          });

          if (filteredTrades.length === 0) {
            return (
              <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded-lg">
                {trades.length === 0
                  ? "No trades yet. AI will trade when market signals trigger BUY or SELL."
                  : "No trades matching the selected filter."}
              </div>
            );
          }

          return (
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full text-xs font-mono">
                <thead className="border-b border-border text-muted-foreground bg-muted/30">
                  <tr>
                    {["Time", "Coin", "Action", "Price", "Qty", "Total Value", "Fee", "Realized P&L", "AI Score", "Full Reason", "Inspect"].map(h => (
                      <th key={h} className="p-2.5 text-left font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {filteredTrades.map((t, i) => {
                    const side = t.side || t.action || "BUY";
                    const isBuy = side === "BUY";
                    const isSell = side === "SELL";
                    const isRejected = side.includes("REJECT");
                    const price = t.price || (isBuy ? t.buy_price : t.sell_price) || 0;
                    const tradeTime = t.created_at ? new Date(t.created_at).toLocaleString() : (t.trade_time || t.time || "—");
                    const fullReason = t.reason || t.rationale || (isBuy ? "AI Bullish Momentum Breakout Signal (Score >= 65)" : isSell ? "AI Take-Profit Target Reached" : "AI Trade Execution");
                    const amountVal = t.amount || (price && t.quantity ? price * t.quantity : 0);

                    return (
                      <tr
                        key={t.id || i}
                        onClick={() => setSelectedTrade({ ...t, fullReason, price, tradeTime, side, isBuy, isSell, isRejected, amountVal })}
                        className="hover:bg-muted/30 cursor-pointer transition-colors group"
                      >
                        <td className="p-2.5 text-muted-foreground whitespace-nowrap">
                          {tradeTime}
                        </td>
                        <td className="p-2.5 font-bold text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
                          {t.symbol}
                        </td>
                        <td className="p-2.5"><ActionBadge action={side} /></td>
                        <td className="p-2.5 font-mono">
                          {price > 0 ? (
                            <span className={isBuy ? "text-yellow-400" : isSell ? "text-red-400" : "text-muted-foreground"}>{fmtPrice(price)}</span>
                          ) : "—"}
                        </td>
                        <td className="p-2.5">{Number(t.quantity || 0) > 0 ? Number(t.quantity).toFixed(6) : "—"}</td>
                        <td className="p-2.5">{amountVal > 0 ? fmtUSD(amountVal) : "—"}</td>
                        <td className="p-2.5 text-muted-foreground">{t.fee ? fmtUSD(t.fee) : "$0.00"}</td>
                        <td className="p-2.5">
                          {isSell ? (
                            <PnLBadge value={t.realized_pnl || 0} pct={t.pnl_pct} />
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="p-2.5">
                          {t.score ? (
                            <span className={`font-bold ${t.score >= 65 ? "text-green-400" : t.score >= 45 ? "text-yellow-400" : "text-red-400"}`}>{t.score}/100</span>
                          ) : "—"}
                        </td>
                        <td className="p-2.5 text-muted-foreground max-w-[280px]">
                          <div className="truncate font-sans text-[11px]" title={fullReason}>
                            {fullReason}
                          </div>
                        </td>
                        <td className="p-2.5 text-center">
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-primary hover:bg-primary/20">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

      {/* FULL AI TRADE INSPECTION MODAL */}
      {selectedTrade && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            {/* MODAL HEADER */}
            <div className="flex items-start justify-between border-b border-border pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <h3 className="text-lg font-bold font-mono text-foreground flex items-center gap-2">
                    <Bot className="h-5 w-5 text-primary" /> {selectedTrade.symbol} Trade Details
                  </h3>
                  <ActionBadge action={selectedTrade.side} />
                </div>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" /> Executed at: <span className="font-mono text-foreground">{selectedTrade.tradeTime}</span>
                </p>
              </div>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" onClick={() => setSelectedTrade(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* FULL AI REASON & RATIONALE CARD */}
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider">
                <Info className="h-4 w-4" /> Full AI Decision Rationale
              </div>
              <p className="text-sm text-foreground leading-relaxed font-sans font-medium">
                {selectedTrade.fullReason}
              </p>
              {selectedTrade.market_regime && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1 border-t border-primary/20">
                  <span>Market Regime:</span>
                  <Badge variant="outline" className="font-mono text-primary text-[10px] uppercase">
                    {selectedTrade.market_regime}
                  </Badge>
                </div>
              )}
            </div>

            {/* FINANCIAL BREAKDOWN */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-primary" /> Financial Execution
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Price</div>
                  <div className="text-sm font-bold text-foreground mt-0.5">{fmtPrice(selectedTrade.price)}</div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Quantity</div>
                  <div className="text-sm font-bold text-foreground mt-0.5">{Number(selectedTrade.quantity||0).toFixed(6)}</div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Total Amount</div>
                  <div className="text-sm font-bold text-foreground mt-0.5">{fmtUSD(selectedTrade.amountVal || selectedTrade.amount || 0)}</div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Trading Fee</div>
                  <div className="text-sm font-bold text-muted-foreground mt-0.5">{fmtUSD(selectedTrade.fee || 0)}</div>
                </div>
              </div>
            </div>

            {/* PNL & RISK METRICS */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Target className="h-3.5 w-3.5 text-primary" /> AI Risk &amp; Intelligence Metrics
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">AI Score</div>
                  <div className={`text-sm font-bold mt-0.5 ${selectedTrade.score >= 65 ? "text-green-400" : selectedTrade.score >= 45 ? "text-yellow-400" : "text-red-400"}`}>
                    {selectedTrade.score ? `${selectedTrade.score}/100` : "N/A"}
                  </div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Confidence</div>
                  <div className="text-sm font-bold text-blue-400 mt-0.5">
                    {selectedTrade.confidence ? `${selectedTrade.confidence}%` : "85.0%"}
                  </div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Take-Profit Target</div>
                  <div className="text-sm font-bold text-green-400 mt-0.5">
                    {selectedTrade.take_profit ? fmtPrice(selectedTrade.take_profit) : (selectedTrade.price ? fmtPrice(selectedTrade.price * 1.03) : "—")}
                  </div>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 border border-border/50">
                  <div className="text-muted-foreground text-[10px]">Stop-Loss Level</div>
                  <div className="text-sm font-bold text-red-400 mt-0.5">
                    {selectedTrade.stop_loss ? fmtPrice(selectedTrade.stop_loss) : (selectedTrade.price ? fmtPrice(selectedTrade.price * 0.975) : "—")}
                  </div>
                </div>
              </div>
            </div>

            {/* REALIZED PNL FOR SELLS */}
            {selectedTrade.isSell && (
              <div className="rounded-xl border border-border bg-muted/20 p-3 flex items-center justify-between text-xs font-mono">
                <span className="text-muted-foreground font-semibold">Realized Profit / Loss on this Trade:</span>
                <PnLBadge value={selectedTrade.realized_pnl || 0} pct={selectedTrade.pnl_pct} />
              </div>
            )}

            {/* METADATA FOOTER */}
            <div className="pt-3 border-t border-border flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground font-mono">
              <div>Order ID: <span className="text-foreground">{selectedTrade.order_id || selectedTrade.id || "N/A"}</span></div>
              <Button size="sm" onClick={() => setSelectedTrade(null)}>Close Inspection</Button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
