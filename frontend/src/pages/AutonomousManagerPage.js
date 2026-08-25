import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Brain, Sparkles, Zap, RefreshCw, ShieldAlert,
  TrendingUp, TrendingDown, Wallet, Play, CheckCircle2,
  ArrowRight, Activity, DollarSign, Lock
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api, getErrorMessage } from "@/lib/api";
import { formatUSD, formatPercent } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/States";

export default function AutonomousManagerPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningCycle, setRunningCycle] = useState(false);
  const [error, setError] = useState(null);

  const [capitalInput, setCapitalInput] = useState(1000);
  const [autoRebalance, setAutoRebalance] = useState(true);

  const loadStatus = async () => {
    try {
      const { data } = await api.get("/portfolio-manager/status");
      setStatus(data);
      if (data.allocated_capital) setCapitalInput(data.allocated_capital);
      setAutoRebalance(data.auto_rebalance);
    } catch (e) {
      setError(getErrorMessage(e, "Failed to load manager status"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const runCycle = async () => {
    if (runningCycle) return;
    setRunningCycle(true);
    try {
      toast.info("Autonomous AI Engine scanning market assets across 5 Brains…");
      const { data } = await api.post("/portfolio-manager/run-cycle", {
        capital: Number(capitalInput) || 1000,
      });
      toast.success(data.message || "Autonomous rebalance cycle complete!");
      if (data?.cycle) {
        setStatus((prev) => ({
          ...prev,
          recent_cycles: [data.cycle, ...(prev?.recent_cycles || [])],
          cash_buffer: data.cycle.cash_buffer,
        }));
      }
      await loadStatus();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Autonomous cycle failed");
    } finally {
      setRunningCycle(false);
    }
  };

  const saveConfig = async () => {
    try {
      await api.post("/portfolio-manager/config", {
        allocated_capital: Number(capitalInput) || 1000,
        auto_rebalance: autoRebalance,
      });
      toast.success("Manager settings updated");
      loadStatus();
    } catch (e) {
      toast.error("Failed to save configuration");
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-sm text-muted-foreground">
        Initializing Autonomous AI Portfolio Manager…
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadStatus} />;
  }

  const recentCycle = status?.recent_cycles?.[0];
  const evalList = recentCycle?.asset_evaluations || [];
  const investedUsd = recentCycle?.invested_usd || 0;
  const cashBuffer = recentCycle?.cash_buffer ?? status?.cash_buffer ?? 1000;
  const totalEquity = recentCycle?.total_equity ?? cashBuffer + investedUsd;

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">
              Autonomous AI Crypto Portfolio Manager
            </h1>
            <Badge className="bg-primary/15 text-primary border-primary/30 text-xs font-semibold">
              5-Brain Engine
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Allocate trading capital → AI continuously scans, scores, decides, and allocates position sizes automatically.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadStatus}
            data-testid="refresh-manager-btn"
          >
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>

          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold flex items-center gap-2 shadow-sm"
            onClick={runCycle}
            disabled={runningCycle}
            data-testid="run-autonomous-cycle-btn"
          >
            {runningCycle ? (
              <>
                <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Executing 5 Brains…
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 fill-white/20" />
                <span>⚡ Run Autonomous AI Cycle</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ── 100% AI Autonomous Control Banner ─────────────────────────────── */}
      <div className="rounded-xl border border-primary/40 bg-gradient-to-r from-primary/10 via-card to-background p-4 flex items-center justify-between flex-wrap gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
            🤖
          </div>
          <div>
            <div className="font-semibold text-sm text-foreground flex items-center gap-2">
              <span>100% AI Autonomous Trading Mode</span>
              <Badge className="bg-[hsl(var(--success))]/15 text-[hsl(var(--success))] border-[hsl(var(--success))]/40 text-[10px] font-semibold">
                AI Sole Execution
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Inside this Portfolio Manager, <strong>ONLY the AI can BUY, HOLD, or SELL</strong>. You set the allocated capital boundary; the 5-Brain AI analyzes market signals and executes trades continuously in the background.
            </p>
          </div>
        </div>
      </div>

      {/* ── 5-Brain Interactive Pipeline Visualizer ───────────────────────── */}
      <div className="rounded-xl border border-border bg-card p-4 md:p-5">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          <span>The 5 Autonomous AI Brains</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          <PipelineStep step="1" title="Market AI" subtitle="Multi-asset scanner" detail="Scans BTC, ETH, SOL, BNB & indicators" icon={Activity} active />
          <PipelineStep step="2" title="Prediction Score" subtitle="0-100 Composite" detail="Synthesizes 5 sub-agent ratings" icon={Sparkles} active />
          <PipelineStep step="3" title="Decision AI" subtitle="BUY / HOLD / SELL" detail="80+ BUY, 60-79 HOLD, 0-39 SELL" icon={Brain} active />
          <PipelineStep step="4" title="Allocation & Risk" subtitle="Dynamic Sizing" detail="Allocates up to 30% max, keeps cash" icon={ShieldAlert} active />
          <PipelineStep step="5" title="Execution Engine" subtitle="Auto Trade & Log" detail="Fills orders & logs full audit history" icon={Zap} active />
        </div>
      </div>

      {/* ── Capital & Allocation Overview Cards ───────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Allocated Capital Settings */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Wallet className="h-4 w-4 text-primary" /> Allocated Capital
            </span>
            <span className="text-xs font-mono font-bold text-foreground">{formatUSD(status?.allocated_capital)}</span>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Trading Capital Allocation ($ USD)</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min="100"
                step="100"
                value={capitalInput}
                onChange={(e) => setCapitalInput(e.target.value)}
                className="h-9 font-mono text-sm"
              />
              <Button size="sm" variant="secondary" onClick={saveConfig}>Save</Button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              The AI will manage trading decisions strictly within this capital boundary.
            </p>
          </div>

          <div className="pt-2 border-t border-border/50 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Auto-Rebalance Background Mode</span>
            <Switch
              checked={autoRebalance}
              onCheckedChange={(v) => { setAutoRebalance(v); saveConfig(); }}
            />
          </div>
        </div>

        {/* Invested vs Cash Buffer */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 md:col-span-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Portfolio Allocation & Cash Buffer
            </span>
            <span className="text-xs font-mono font-bold text-primary">Total Equity: {formatUSD(totalEquity)}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1">
            <div className="p-3 rounded-lg bg-muted/30 border border-border/60">
              <div className="text-[11px] text-muted-foreground mb-1">Invested Allocation</div>
              <div className="text-lg font-mono font-semibold text-foreground">{formatUSD(investedUsd)}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                {totalEquity > 0 ? ((investedUsd / totalEquity) * 100).toFixed(1) : 0}% of capital
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/30 border border-border/60">
              <div className="text-[11px] text-muted-foreground mb-1">Cash Buffer (Preserved)</div>
              <div className="text-lg font-mono font-semibold text-[hsl(var(--success))]">{formatUSD(cashBuffer)}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                {totalEquity > 0 ? ((cashBuffer / totalEquity) * 100).toFixed(1) : 100}% cash safety
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/30 border border-border/60 col-span-2 sm:col-span-1">
              <div className="text-[11px] text-muted-foreground mb-1">Active Positions</div>
              <div className="text-lg font-mono font-semibold text-foreground">
                {status?.positions?.length || 0} Assets
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">
                Max 30% per asset limit
              </div>
            </div>
          </div>

          {/* Allocation Bar */}
          <div className="space-y-1 pt-1">
            <div className="flex justify-between text-[11px] text-muted-foreground">
              <span>Capital Breakdown</span>
              <span>Invested: {formatUSD(investedUsd)} | Cash: {formatUSD(cashBuffer)}</span>
            </div>
            <Progress value={totalEquity > 0 ? (investedUsd / totalEquity) * 100 : 0} className="h-2 bg-muted" />
          </div>
        </div>
      </div>

      {/* ── Multi-Asset Prediction Score Board ─────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card p-4 md:p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="font-display font-semibold text-lg tracking-tight">Multi-Asset Prediction Score Board</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Live AI scores & dynamic capital allocations for tracked crypto assets.
            </p>
          </div>
          {recentCycle && (
            <span className="text-xs text-muted-foreground font-mono">
              Last Rebalance: {new Date(recentCycle.created_at).toLocaleTimeString()}
            </span>
          )}
        </div>

        {evalList.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground border border-dashed rounded-lg">
            No autonomous cycle run yet. Click <strong className="text-foreground">⚡ Run Autonomous AI Cycle</strong> above to scan & score the market.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {evalList.map((item) => {
              const score = item.prediction_score || 0;
              const dec = item.decision || {};
              const action = dec.action || "WAIT";

              const isBuy = action === "BUY";
              const isSell = action === "SELL";
              const isHold = action === "HOLD";

              const badgeColor = isBuy
                ? "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))] border-[hsl(var(--success))]/40"
                : isSell
                ? "bg-[hsl(var(--danger))]/15 text-[hsl(var(--danger))] border-[hsl(var(--danger))]/40"
                : "bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))] border-[hsl(var(--warning))]/40";

              return (
                <div key={item.symbol} className="p-3.5 rounded-xl border border-border/80 bg-background/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm text-foreground flex items-center gap-2">
                      <span>{item.symbol}</span>
                      <span className="font-mono text-xs text-muted-foreground">${item.current_price?.toLocaleString()}</span>
                    </div>
                    <Badge variant="outline" className={`text-xs font-semibold ${badgeColor}`}>
                      {dec.badge || action}
                    </Badge>
                  </div>

                  {/* Prediction Score Gauge */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground font-medium">AI Prediction Score</span>
                      <span className="font-mono font-bold text-foreground">{score} / 100</span>
                    </div>
                    <Progress value={score} className="h-2 bg-muted" />
                  </div>

                  {/* Allocation & Details */}
                  <div className="text-xs text-muted-foreground leading-relaxed pt-1 border-t border-border/40">
                    <div>{item.execution_details}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Autonomous Audit Log Timeline ──────────────────────────────────── */}
      {status?.recent_cycles?.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 md:p-5 space-y-3">
          <h2 className="font-display font-semibold text-base tracking-tight">Rebalance Audit History</h2>
          <div className="space-y-2">
            {status.recent_cycles.slice(0, 5).map((c) => (
              <div key={c.id} className="p-3 rounded-lg bg-muted/20 border border-border/50 text-xs flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[hsl(var(--success))]" />
                  <span className="font-mono text-muted-foreground">
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                  <span className="text-foreground font-medium">
                    {c.actions_taken?.length > 0
                      ? `Executed ${c.actions_taken.length} trade actions`
                      : "Maintained cash buffer & positions (No changes)"}
                  </span>
                </div>
                <div className="font-mono text-muted-foreground">
                  Cash: {formatUSD(c.cash_buffer)} | Equity: {formatUSD(c.total_equity)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PipelineStep({ step, title, subtitle, detail, icon: Icon, active }) {
  return (
    <div className="p-3 rounded-lg border border-border/70 bg-background/50 space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-mono font-bold text-primary">Brain #{step}</span>
        <Icon className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="font-semibold text-foreground text-xs">{title}</div>
      <div className="text-[11px] text-muted-foreground font-medium">{subtitle}</div>
      <div className="text-[10px] text-muted-foreground/80 leading-tight pt-0.5">{detail}</div>
    </div>
  );
}
