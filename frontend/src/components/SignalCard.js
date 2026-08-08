import React from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus, Copy, Sparkles, MessageCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatUSD } from "@/lib/format";
import { toast } from "sonner";
import { ChatDrawer } from "@/components/ChatDrawer";

const actionColors = {
  BUY:  { bg: "bg-[hsl(var(--success))]/12", border: "border-[hsl(var(--success))]/40", text: "text-[hsl(var(--success))]", icon: TrendingUp },
  SELL: { bg: "bg-[hsl(var(--danger))]/12",  border: "border-[hsl(var(--danger))]/40",  text: "text-[hsl(var(--danger))]",  icon: TrendingDown },
  HOLD: { bg: "bg-muted/60",                 border: "border-border",                    text: "text-muted-foreground",     icon: Minus },
};

const riskColors = {
  low:    "bg-[hsl(var(--success))]/12 text-[hsl(var(--success))] border-[hsl(var(--success))]/30",
  medium: "bg-[hsl(var(--warning))]/12 text-[hsl(var(--warning))] border-[hsl(var(--warning))]/30",
  high:   "bg-[hsl(var(--danger))]/12 text-[hsl(var(--danger))] border-[hsl(var(--danger))]/30",
};

function confidenceLabel(c) {
  const p = Math.round((c || 0) * 100);
  if (p >= 80) return { p, label: "Very high" };
  if (p >= 65) return { p, label: "High" };
  if (p >= 50) return { p, label: "Moderate" };
  if (p >= 35) return { p, label: "Low" };
  return { p, label: "Very low" };
}

function copy(value, name) {
  try {
    navigator.clipboard.writeText(String(value));
    toast.success(`${name} copied`);
  } catch { /* no-op */ }
}

export function SignalCard({ result, symbol, timeframe, signalId, className = "" }) {
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      data-testid="signal-card"
      className={`rounded-xl border border-border bg-card shadow-[0_1px_0_hsl(var(--border)/0.6),0_18px_50px_hsl(220_18%_2%_/_0.35)] p-5 ${className}`}
    >
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

      {/* Big Action */}
      <div className="mt-5 flex items-center gap-4">
        <div
          data-testid="signal-action-badge"
          className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold uppercase tracking-wide border ${cfg.bg} ${cfg.border} ${cfg.text}`}
        >
          <ActionIcon className="h-4 w-4" />
          {s.action}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-mono tabular-nums" data-testid="signal-confidence-meter">{conf.p}% <span className="text-muted-foreground">({conf.label})</span></span>
          </div>
          <Progress value={conf.p} className="mt-1 h-2" />
        </div>
      </div>

      {/* Levels */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Level label="Entry"        value={s.entry_price}  onCopy={() => copy(s.entry_price, "Entry")}  testId="signal-entry-value" />
        <Level label="Stop Loss"    value={s.stop_loss}    onCopy={() => copy(s.stop_loss, "Stop")}    testId="signal-stop-loss-value" />
        <Level label="Take Profit"  value={s.take_profit}  onCopy={() => copy(s.take_profit, "Take profit")}  testId="signal-take-profit-value" />
      </div>

      {/* Key factors */}
      {s.key_factors?.length ? (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Key factors</div>
          <div className="flex flex-wrap gap-1.5">
            {s.key_factors.map((k, i) => (
              <Badge key={i} variant="secondary" className="font-normal">{k}</Badge>
            ))}
          </div>
        </div>
      ) : null}

      {/* Reasoning */}
      <div className="mt-4">
        <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">AI reasoning</div>
        <p className="text-sm text-muted-foreground leading-relaxed">{s.reasoning}</p>
      </div>

      {/* Indicators summary */}
      <div className="mt-3 text-xs text-muted-foreground">
        <span className="uppercase tracking-wider mr-1">Indicators:</span>
        <span className="text-foreground/90">{s.indicator_summary}</span>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground gap-3 flex-wrap">
        <span className="uppercase tracking-wider">Horizon: <span className="text-foreground">{s.time_horizon}</span></span>
        {signalId ? (
          <ChatDrawer signalId={signalId} triggerLabel="Chat with AI" triggerVariant="outline" />
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
      <div className="h-3 bg-muted rounded w-2/3" />
      <div className="h-3 bg-muted rounded" />
      <div className="h-3 bg-muted rounded w-5/6" />
    </div>
  );
}
