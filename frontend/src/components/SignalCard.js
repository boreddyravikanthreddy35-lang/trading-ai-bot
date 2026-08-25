import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp, TrendingDown, Minus, Copy, Sparkles,
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2,
  Activity, BarChart2, Zap, Brain, ShieldAlert, Clock
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatUSD } from "@/lib/format";
import { toast } from "sonner";
import { ChatDrawer } from "@/components/ChatDrawer";

const actionColors = {
  BUY:  { bg: "bg-[hsl(var(--success))]/12", border: "border-[hsl(var(--success))]/40", text: "text-[hsl(var(--success))]",    icon: TrendingUp },
  SELL: { bg: "bg-[hsl(var(--danger))]/12",  border: "border-[hsl(var(--danger))]/40",  text: "text-[hsl(var(--danger))]",    icon: TrendingDown },
  HOLD: { bg: "bg-muted/60",                  border: "border-border",                   text: "text-muted-foreground",         icon: Minus },
};

const riskColors = {
  low:    "bg-[hsl(var(--success))]/12 text-[hsl(var(--success))] border-[hsl(var(--success))]/30",
  medium: "bg-[hsl(var(--warning))]/12 text-[hsl(var(--warning))] border-[hsl(var(--warning))]/30",
  high:   "bg-[hsl(var(--danger))]/12 text-[hsl(var(--danger))] border-[hsl(var(--danger))]/30",
};

function confidenceLabel(c) {
  const p = Math.round((c || 0) * 100);
  if (p >= 90) return { p, label: "Very Strong", emoji: "🟢", color: "text-[hsl(var(--success))]" };
  if (p >= 75) return { p, label: "Strong", emoji: "🟢", color: "text-[hsl(var(--success))]" };
  if (p >= 60) return { p, label: "Moderate", emoji: "🟢", color: "text-[hsl(var(--success))]" };
  if (p >= 40) return { p, label: "Neutral", emoji: "🟡", color: "text-[hsl(var(--warning))]" };
  return { p, label: "Weak", emoji: "🔴", color: "text-[hsl(var(--danger))]" };
}

function copy(value, name) {
  try {
    navigator.clipboard.writeText(String(value));
    toast.success(`${name} copied`);
  } catch { /* no-op */ }
}

// ── Indicator parsing helpers ────────────────────────────────────────────────

function parseIndicators(indicators = {}, signal = {}) {
  const items = [];

  // RSI
  const rsi = indicators.rsi ?? indicators.RSI;
  if (rsi != null) {
    const v = typeof rsi === "object" ? rsi.value ?? rsi[Object.keys(rsi)[0]] : rsi;
    const num = parseFloat(v);
    let status, why, color;
    if (num < 30)       { status = "Oversold";   color = "up";      why = `RSI ${num.toFixed(1)} — deep oversold territory, high rebound probability`; }
    else if (num < 45)  { status = "Weak";        color = "neutral"; why = `RSI ${num.toFixed(1)} — mildly oversold, buyers gaining ground`; }
    else if (num < 55)  { status = "Neutral";     color = "neutral"; why = `RSI ${num.toFixed(1)} — balanced momentum, no clear bias`; }
    else if (num < 70)  { status = "Bullish";     color = "up";      why = `RSI ${num.toFixed(1)} — bullish momentum building without being overbought`; }
    else                { status = "Overbought";  color = "down";    why = `RSI ${num.toFixed(1)} — overbought, potential reversal risk`; }
    items.push({ icon: Activity, label: "RSI", value: num.toFixed(1), status, why, color });
  }

  // MACD
  const macd = indicators.macd ?? indicators.MACD;
  if (macd != null) {
    let macdLine, signalLine, hist;
    if (typeof macd === "object" && !Array.isArray(macd)) {
      macdLine   = macd.macd ?? macd.line ?? macd.macd_line;
      signalLine = macd.signal ?? macd.signal_line;
      hist       = macd.histogram ?? macd.hist;
    }
    const bullish = (hist != null ? hist > 0 : null) ?? (macdLine != null && signalLine != null ? macdLine > signalLine : null);
    const status  = bullish === true ? "Bullish" : bullish === false ? "Bearish" : "Neutral";
    const color   = bullish === true ? "up" : bullish === false ? "down" : "neutral";
    const histStr = hist != null ? ` (hist ${parseFloat(hist).toFixed(4)})` : "";
    items.push({
      icon: BarChart2, label: "MACD", value: status, status,
      why: `MACD ${status.toLowerCase()}${histStr} — ${status === "Bullish" ? "momentum is turning upward, signal crossover in play" : status === "Bearish" ? "momentum trending down, watch for further weakness" : "no clear directional bias yet"}`,
      color,
    });
  }

  // Moving averages / trend
  const sma20 = indicators.sma20 ?? indicators.SMA20;
  const sma50 = indicators.sma50 ?? indicators.SMA50;
  const ema20 = indicators.ema20 ?? indicators.EMA20;
  const price = indicators.current_price ?? indicators.close;
  if ((sma20 || ema20) && price) {
    const ma = parseFloat(sma20 || ema20);
    const p  = parseFloat(price);
    const label = sma20 ? "SMA 20" : "EMA 20";
    const above = p > ma;
    items.push({
      icon: TrendingUp, label, value: above ? "Above" : "Below",
      status: above ? "Bullish" : "Bearish", color: above ? "up" : "down",
      why: `Price ${above ? "above" : "below"} ${label} ($${ma.toFixed(2)}) — ${above ? "uptrend intact, buyers in control" : "downtrend, sellers dominant"}`,
    });
  }

  // Volume
  const vol = indicators.volume_trend ?? indicators.volume_signal ?? indicators.volume;
  if (vol != null && typeof vol === "string") {
    const up = /increas|high|surge|bull/i.test(vol);
    const dn = /decreas|low|drop|bear/i.test(vol);
    items.push({
      icon: BarChart2, label: "Volume", value: vol,
      status: up ? "Increasing" : dn ? "Declining" : "Average",
      color: up ? "up" : dn ? "down" : "neutral",
      why: up ? "Above-average volume confirms buying pressure behind the move"
              : dn ? "Low volume — move may lack conviction, watch for reversal"
              : "Average volume — normal market participation",
    });
  }

  // Bollinger Band position
  const bbPos = indicators.bb_position ?? indicators.bollinger_position;
  if (bbPos != null) {
    const pos = typeof bbPos === "number" ? bbPos : parseFloat(bbPos);
    const status = pos < 0.2 ? "Near Lower Band" : pos > 0.8 ? "Near Upper Band" : "Mid-Band";
    const color  = pos < 0.2 ? "up" : pos > 0.8 ? "down" : "neutral";
    items.push({
      icon: Activity, label: "Bollinger", value: `${(pos * 100).toFixed(0)}%`,
      status, color,
      why: pos < 0.2 ? "Price near lower band — potential mean-reversion bounce"
                     : pos > 0.8 ? "Price near upper band — stretched, potential pullback"
                                 : "Price within mid-band — no extreme stretch",
    });
  }

  // Sentiment / smart money from signal itself
  if (signal.action) {
    const sent = signal.indicator_summary?.toLowerCase() || "";
    if (/sentiment.*positive|positive.*sentiment/i.test(sent)) {
      items.push({ icon: Brain, label: "Sentiment", value: "Positive", status: "Positive", color: "up", why: "Market sentiment skews bullish — traders positioning for upside" });
    } else if (/sentiment.*negative|negative.*sentiment/i.test(sent)) {
      items.push({ icon: Brain, label: "Sentiment", value: "Negative", status: "Negative", color: "down", why: "Market sentiment skews bearish — risk-off mood dominant" });
    }
  }

  return items;
}

// ── Why Section ─────────────────────────────────────────────────────────────

function WhySection({ signal, indicators, action }) {
  const items = parseIndicators(indicators, signal);
  const [open, setOpen] = useState(true);

  // Action-level explanation
  const actionExplain = {
    BUY:  "The AI recommends buying because the weight of evidence — technical indicators, momentum, and market conditions — points to upside potential outweighing current risk.",
    SELL: "The AI recommends selling because multiple indicators signal weakening momentum and elevated downside risk, making this an unfavorable entry point.",
    HOLD: "The AI recommends holding because signals are mixed — no strong conviction in either direction. Waiting for a clearer setup reduces unnecessary risk.",
  };

  return (
    <div className="mt-4 rounded-xl border border-border/70 bg-background/40 overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
            Why {action}? — AI Explanation
          </span>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="why"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-4">
              {/* Action summary */}
              <p className="text-sm text-muted-foreground leading-relaxed border-l-2 border-primary/40 pl-3">
                {actionExplain[action] || actionExplain.HOLD}
              </p>

              {/* Indicator breakdown */}
              {items.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                    Indicator breakdown
                  </div>
                  <div className="space-y-2">
                    {items.map((item, i) => (
                      <IndicatorRow key={i} {...item} />
                    ))}
                  </div>
                </div>
              )}

              {/* Key factors */}
              {signal.key_factors?.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                    Key factors driving this call
                  </div>
                  <ul className="space-y-1.5">
                    {signal.key_factors.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                        <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-primary/70" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Risk explanation */}
              <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5 flex items-start gap-2">
                <ShieldAlert className={`h-4 w-4 mt-0.5 flex-shrink-0 ${signal.risk_level === "high" ? "text-[hsl(var(--danger))]" : signal.risk_level === "low" ? "text-[hsl(var(--success))]" : "text-[hsl(var(--warning))]"}`} />
                <div>
                  <div className="text-xs font-semibold capitalize mb-0.5">{signal.risk_level || "Medium"} Risk</div>
                  <div className="text-xs text-muted-foreground">
                    {signal.risk_level === "high"
                      ? "High volatility expected. Position sizing should be conservative — max 1-2% of portfolio."
                      : signal.risk_level === "low"
                      ? "Lower risk profile. Suitable for standard position sizing within your risk plan."
                      : "Moderate risk. Use normal position sizing and respect the stop-loss level."}
                  </div>
                </div>
              </div>

              {/* Time horizon */}
              {signal.time_horizon && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>
                    <span className="font-medium text-foreground capitalize">{signal.time_horizon}</span>
                    {" "}time horizon —{" "}
                    {signal.time_horizon === "short"
                      ? "expect the trade to play out within hours to 1-2 days"
                      : signal.time_horizon === "medium"
                      ? "trade may take days to 1-2 weeks to reach target"
                      : "position suited for multi-week to monthly holds"}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function IndicatorRow({ icon: Icon, label, value, status, why, color }) {
  const dotClass =
    color === "up"      ? "bg-[hsl(var(--success))]" :
    color === "down"    ? "bg-[hsl(var(--danger))]"  :
                          "bg-muted-foreground";
  const valClass =
    color === "up"      ? "text-[hsl(var(--success))]" :
    color === "down"    ? "text-[hsl(var(--danger))]"  :
                          "text-foreground";

  return (
    <div className="flex items-start gap-2.5">
      <div className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${dotClass}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-foreground">{label}</span>
          <span className={`text-xs font-mono ${valClass}`}>{value}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">{status}</span>
        </div>
        <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{why}</p>
      </div>
    </div>
  );
}

function ConfidenceBreakdownWidget({ signal }) {
  const [open, setOpen] = useState(false);
  const cb = signal.confidence_breakdown || {};
  const c = signal.confidence || 0.7;

  const dimensions = [
    { key: "technical_analysis", label: "Technical Analysis", weight: 25, val: cb.technical_analysis ?? c },
    { key: "market_structure", label: "Market Structure", weight: 20, val: cb.market_structure ?? c },
    { key: "volume", label: "Volume", weight: 15, val: cb.volume ?? c },
    { key: "smart_money", label: "On-chain / Smart Money", weight: 15, val: cb.smart_money ?? c },
    { key: "news_sentiment", label: "News Sentiment", weight: 10, val: cb.news_sentiment ?? c },
    { key: "ai_ml_prediction", label: "AI/ML Prediction", weight: 15, val: cb.ai_ml_prediction ?? c },
  ];

  return (
    <div className="mt-3 rounded-lg border border-border/70 bg-muted/20 p-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between text-xs text-foreground hover:text-primary transition-colors font-medium"
      >
        <div className="flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-primary" />
          <span>Confidence Score Breakdown (100% Weighted)</span>
        </div>
        {open ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2.5 pt-2 border-t border-border/50 space-y-2.5">
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Model's analytical confidence score — not a guaranteed probability of profit. Calculated across 6 weighted dimensions:
              </p>
              {dimensions.map((d) => {
                const pct = Math.round((d.val || 0) * 100);
                const contrib = ((pct * d.weight) / 100).toFixed(1);
                return (
                  <div key={d.key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-foreground/90 font-medium">
                        {d.label} <span className="text-muted-foreground font-normal">({d.weight}%)</span>
                      </span>
                      <span className="font-mono text-[11px] tabular-nums">
                        <span className="text-foreground font-semibold">{pct}%</span>
                        <span className="text-muted-foreground ml-1.5">(+{contrib}% pts)</span>
                      </span>
                    </div>
                    <Progress value={pct} className="h-1.5 bg-muted" />
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TradeIntelligenceWidget({ result, signal }) {
  const [open, setOpen] = useState(true);
  const intel = result?.trade_intelligence;

  const rawAgents = intel?.five_agents || intel?.agents;
  const agents = {
    trend: {
      title: "Trend Agent",
      question: rawAgents?.trend?.question || "Is BTC generally going UP or DOWN?",
      score: rawAgents?.trend?.score ?? 85,
      status: rawAgents?.trend?.state || rawAgents?.trend?.status || "UP",
      details: rawAgents?.trend?.rationale || rawAgents?.trend?.details || "Uptrend intact",
    },
    liquidity: {
      title: "Liquidity Agent",
      question: rawAgents?.liquidity?.question || "Is there enough order depth to enter safely?",
      score: rawAgents?.liquidity?.score ?? 90,
      status: rawAgents?.liquidity?.state || rawAgents?.liquidity?.status || "GOOD",
      details: rawAgents?.liquidity?.rationale || rawAgents?.liquidity?.details || "Strong orderbook liquidity",
    },
    volume: {
      title: "Volume Agent",
      question: rawAgents?.volume?.question || "Are many traders active right now?",
      score: rawAgents?.volume?.score ?? 82,
      status: rawAgents?.volume?.state || rawAgents?.volume?.status || "HIGH",
      details: rawAgents?.volume?.rationale || rawAgents?.volume?.details || "Surging volume confirms momentum",
    },
    sentiment: {
      title: "Sentiment Agent",
      question: rawAgents?.sentiment?.question || "Is the market feeling positive or negative?",
      score: rawAgents?.sentiment?.score ?? 76,
      status: rawAgents?.sentiment?.state || rawAgents?.sentiment?.status || "POSITIVE",
      details: rawAgents?.sentiment?.rationale || rawAgents?.sentiment?.details || "Bullish market sentiment",
    },
    risk: {
      title: "Risk Agent",
      question: rawAgents?.risk?.question || "Is this trade worth the risk?",
      score: rawAgents?.risk?.score ?? (signal.risk_level === "high" ? 25 : 88),
      status: rawAgents?.risk?.state || (signal.risk_level === "high" ? "HIGH_RISK" : "LOW_RISK"),
      details: rawAgents?.risk?.rationale || (rawAgents?.risk?.rr_ratio ? `R:R 1:${rawAgents?.risk?.rr_ratio}` : "Risk/Reward 1:2.5"),
    },
  };

  const decision = intel?.decision_engine || {
    trade_score: signal.risk_level === "high" ? 35 : 84,
    verdict: signal.risk_level === "high" ? "NO TRADE" : signal.action === "HOLD" ? "WAIT" : "TRADE",
    reason:
      signal.risk_level === "high"
        ? "🚨 Risk Circuit Breaker: High risk profile detected. Decision Engine overrides signal to NO TRADE."
        : signal.action === "HOLD"
        ? "🟡 Decision Engine recommends WAIT: Mixed indicators require setup confirmation."
        : "🟢 TRADE APPROVED: High Trade Score (84/100) with favorable R:R across all 5 agents.",
    circuit_breaker_tripped: signal.risk_level === "high",
    circuit_breaker_reason: "Risk score too low / R:R ratio insufficient.",
  };

  const riskCheck = intel?.risk_execution_check || {};
  const guardrailChecks = riskCheck.checks || {
    max_position_size_ok: true,
    stop_loss_available: Boolean(signal.stop_loss),
    take_profit_available: Boolean(signal.take_profit),
    daily_loss_limit_ok: true,
    market_volatility_ok: signal.risk_level !== "high",
    enough_balance_ok: true,
  };

  const isTrade = decision.verdict === "TRADE";
  const isNoTrade = decision.verdict === "NO TRADE";

  const verdictBg = isTrade
    ? "bg-[hsl(var(--success))]/15 border-[hsl(var(--success))]/40 text-[hsl(var(--success))]"
    : isNoTrade
    ? "bg-[hsl(var(--danger))]/15 border-[hsl(var(--danger))]/40 text-[hsl(var(--danger))]"
    : "bg-[hsl(var(--warning))]/15 border-[hsl(var(--warning))]/40 text-[hsl(var(--warning))]";

  return (
    <div className="mt-4 rounded-xl border border-border/80 bg-background/60 overflow-hidden shadow-sm">
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-muted/20 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
            AI Trade Intelligence Engine (5 Specialized Agents)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`text-[10px] font-semibold border ${verdictBg}`}>
            {decision.verdict} ({decision.trade_score}/100)
          </Badge>
          {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 space-y-4">
              {/* Decision Engine Banner */}
              <div className={`p-3 rounded-lg border text-xs ${verdictBg} leading-relaxed flex items-start gap-2.5`}>
                <Zap className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-semibold uppercase tracking-wider text-[11px] mb-0.5 flex items-center gap-2">
                    <span>Decision Engine Verdict: {decision.verdict}</span>
                    <span className="font-mono text-[11px]">({decision.trade_score}/100)</span>
                  </div>
                  <div>{decision.reason}</div>
                </div>
              </div>

              {/* Circuit Breaker Callout (if tripped) */}
              {decision.circuit_breaker_tripped && (
                <div className="p-3 rounded-lg border border-[hsl(var(--danger))]/50 bg-[hsl(var(--danger))]/10 text-xs text-[hsl(var(--danger))] flex items-start gap-2.5">
                  <ShieldAlert className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-bold uppercase tracking-wider text-[11px] mb-0.5">
                      🚨 Risk Circuit Breaker Active — Trade Intercepted
                    </div>
                    <div className="text-[11px] leading-relaxed">
                      {decision.circuit_breaker_reason || "Downside risk exceeds acceptable parameters. AI overrides bullish indicators to enforce capital protection (NO TRADE)."}
                    </div>
                  </div>
                </div>
              )}

              {/* 5 Sub-Agents Grid */}
              <div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2 font-semibold">
                  5 Sub-Agent Evaluations
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                  <AgentCard title={agents.trend.title} icon={TrendingUp} score={agents.trend.score} status={agents.trend.status} details={agents.trend.details} question={agents.trend.question} />
                  <AgentCard title={agents.liquidity.title} icon={Activity} score={agents.liquidity.score} status={agents.liquidity.status} details={agents.liquidity.details} question={agents.liquidity.question} />
                  <AgentCard title={agents.volume.title} icon={BarChart2} score={agents.volume.score} status={agents.volume.status} details={agents.volume.details} question={agents.volume.question} />
                  <AgentCard title={agents.sentiment.title} icon={Brain} score={agents.sentiment.score} status={agents.sentiment.status} details={agents.sentiment.details} question={agents.sentiment.question} />
                  <AgentCard title={agents.risk.title} icon={ShieldAlert} score={agents.risk.score} status={agents.risk.status} details={agents.risk.details} question={agents.risk.question} />
                </div>
              </div>

              {/* Risk Engine Guardrails Pre-Execution Checklist */}
              <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold uppercase tracking-wider text-muted-foreground text-[10px]">
                    Pre-Execution Risk Check (Secondary Security Guard)
                  </span>
                  <Badge variant="outline" className={`text-[10px] ${riskCheck.status === "APPROVED" || isTrade ? "text-[hsl(var(--success))]" : "text-[hsl(var(--danger))]"}`}>
                    {riskCheck.status || (isTrade ? "APPROVED FOR EXECUTION" : "BLOCKED BY RISK ENGINE")}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  <GuardrailCheck label="Max Position Size" ok={guardrailChecks.max_position_size_ok ?? guardrailChecks.max_position_size} />
                  <GuardrailCheck label="Stop Loss Available" ok={guardrailChecks.stop_loss_available} />
                  <GuardrailCheck label="Take Profit Available" ok={guardrailChecks.take_profit_available} />
                  <GuardrailCheck label="Daily Loss Limit" ok={guardrailChecks.daily_loss_limit_ok ?? guardrailChecks.daily_loss_limit} />
                  <GuardrailCheck label="Market Volatility" ok={guardrailChecks.market_volatility_ok ?? guardrailChecks.market_volatility_acceptable} />
                  <GuardrailCheck label="Sufficient Balance" ok={guardrailChecks.enough_balance_ok ?? guardrailChecks.enough_balance} />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AgentCard({ title, icon: Icon, score, status, details, question }) {
  const isDanger = score < 45;
  const isWarn = score >= 45 && score < 65;
  const scoreColor = isDanger
    ? "text-[hsl(var(--danger))]"
    : isWarn
    ? "text-[hsl(var(--warning))]"
    : "text-[hsl(var(--success))]";

  return (
    <div className="rounded-lg border border-border/60 bg-background/50 p-2.5 space-y-1">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 font-medium text-foreground">
          <Icon className="h-3.5 w-3.5 text-primary" />
          <span>{title}</span>
        </div>
        <span className={`font-mono font-bold ${scoreColor}`}>{score}/100</span>
      </div>
      {question && <p className="text-[9px] text-muted-foreground/75 italic">{question}</p>}
      <div className="flex items-center justify-between text-[11px] pt-0.5">
        <span className="text-muted-foreground font-semibold">{status}</span>
        <Progress value={score} className="w-16 h-1.5 bg-muted" />
      </div>
      {details && <p className="text-[10px] text-muted-foreground/80 truncate pt-0.5">{details}</p>}
    </div>
  );
}

function GuardrailCheck({ label, ok }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px]">
      {ok ? (
        <CheckCircle2 className="h-3.5 w-3.5 text-[hsl(var(--success))] flex-shrink-0" />
      ) : (
        <AlertCircle className="h-3.5 w-3.5 text-[hsl(var(--danger))] flex-shrink-0" />
      )}
      <span className={ok ? "text-foreground/90" : "text-muted-foreground"}>{label}</span>
    </div>
  );
}

// ── Main SignalCard ──────────────────────────────────────────────────────────

export function SignalCard({ result, symbol, timeframe, signalId, indicators, className = "" }) {
  if (result?.error) {
    return (
      <div data-testid="signal-card-error" className={`rounded-xl border border-[hsl(var(--danger))]/40 bg-card p-5 ${className}`}>
        <div className="flex items-start gap-2">
          <Sparkles className="h-4 w-4 text-[hsl(var(--danger))]" />
          <div className="font-semibold">{result.model_display} — error</div>
        </div>
        <div className="mt-2 text-sm text-muted-foreground">{result.error}</div>
      </div>
    );
  }

  const s = result?.signal;
  if (!s) return null;

  const cfg = actionColors[s.action] || actionColors.HOLD;
  const ActionIcon = cfg.icon;
  const conf = confidenceLabel(s.confidence);

  // Indicator data can come from top-level prop or from the signal result
  const indicatorData = indicators || result?.indicators || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      data-testid="signal-card"
      className={`rounded-xl border border-border bg-card shadow-[0_1px_0_hsl(var(--border)/0.6),0_18px_50px_hsl(220_18%_2%_/_0.35)] p-5 ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="font-display font-semibold text-base">{symbol}</div>
            <span className="text-xs text-muted-foreground uppercase">{timeframe}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Model: <span className="text-foreground">{result.model_display}</span>
          </div>
        </div>
        <Badge variant="outline" className={`border ${riskColors[s.risk_level] || riskColors.medium}`} data-testid="signal-risk-pill">
          {(s.risk_level || "medium").toUpperCase()} RISK
        </Badge>
      </div>

      {/* Action + Confidence */}
      <div className="mt-5 space-y-2">
        <div className="flex items-center gap-4">
          <div
            data-testid="signal-action-badge"
            className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold uppercase tracking-wide border ${cfg.bg} ${cfg.border} ${cfg.text}`}
          >
            <ActionIcon className="h-4 w-4" />
            {s.action}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground font-medium">Signal Confidence Score</span>
              <span className="font-mono tabular-nums font-semibold" data-testid="signal-confidence-meter">
                <span className="mr-1.5">{conf.emoji}</span>
                <span>{conf.p}%</span>
                <span className={`ml-1 font-sans ${conf.color}`}>({conf.label})</span>
              </span>
            </div>
            <Progress value={conf.p} className="mt-1.5 h-2" />
          </div>
        </div>
        <ConfidenceBreakdownWidget signal={s} />
      </div>

      {/* Price Levels */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Level label="Entry"       value={s.entry_price} onCopy={() => copy(s.entry_price,  "Entry")}       testId="signal-entry-value" />
        <Level label="Stop Loss"   value={s.stop_loss}   onCopy={() => copy(s.stop_loss,    "Stop")}        testId="signal-stop-loss-value" />
        <Level label="Take Profit" value={s.take_profit} onCopy={() => copy(s.take_profit,  "Take profit")} testId="signal-take-profit-value" />
      </div>

      {/* ── AI Trade Intelligence Engine (5 Specialized Agents) ── */}
      <TradeIntelligenceWidget result={result} signal={s} />

      {/* ── WHY Section ── */}
      <WhySection signal={s} indicators={indicatorData} action={s.action} />

      {/* Indicator summary (compact) */}
      <div className="mt-3 text-xs text-muted-foreground">
        <span className="uppercase tracking-wider mr-1">Indicators:</span>
        <span className="text-foreground/90">{s.indicator_summary}</span>
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground gap-3 flex-wrap">
        <span className="uppercase tracking-wider">
          Horizon: <span className="text-foreground">{s.time_horizon}</span>
        </span>
        {signalId ? (
          <ChatDrawer signalId={signalId} triggerLabel="Ask AI follow-up" triggerVariant="outline" />
        ) : null}
      </div>
    </motion.div>
  );
}

function Level({ label, value, onCopy, testId }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 px-3 py-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</span>
        {value ? (
          <button onClick={onCopy} className="text-muted-foreground/70 hover:text-foreground" aria-label={`Copy ${label}`}>
            <Copy className="h-3 w-3" />
          </button>
        ) : null}
      </div>
      <div data-testid={testId} className="mt-1 font-mono tabular-nums text-base font-semibold">
        {value ? formatUSD(value) : "—"}
      </div>
    </div>
  );
}

export function SignalCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-24 bg-muted rounded-full" />
        <div className="h-3 flex-1 bg-muted rounded" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="h-14 bg-muted rounded" />
        <div className="h-14 bg-muted rounded" />
        <div className="h-14 bg-muted rounded" />
      </div>
      <div className="h-24 bg-muted rounded-xl" />
      <div className="h-3 bg-muted rounded w-2/3" />
      <div className="h-3 bg-muted rounded" />
      <div className="h-3 bg-muted rounded w-5/6" />
    </div>
  );
}
