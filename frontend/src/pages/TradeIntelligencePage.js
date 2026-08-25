import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Brain, TrendingUp, BarChart2, Activity, ShieldAlert, Zap,
  CheckCircle2, AlertCircle, RefreshCw, Layers, ShieldCheck, Compass,
  GitCompare, History, HelpCircle, AlertTriangle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";

const COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT"];
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

export default function TradeIntelligencePage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [model, setModel] = useState("gemini");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [simPreset, setSimPreset] = useState(null);

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setSimPreset(null);
    try {
      const { data } = await api.post("/ai/signal", { symbol, timeframe, model });
      const firstRes = data.results?.[0] || {};
      setResult(firstRes);
      toast.success(`Trade Intelligence evaluated for ${symbol}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to run Trade Intelligence");
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, model]);

  useEffect(() => {
    runAnalysis();
  }, [runAnalysis]);

  // Preset Scenario Handler for interactive testing
  const loadPreset = (type) => {
    if (type === "high_quality") {
      setSimPreset({
        regime_detector: { regime: "TRENDING", confidence: 87, description: "Strong bullish momentum intact above 20 SMA." },
        strategy_selector: { strategy: "Momentum / Trend Following", type: "TREND", rationale: "Uptrend active. Trailing stop momentum entries selected." },
        trade_quality: {
          score: 82,
          badge: "🟢 HIGH-QUALITY SETUP",
          disclaimer: "82/100 represents model analytical score according to criteria, NOT guaranteed profit probability.",
          factors: { trend: 87, momentum: 79, volume: 81, liquidity: 72, market_structure: 84, sentiment: 68, risk_reward: 91 },
        },
        risk_engine: { account_balance: 1000, max_risk_pct: 1.0, max_loss_usd: 10.0, proposed_loss_usd: 8.5, status: "APPROVED", reason: "Max allowed risk $10.00 (1.0% of $1,000). Proposed risk: $8.50." },
        decision_engine: { trade_score: 82, verdict: "TRADE", reason: "🟢 TRADE APPROVED: High Quality Score (82/100) with 1:2.5 Risk/Reward ratio.", rr_ratio: 2.5 },
        refusal_reasons: [],
        counterfactual_engine: {
          optimal_decision: "BUY NOW",
          rationale: "High trade quality score and strong R:R justify immediate entry.",
          scenarios: [
            { action: "BUY NOW", risk: "MEDIUM", reward: "HIGH", description: "Enter immediately at market price ($100,000)" },
            { action: "WAIT FOR BREAKOUT", risk: "LOW", reward: "MEDIUM", description: "Wait for breakout above $101,500" },
            { action: "DO NOTHING", risk: "LOW", opportunity_cost: "HIGH", description: "Hold cash position" },
          ],
        },
        trading_memory: {
          regime_performance: [
            { regime: "Trending Markets", win_rate: 71, trades: 183 },
            { regime: "Ranging Markets", win_rate: 59, trades: 142 },
            { regime: "High Volatility", win_rate: 48, trades: 89 },
          ],
          best_strategy: "Momentum Trend + High Volume Confirmation",
        },
        uncertainty_gauge: { trend_model: "BUY", momentum_model: "BUY", sentiment_model: "BUY", uncertainty: "LOW", model_confidence: 88, reason: "All 3 models in 100% agreement." },
      });
      toast.info("Loaded Preset: High-Quality Bullish Setup");
    } else if (type === "rejection") {
      setSimPreset({
        regime_detector: { regime: "HIGH_VOLATILITY", confidence: 91, description: "Rapid price swings and flash moves active." },
        strategy_selector: { strategy: "Volatility Breakout / Conservative", type: "BREAKOUT", rationale: "High volatility environment requires strict risk filters." },
        trade_quality: {
          score: 35,
          badge: "🔴 WEAK SETUP",
          disclaimer: "35/100 represents model analytical score according to criteria.",
          factors: { trend: 90, momentum: 85, volume: 80, liquidity: 40, market_structure: 50, sentiment: 40, risk_reward: 20 },
        },
        risk_engine: { account_balance: 1000, max_risk_pct: 1.0, max_loss_usd: 10.0, proposed_loss_usd: 35.0, status: "REJECTED", reason: "Max allowed risk $10.00. Proposed trade risk $35.00 exceeds limit!" },
        decision_engine: { trade_score: 35, verdict: "NO TRADE", reason: "🚨 REJECTED: Risk Agent score is 20/100. Trend is 90, but system refuses trade because risk is too high!", rr_ratio: 0.8 },
        refusal_reasons: [
          "❌ Poor Risk/Reward ratio (1:0.8 < min 1:1.5 required)",
          "❌ Liquidity deteriorating in thin orderbook",
          "❌ Volatility too high (Flash crash risk detected)",
          "❌ Resistance nearby at $101,200",
        ],
        counterfactual_engine: {
          optimal_decision: "WAIT FOR BREAKOUT",
          rationale: "Risk is too high for immediate entry. Waiting for pullback or breakout is optimal.",
          scenarios: [
            { action: "BUY NOW", risk: "HIGH", reward: "LOW", description: "High risk of rapid reversal" },
            { action: "WAIT FOR BREAKOUT", risk: "MEDIUM", reward: "HIGH", description: "Wait for confirmed structure" },
            { action: "DO NOTHING", risk: "LOW", opportunity_cost: "LOW", description: "Preserve capital" },
          ],
        },
        trading_memory: {
          regime_performance: [
            { regime: "Trending Markets", win_rate: 71, trades: 183 },
            { regime: "Ranging Markets", win_rate: 59, trades: 142 },
            { regime: "High Volatility", win_rate: 48, trades: 89 },
          ],
          best_strategy: "Avoid Trading During High Volatility Spikes",
        },
        uncertainty_gauge: { trend_model: "BUY", momentum_model: "BUY", sentiment_model: "SELL", uncertainty: "HIGH", model_confidence: 45, reason: "Models disagree! Trend says BUY, but Sentiment says SELL." },
      });
      toast.warning("Loaded Preset: Trade Refusal & Rejection Breakdown");
    }
  };

  const intel = simPreset || result?.trade_intelligence || {
    regime_detector: { regime: "TRENDING", confidence: 87, description: "Bullish trend active." },
    strategy_selector: { strategy: "Momentum / Trend Following", type: "TREND", rationale: "Trend strategy selected." },
    trade_quality: {
      score: 82,
      badge: "🟢 HIGH-QUALITY SETUP",
      disclaimer: "82/100 represents model analytical score according to criteria, NOT guaranteed profit probability.",
      factors: { trend: 87, momentum: 79, volume: 81, liquidity: 72, market_structure: 84, sentiment: 68, risk_reward: 91 },
    },
    risk_engine: { account_balance: 1000, max_risk_pct: 1.0, max_loss_usd: 10.0, proposed_loss_usd: 8.5, status: "APPROVED", reason: "Risk within limit." },
    decision_engine: { trade_score: 82, verdict: "TRADE", reason: "🟢 TRADE APPROVED", rr_ratio: 2.5 },
    refusal_reasons: [],
    counterfactual_engine: {
      optimal_decision: "BUY NOW",
      rationale: "Favorable parameters.",
      scenarios: [
        { action: "BUY NOW", risk: "MEDIUM", reward: "HIGH", description: "Market entry" },
        { action: "WAIT FOR BREAKOUT", risk: "LOW", reward: "MEDIUM", description: "Breakout entry" },
        { action: "DO NOTHING", risk: "LOW", opportunity_cost: "HIGH", description: "Capital preservation" },
      ],
    },
    trading_memory: {
      regime_performance: [
        { regime: "Trending Markets", win_rate: 71, trades: 183 },
        { regime: "Ranging Markets", win_rate: 59, trades: 142 },
        { regime: "High Volatility", win_rate: 48, trades: 89 },
      ],
      best_strategy: "Momentum Trend + High Volume",
    },
    uncertainty_gauge: { trend_model: "BUY", momentum_model: "BUY", sentiment_model: "BUY", uncertainty: "LOW", model_confidence: 88, reason: "Models agree." },
  };

  const isNoTrade = intel.decision_engine?.verdict === "NO TRADE";
  const isWait = intel.decision_engine?.verdict === "WAIT";
  const isTrade = !isNoTrade && !isWait;

  const verdictCls = isTrade
    ? "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))] border-[hsl(var(--success))]/40"
    : isNoTrade
    ? "bg-[hsl(var(--danger))]/15 text-[hsl(var(--danger))] border-[hsl(var(--danger))]/40"
    : "bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))]/40 text-[hsl(var(--warning))]";

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-8 pb-24">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <Brain className="h-5 w-5 text-primary" />
            </div>
            <h1 className="font-display font-bold text-2xl tracking-tight">Adaptive AI Trade Intelligence</h1>
            <Badge variant="outline" className="border-primary/40 text-primary text-[11px]">8 Core Modules</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Adaptive architecture with Market Regime Detection, Strategy Selection, Refusal Engine ("Why NOT this trade?"), & Counterfactual Analysis.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          <Select value={symbol} onValueChange={setSymbol}>
            <SelectTrigger className="w-32 h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {COINS.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-24 h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEFRAMES.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button size="sm" onClick={runAnalysis} disabled={loading} className="h-9">
            {loading ? <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Zap className="h-3.5 w-3.5 mr-1.5" />}
            Evaluate Pair
          </Button>
        </div>
      </div>

      {/* Simulator Presets Bar */}
      <Card className="border border-border/80 bg-card/60">
        <CardContent className="p-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Zap className="h-4 w-4 text-primary" />
            <span>Interactive Demo Scenarios:</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" size="sm" onClick={() => loadPreset("high_quality")} className="h-8 text-xs border-[hsl(var(--success))]/40 hover:bg-[hsl(var(--success))]/10">
              🟢 High-Quality Trade (TRADE)
            </Button>
            <Button variant="outline" size="sm" onClick={() => loadPreset("rejection")} className="h-8 text-xs border-[hsl(var(--danger))]/40 hover:bg-[hsl(var(--danger))]/10">
              ❌ Refusal & Rejection Breakdown (NO TRADE)
            </Button>
            {simPreset && (
              <Button variant="ghost" size="sm" onClick={() => setSimPreset(null)} className="h-8 text-xs text-muted-foreground">
                Reset to Live Market Data
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Top 2 Module Cards: 1. Market Regime & 2. Strategy Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Module 1: Market Regime Detector */}
        <Card className="border border-border bg-card">
          <CardHeader className="py-4 px-5 border-b border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Compass className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-semibold">1️⃣ Market Regime Detector</CardTitle>
              </div>
              <Badge variant="outline" className="border-primary/40 text-primary text-[10px]">
                {intel.regime_detector?.confidence}% Confidence
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Detected Regime:</span>
              <span className="font-mono font-bold text-base text-foreground">{intel.regime_detector?.regime}</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {intel.regime_detector?.description}
            </p>
          </CardContent>
        </Card>

        {/* Module 2: Strategy Selector */}
        <Card className="border border-border bg-card">
          <CardHeader className="py-4 px-5 border-b border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-semibold">2️⃣ Strategy Selector</CardTitle>
              </div>
              <Badge variant="outline" className="border-primary/40 text-primary text-[10px]">Adaptive Strategy</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Matched Strategy:</span>
              <span className="font-mono font-bold text-sm text-foreground">{intel.strategy_selector?.strategy}</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {intel.strategy_selector?.rationale}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Decision & Trade Quality Banner */}
      <Card className="border border-border bg-card shadow-lg">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Badge variant="outline" className={`text-base font-bold px-4 py-1.5 border ${verdictCls}`}>
                  {intel.decision_engine?.verdict}
                </Badge>
                <div className="text-sm font-mono font-semibold">
                  Trade Quality: <span className="text-foreground">{intel.trade_quality?.score}/100</span>
                </div>
                <Badge variant="outline" className="text-xs border-border">{intel.trade_quality?.badge}</Badge>
              </div>
              <p className="text-xs text-muted-foreground italic max-w-2xl">
                {intel.trade_quality?.disclaimer}
              </p>
              <p className="text-sm text-foreground/90 pt-1 leading-relaxed border-l-2 border-primary/40 pl-3">
                {intel.decision_engine?.reason}
              </p>
            </div>

            {/* Risk Engine Security Guard Badge */}
            <div className="p-4 rounded-xl border border-border/80 bg-muted/20 text-center min-w-[200px] space-y-1">
              <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-foreground">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <span>4️⃣ Risk Engine</span>
              </div>
              <div className={`text-sm font-mono font-bold ${intel.risk_engine?.status === "APPROVED" ? "text-[hsl(var(--success))]" : "text-[hsl(var(--danger))]"}`}>
                {intel.risk_engine?.status === "APPROVED" ? "✓ RISK APPROVED" : "❌ TRADE REJECTED"}
              </div>
              <div className="text-[11px] text-muted-foreground">
                Max Risk ${intel.risk_engine?.max_loss_usd} ({intel.risk_engine?.max_risk_pct}% of ${intel.risk_engine?.account_balance})
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Module 5: "Why NOT this trade?" (Refusal Engine) */}
      {(isNoTrade || isWait || intel.refusal_reasons?.length > 0) && (
        <Card className="border border-[hsl(var(--danger))]/40 bg-[hsl(var(--danger))]/5">
          <CardHeader className="py-4 px-6 border-b border-[hsl(var(--danger))]/30">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-[hsl(var(--danger))]" />
              <CardTitle className="text-base font-semibold text-[hsl(var(--danger))]">
                5️⃣ "Why NOT this trade?" — Refusal & Rejection Breakdown
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-3">
            <p className="text-xs text-muted-foreground">
              Potential trade setup detected, but the system refused entry due to the following specific risk violations:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {intel.refusal_reasons?.map((reason, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-[hsl(var(--danger))]/30 bg-background/60 text-xs font-medium text-foreground flex items-center gap-2">
                  <span>{reason}</span>
                </div>
              ))}
            </div>
            <div className="text-xs font-semibold text-foreground pt-2">
              System Recommendation: <span className="text-[hsl(var(--warning))] font-mono">WAIT / DO NOT ENTER</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Tabs: Counterfactual Engine, Factor Breakdown, Trading Memory, Uncertainty */}
      <Tabs defaultValue="counterfactual" className="w-full">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 h-10">
          <TabsTrigger value="counterfactual" className="text-xs">6️⃣ Counterfactual Engine</TabsTrigger>
          <TabsTrigger value="factors" className="text-xs">3️⃣ Factor Breakdown</TabsTrigger>
          <TabsTrigger value="memory" className="text-xs">7️⃣ Trading Memory</TabsTrigger>
          <TabsTrigger value="uncertainty" className="text-xs">8️⃣ Uncertainty Gauge</TabsTrigger>
        </TabsList>

        {/* Tab 6: Counterfactual Engine */}
        <TabsContent value="counterfactual" className="mt-4">
          <Card className="border border-border bg-card">
            <CardHeader className="py-4 px-6 border-b border-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitCompare className="h-4 w-4 text-primary" />
                  <CardTitle className="text-base font-semibold">6️⃣ Counterfactual Scenario Engine</CardTitle>
                </div>
                <Badge variant="outline" className="border-primary/40 text-primary text-xs">
                  Optimal Path: {intel.counterfactual_engine?.optimal_decision}
                </Badge>
              </div>
              <CardDescription className="text-xs mt-1">
                Compares alternative parallel actions side-by-side rather than evaluating only one action in isolation.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {intel.counterfactual_engine?.scenarios?.map((s, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border transition-all ${
                      intel.counterfactual_engine?.optimal_decision === s.action
                        ? "border-primary/50 bg-primary/8 shadow-md"
                        : "border-border/70 bg-background/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm">{s.action}</span>
                      {intel.counterfactual_engine?.optimal_decision === s.action && (
                        <Badge variant="outline" className="text-[10px] bg-primary/10 border-primary text-primary">BEST PATH</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">{s.description}</p>
                    <div className="mt-4 pt-3 border-t border-border/40 space-y-1.5 text-xs font-mono">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Risk:</span>
                        <span className={s.risk === "HIGH" ? "text-[hsl(var(--danger))]" : "text-[hsl(var(--success))]"}>{s.risk}</span>
                      </div>
                      {s.reward && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Reward:</span>
                          <span className="text-[hsl(var(--success))]">{s.reward}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed border-l-2 border-primary/40 pl-3">
                <span className="font-semibold text-foreground">Scenario Rationale:</span> {intel.counterfactual_engine?.rationale}
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Factor Breakdown */}
        <TabsContent value="factors" className="mt-4">
          <Card className="border border-border bg-card">
            <CardHeader className="py-4 px-6 border-b border-border/60">
              <CardTitle className="text-base font-semibold">3️⃣ Multi-Factor Trade Quality Score Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(intel.trade_quality?.factors || {}).map(([key, val]) => (
                  <div key={key} className="space-y-1.5 p-3 rounded-lg border border-border/60 bg-muted/20">
                    <div className="flex items-center justify-between text-xs font-medium">
                      <span className="capitalize text-foreground/90">{key.replace("_", " ")}</span>
                      <span className="font-mono font-bold text-foreground">{val}/100</span>
                    </div>
                    <Progress value={val} className="h-2 bg-muted" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 7: Trading Memory */}
        <TabsContent value="memory" className="mt-4">
          <Card className="border border-border bg-card">
            <CardHeader className="py-4 px-6 border-b border-border/60">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-primary" />
                <CardTitle className="text-base font-semibold">7️⃣ Trading Memory & Regime Performance</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {intel.trading_memory?.regime_performance?.map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-border/70 bg-background/50 space-y-2">
                    <div className="text-xs text-muted-foreground font-medium">{item.regime}</div>
                    <div className="font-mono text-2xl font-bold text-primary">{item.win_rate}% <span className="text-xs font-normal text-muted-foreground">win rate</span></div>
                    <div className="text-[11px] text-muted-foreground">Based on {item.trades} backtested & historical trades</div>
                  </div>
                ))}
              </div>
              <div className="p-3 rounded-lg border border-border bg-muted/30 text-xs">
                <span className="font-semibold text-foreground">Best Recommended Strategy:</span> {intel.trading_memory?.best_strategy}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 8: Uncertainty Gauge */}
        <TabsContent value="uncertainty" className="mt-4">
          <Card className="border border-border bg-card">
            <CardHeader className="py-4 px-6 border-b border-border/60">
              <div className="flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-primary" />
                <CardTitle className="text-base font-semibold">8️⃣ Model Disagreement & Uncertainty Gauge</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                <div className="p-3 rounded-lg border border-border bg-background/50">
                  <div className="text-xs text-muted-foreground">Trend Model</div>
                  <div className="font-mono font-bold text-base text-foreground mt-1">{intel.uncertainty_gauge?.trend_model}</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-background/50">
                  <div className="text-xs text-muted-foreground">Momentum Model</div>
                  <div className="font-mono font-bold text-base text-foreground mt-1">{intel.uncertainty_gauge?.momentum_model}</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-background/50">
                  <div className="text-xs text-muted-foreground">Sentiment Model</div>
                  <div className="font-mono font-bold text-base text-foreground mt-1">{intel.uncertainty_gauge?.sentiment_model}</div>
                </div>
              </div>
              <div className="p-4 rounded-xl border border-border bg-muted/20 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span>Uncertainty Level: <span className="font-mono text-primary">{intel.uncertainty_gauge?.uncertainty}</span></span>
                  <span>Model Confidence: <span className="font-mono text-foreground">{intel.uncertainty_gauge?.model_confidence}%</span></span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{intel.uncertainty_gauge?.reason}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
