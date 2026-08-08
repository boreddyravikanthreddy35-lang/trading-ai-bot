import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Bot as BotIcon, Plus, Play, Pause, Trash2, Sparkles,
  RefreshCw, Settings2, TrendingUp, TrendingDown, Minus, ShieldAlert, X
} from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { EmptyState, ErrorState } from "@/components/States";

const SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
];
const TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"];

export default function BotsPage() {
  const [bots, setBots] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = async () => {
    setError(null);
    try {
      const { data } = await api.get("/bots");
      setBots(data.bots || []);
      if (selected) {
        const found = (data.bots || []).find((b) => b.id === selected.id);
        setSelected(found || null);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load bots");
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">AI Trading Bots</h1>
          <p className="text-sm text-muted-foreground mt-1">Let Claude or Gemini scan the market on a schedule and auto-execute high-confidence signals.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-bots-btn"><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
          <BotFormDialog onSaved={load} />
        </div>
      </div>

      <div className="rounded-lg border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/8 px-4 py-2.5 mb-5 flex items-start gap-2 text-xs">
        <ShieldAlert className="h-4 w-4 text-[hsl(var(--warning))] shrink-0 mt-0.5" />
        <div className="text-muted-foreground">
          Bots trade on your <strong className="text-foreground">paper portfolio by default</strong>. Enable “Use testnet” only after configuring Binance testnet keys in Settings. HOLD signals or trades below your confidence threshold are skipped automatically.
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {bots === null ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : bots.length === 0 ? (
        <EmptyState
          title="No bots yet"
          description="Create your first AI trading bot. Choose the coin, model, confidence threshold, and how often it should run."
          action={<BotFormDialog onSaved={load} triggerLabel="Create your first bot" />}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 space-y-3">
            {bots.map((b) => (
              <BotCard
                key={b.id}
                bot={b}
                onClick={() => setSelected(b)}
                active={selected?.id === b.id}
                onChange={load}
              />
            ))}
          </div>
          <div className="lg:col-span-7">
            {selected ? (
              <BotRunsPanel bot={selected} onChange={load} onClose={() => setSelected(null)} />
            ) : (
              <div className="rounded-xl border border-dashed border-border p-8 text-center text-muted-foreground">
                Select a bot on the left to view its run history and controls.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function BotCard({ bot, onClick, active, onChange }) {
  const toggle = async (e) => {
    e.stopPropagation();
    try {
      await api.patch(`/bots/${bot.id}`, { active: !bot.active });
      toast.success(bot.active ? "Bot paused" : "Bot started");
      onChange();
    } catch (err) { toast.error(err?.response?.data?.detail || "Update failed"); }
  };
  const del = async (e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete bot "${bot.name}"?`)) return;
    try {
      await api.delete(`/bots/${bot.id}`);
      toast.success("Bot deleted");
      onChange();
    } catch { toast.error("Delete failed"); }
  };
  const runNow = async (e) => {
    e.stopPropagation();
    try {
      toast.info(`Running ${bot.name}…`);
      const { data } = await api.post(`/bots/${bot.id}/run`);
      const status = data.status;
      if (status === "executed") toast.success(`Bot fired: ${data.signal?.action} ${bot.symbol}`);
      else if (status === "skipped") toast(`Skipped: ${data.skip_reason || "low confidence"}`);
      else toast.error(`Bot error: ${data.error || "unknown"}`);
      onChange();
    } catch (err) { toast.error(err?.response?.data?.detail || "Run failed"); }
  };

  return (
    <div
      onClick={onClick}
      data-testid={`bot-card-${bot.id}`}
      className={`rounded-xl border ${active ? "border-primary/60" : "border-border"} bg-card p-4 cursor-pointer transition-colors hover:border-primary/40`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <BotIcon className="h-4 w-4 text-primary" />
          <div className="font-display font-semibold truncate">{bot.name}</div>
        </div>
        <Badge variant="outline" className={bot.active ? "text-[hsl(var(--success))] border-[hsl(var(--success))]/40" : "text-muted-foreground"}>
          {bot.active ? "Active" : "Paused"}
        </Badge>
      </div>
      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-muted-foreground">
        <Kv label="Symbol" value={bot.symbol} />
        <Kv label="Timeframe" value={bot.timeframe} />
        <Kv label="Model" value={bot.model === "claude" ? "Claude" : "Gemini"} />
        <Kv label="Every" value={`${bot.interval_minutes}m`} />
        <Kv label="Size" value={formatUSD(bot.size_usd)} />
        <Kv label="Min conf." value={`${Math.round(bot.min_confidence * 100)}%`} />
        <Kv label="Actions" value={(bot.allow_actions || []).join("/")} />
        <Kv label="Mode" value={bot.use_testnet ? "Testnet" : "Paper"} />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Button size="sm" variant="outline" onClick={runNow} data-testid="bot-run-now-btn"><Play className="h-3.5 w-3.5 mr-1.5" /> Run now</Button>
        <Button size="sm" variant="outline" onClick={toggle} data-testid="bot-toggle-btn">
          {bot.active ? <><Pause className="h-3.5 w-3.5 mr-1.5" /> Pause</> : <><Play className="h-3.5 w-3.5 mr-1.5" /> Start</>}
        </Button>
        <div className="flex-1" />
        <Button size="sm" variant="ghost" onClick={del} data-testid="bot-delete-btn"><Trash2 className="h-4 w-4 text-muted-foreground" /></Button>
      </div>
    </div>
  );
}

function Kv({ label, value }) {
  return (
    <div>
      <div className="uppercase tracking-wider text-[10px]">{label}</div>
      <div className="text-sm text-foreground font-mono tabular-nums">{value}</div>
    </div>
  );
}

function BotRunsPanel({ bot, onChange, onClose }) {
  const [runs, setRuns] = useState([]);
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setBusy(true);
    try {
      const { data } = await api.get(`/bots/${bot.id}/runs`);
      setRuns(data.runs || []);
    } catch { /* noop */ } finally { setBusy(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [bot.id]);

  return (
    <div className="rounded-xl border border-border bg-card" data-testid="bot-runs-panel">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BotIcon className="h-4 w-4 text-primary" />
          <div className="font-display font-semibold">{bot.name} — recent runs</div>
        </div>
        <div className="flex items-center gap-2">
          <BotFormDialog bot={bot} onSaved={onChange} triggerLabel={<><Settings2 className="h-4 w-4 mr-2" /> Edit</>} triggerVariant="outline" />
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
      </div>
      {busy && !runs.length ? (
        <div className="p-4 text-sm text-muted-foreground">Loading runs…</div>
      ) : !runs.length ? (
        <div className="p-6 text-center text-sm text-muted-foreground">No runs yet. Click “Run now” on the card to fire a manual cycle.</div>
      ) : (
        <div className="max-h-[560px] overflow-y-auto">
          {runs.map((r) => <RunRow key={r.id} run={r} />)}
        </div>
      )}
    </div>
  );
}

function RunRow({ run }) {
  const sig = run.signal;
  const status = run.status;
  const icon = sig?.action === "BUY" ? <TrendingUp className="h-4 w-4 text-[hsl(var(--up))]" />
             : sig?.action === "SELL" ? <TrendingDown className="h-4 w-4 text-[hsl(var(--down))]" />
             : <Minus className="h-4 w-4 text-muted-foreground" />;
  const trade = run.execution?.trade || run.execution?.fallback_paper?.trade;
  return (
    <div className="px-4 py-3 border-b border-border/60 text-sm">
      <div className="flex items-center gap-3">
        {icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium">{sig?.action || (status === "error" ? "ERROR" : "—")}</span>
            {sig ? <Badge variant="outline" className="text-[10px]">{Math.round((sig.confidence || 0) * 100)}%</Badge> : null}
            <span className="text-xs text-muted-foreground">{run.symbol} · {run.timeframe} · {run.model}</span>
          </div>
          {status === "executed" && trade ? (
            <div className="text-xs text-muted-foreground">Filled {trade.quantity?.toFixed?.(6)} @ ${trade.price?.toLocaleString?.()}</div>
          ) : status === "skipped" ? (
            <div className="text-xs text-muted-foreground">Skipped — {run.skip_reason || "low confidence"}</div>
          ) : status === "error" ? (
            <div className="text-xs text-[hsl(var(--danger))]">Error — {run.error}</div>
          ) : null}
        </div>
        <div className="text-[11px] text-muted-foreground whitespace-nowrap">{shortDate(run.created_at)}</div>
      </div>
    </div>
  );
}


function BotFormDialog({ bot, onSaved, triggerLabel = <><Plus className="h-4 w-4 mr-2" /> New bot</>, triggerVariant = "default" }) {
  const isEdit = !!bot;
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: bot?.name || "AI Bot",
    symbol: bot?.symbol || "BTCUSDT",
    timeframe: bot?.timeframe || "1h",
    model: bot?.model || "claude",
    interval_minutes: bot?.interval_minutes || 60,
    size_usd: bot?.size_usd || 100,
    min_confidence: bot?.min_confidence || 0.65,
    use_testnet: bot?.use_testnet || false,
    max_daily_loss: bot?.max_daily_loss || 500,
    active: bot?.active ?? false,
    allow_buy: (bot?.allow_actions || ["BUY", "SELL"]).includes("BUY"),
    allow_sell: (bot?.allow_actions || ["BUY", "SELL"]).includes("SELL"),
  });

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.allow_buy && !form.allow_sell) return toast.error("Allow at least BUY or SELL");
    const payload = {
      name: form.name.trim(),
      symbol: form.symbol,
      timeframe: form.timeframe,
      model: form.model,
      interval_minutes: Number(form.interval_minutes),
      size_usd: Number(form.size_usd),
      min_confidence: Number(form.min_confidence),
      allow_actions: [form.allow_buy ? "BUY" : null, form.allow_sell ? "SELL" : null].filter(Boolean),
      use_testnet: !!form.use_testnet,
      max_daily_loss: Number(form.max_daily_loss),
      active: !!form.active,
    };
    try {
      if (isEdit) {
        await api.patch(`/bots/${bot.id}`, payload);
        toast.success("Bot updated");
      } else {
        await api.post("/bots", payload);
        toast.success("Bot created");
      }
      setOpen(false);
      onSaved?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant} size={isEdit ? "sm" : "default"} data-testid="bot-form-open">
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{isEdit ? "Edit bot" : "Create AI trading bot"}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => update("name", e.target.value)} className="mt-1" data-testid="bot-name-input" />
          </div>
          <div>
            <Label>Symbol</Label>
            <Select value={form.symbol} onValueChange={(v) => update("symbol", v)}>
              <SelectTrigger className="mt-1" data-testid="bot-symbol-select"><SelectValue /></SelectTrigger>
              <SelectContent className="max-h-64">
                {SYMBOLS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Timeframe</Label>
            <Select value={form.timeframe} onValueChange={(v) => update("timeframe", v)}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>AI Model</Label>
            <Select value={form.model} onValueChange={(v) => update("model", v)}>
              <SelectTrigger className="mt-1" data-testid="bot-model-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="claude">Claude Sonnet 4.5</SelectItem>
                <SelectItem value="gemini">Gemini 2.5 Pro</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Interval (minutes)</Label>
            <Input type="number" min="1" max="1440" value={form.interval_minutes} onChange={(e) => update("interval_minutes", e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label>Size per trade (USD)</Label>
            <Input type="number" min="1" step="any" value={form.size_usd} onChange={(e) => update("size_usd", e.target.value)} className="mt-1" data-testid="bot-size-input" />
          </div>
          <div>
            <Label>Min confidence (0-1)</Label>
            <Input type="number" min="0" max="1" step="0.05" value={form.min_confidence} onChange={(e) => update("min_confidence", e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label>Max daily loss (USD)</Label>
            <Input type="number" min="0" step="any" value={form.max_daily_loss} onChange={(e) => update("max_daily_loss", e.target.value)} className="mt-1" />
          </div>
          <div className="col-span-2 flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.allow_buy} onChange={(e) => update("allow_buy", e.target.checked)} />
              Allow BUY
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.allow_sell} onChange={(e) => update("allow_sell", e.target.checked)} />
              Allow SELL
            </label>
          </div>
          <div className="col-span-2 flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <div className="text-sm font-medium">Use Binance testnet</div>
              <div className="text-xs text-muted-foreground">Requires enabled testnet keys in Settings.</div>
            </div>
            <Switch checked={form.use_testnet} onCheckedChange={(v) => update("use_testnet", v)} data-testid="bot-testnet-switch" />
          </div>
          <div className="col-span-2 flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <div className="text-sm font-medium">Start immediately</div>
              <div className="text-xs text-muted-foreground">Schedules the first run and every {form.interval_minutes} minutes after.</div>
            </div>
            <Switch checked={form.active} onCheckedChange={(v) => update("active", v)} data-testid="bot-active-switch" />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={submit} data-testid="bot-form-submit">{isEdit ? "Save changes" : "Create bot"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
