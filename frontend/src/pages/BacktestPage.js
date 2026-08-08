import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { FlaskConical, Play, Save, Star, Trash2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { api } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from "@/components/ui/dialog";
import { ErrorState, EmptyState } from "@/components/States";

const SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
];
const STRATEGIES = [
  { value: "sma_crossover", label: "SMA Crossover" },
  { value: "rsi", label: "RSI Mean Reversion" },
  { value: "macd", label: "MACD Crossover" },
];
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setInterval] = useState("1h");
  const [strategy, setStrategy] = useState("sma_crossover");
  const [limit, setLimit] = useState(500);
  const [fast, setFast] = useState(20);
  const [slow, setSlow] = useState(50);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [oversold, setOversold] = useState(30);
  const [overbought, setOverbought] = useState(70);
  const [initialCash, setInitialCash] = useState(10000);

  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Presets
  const [presets, setPresets] = useState([]);
  const [saveOpen, setSaveOpen] = useState(false);
  const [presetName, setPresetName] = useState("");

  const loadPresets = async () => {
    try {
      const { data } = await api.get("/presets");
      setPresets(data.presets || []);
    } catch { /* silent */ }
  };
  useEffect(() => { loadPresets(); }, []);

  const applyPreset = (p) => {
    setSymbol(SYMBOLS.includes(p.symbol) ? p.symbol : symbol); // symbol not stored in preset for now, keep current
    setStrategy(p.strategy);
    setInterval(p.interval);
    setLimit(p.limit);
    setInitialCash(p.initial_cash);
    if (p.strategy === "sma_crossover") { setFast(p.fast || 20); setSlow(p.slow || 50); }
    if (p.strategy === "rsi") { setRsiPeriod(p.rsi_period || 14); setOversold(p.oversold || 30); setOverbought(p.overbought || 70); }
    toast.success(`Loaded preset: ${p.name}`);
  };

  const savePreset = async () => {
    if (!presetName.trim()) return toast.error("Name required");
    try {
      const body = {
        name: presetName.trim(), strategy, interval, limit: Number(limit),
        initial_cash: Number(initialCash), fee_rate: 0.001,
      };
      if (strategy === "sma_crossover") { body.fast = Number(fast); body.slow = Number(slow); }
      if (strategy === "rsi") { body.rsi_period = Number(rsiPeriod); body.oversold = Number(oversold); body.overbought = Number(overbought); }
      await api.post("/presets", body);
      toast.success("Preset saved");
      setSaveOpen(false); setPresetName("");
      loadPresets();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  const deletePreset = async (id) => {
    if (!window.confirm("Delete this preset?")) return;
    try {
      await api.delete(`/presets/${id}`);
      loadPresets();
    } catch { toast.error("Delete failed"); }
  };

  const run = async () => {
    if (busy) return;
    setBusy(true); setError(null); setResult(null);
    try {
      const body = { symbol, interval, strategy, limit: Number(limit), initial_cash: Number(initialCash) };
      if (strategy === "sma_crossover") { body.fast = Number(fast); body.slow = Number(slow); }
      if (strategy === "rsi") { body.rsi_period = Number(rsiPeriod); body.oversold = Number(oversold); body.overbought = Number(overbought); }
      const { data } = await api.post("/backtest/run", body);
      setResult(data);
      toast.success("Backtest complete");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Backtest failed";
      setError(msg);
      toast.error(msg);
    } finally { setBusy(false); }
  };

  const r = result?.result;
  const equity = r?.equity_curve || [];
  const metrics = r?.metrics;

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="mb-5">
        <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Strategy Backtesting</h1>
        <p className="text-sm text-muted-foreground mt-1">Simulate trading strategies on real historical market data.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Form */}
        <section className="lg:col-span-4 space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <FlaskConical className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">Configure</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Symbol</Label>
                <Select value={symbol} onValueChange={setSymbol}>
                  <SelectTrigger data-testid="backtest-symbol-select" className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent className="max-h-72">
                    {SYMBOLS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Interval</Label>
                <Select value={interval} onValueChange={setInterval}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2">
                <Label>Strategy</Label>
                <Select value={strategy} onValueChange={setStrategy}>
                  <SelectTrigger data-testid="backtest-strategy-select" className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {STRATEGIES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              {strategy === "sma_crossover" && (
                <>
                  <div>
                    <Label>Fast SMA</Label>
                    <Input type="number" min="2" max="200" value={fast} onChange={(e) => setFast(e.target.value)} className="mt-1" />
                  </div>
                  <div>
                    <Label>Slow SMA</Label>
                    <Input type="number" min="5" max="500" value={slow} onChange={(e) => setSlow(e.target.value)} className="mt-1" />
                  </div>
                </>
              )}

              {strategy === "rsi" && (
                <>
                  <div>
                    <Label>RSI period</Label>
                    <Input type="number" min="2" max="60" value={rsiPeriod} onChange={(e) => setRsiPeriod(e.target.value)} className="mt-1" />
                  </div>
                  <div>
                    <Label>Oversold</Label>
                    <Input type="number" min="5" max="49" value={oversold} onChange={(e) => setOversold(e.target.value)} className="mt-1" />
                  </div>
                  <div>
                    <Label>Overbought</Label>
                    <Input type="number" min="51" max="95" value={overbought} onChange={(e) => setOverbought(e.target.value)} className="mt-1" />
                  </div>
                </>
              )}

              <div>
                <Label>Candles</Label>
                <Input type="number" min="80" max="1000" value={limit} onChange={(e) => setLimit(e.target.value)} className="mt-1" />
              </div>
              <div>
                <Label>Initial cash ($)</Label>
                <Input type="number" min="100" step="100" value={initialCash} onChange={(e) => setInitialCash(e.target.value)} className="mt-1" />
              </div>
            </div>
            <Button className="w-full mt-4" onClick={run} disabled={busy} data-testid="backtest-run-button">
              {busy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Running…</> : <><Play className="h-4 w-4 mr-2" /> Run backtest</>}
            </Button>
          </div>

          {/* Strategy Presets */}
          <div className="rounded-xl border border-border bg-card p-4" data-testid="strategy-presets-panel">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-primary" />
                <div className="font-display font-semibold">Strategy Presets</div>
              </div>
              <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" data-testid="preset-save-btn"><Save className="h-3.5 w-3.5 mr-1.5" /> Save current</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>Save preset</DialogTitle></DialogHeader>
                  <div>
                    <Label>Name</Label>
                    <Input value={presetName} onChange={(e) => setPresetName(e.target.value)} placeholder="e.g. Fast SMA on 1h" className="mt-1" data-testid="preset-name-input" />
                  </div>
                  <DialogFooter><Button onClick={savePreset} data-testid="preset-save-submit">Save</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            {presets.length === 0 ? (
              <div className="text-xs text-muted-foreground py-2">No saved presets yet. Configure a backtest and hit "Save current".</div>
            ) : (
              <div className="space-y-1.5" data-testid="preset-list">
                {presets.map((p) => (
                  <div key={p.id} className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/40">
                    <button onClick={() => applyPreset(p)} className="flex-1 text-left" data-testid={`preset-apply-${p.id}`}>
                      <div className="text-sm font-medium">{p.name}</div>
                      <div className="text-[11px] text-muted-foreground uppercase">{p.strategy} · {p.interval} · ${Number(p.initial_cash).toLocaleString()}</div>
                    </button>
                    <Button variant="ghost" size="icon" onClick={() => deletePreset(p.id)} data-testid={`preset-delete-${p.id}`}><Trash2 className="h-3.5 w-3.5 text-muted-foreground" /></Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Results */}
        <section className="lg:col-span-8 space-y-4" data-testid="backtest-results-panel">
          {error ? (
            <ErrorState message={error} />
          ) : !result ? (
            <EmptyState title="Run a backtest" description="Choose a strategy on the left and hit ‘Run backtest’ to see the equity curve, metrics, and trades here." />
          ) : (
            <>
              <div className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="font-display font-semibold">{r.strategy} — {result.symbol} {result.interval}</div>
                  <Badge variant="outline" className={clsxColor(metrics.return_pct)}>{formatPercent(metrics.return_pct)} return</Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="backtest-metrics">
                  <Metric label="Ending equity" value={formatUSD(metrics.ending_equity)} />
                  <Metric label="Total PnL" value={formatUSD(metrics.total_pnl)} tone={metrics.total_pnl >= 0 ? "up" : "down"} />
                  <Metric label="# trades" value={metrics.num_trades} />
                  <Metric label="Win rate" value={`${metrics.win_rate_pct}%`} tone={metrics.win_rate_pct >= 50 ? "up" : "down"} />
                  <Metric label="Avg win" value={formatUSD(metrics.avg_win)} tone="up" />
                  <Metric label="Avg loss" value={formatUSD(metrics.avg_loss)} tone="down" />
                  <Metric label="Max drawdown" value={`-${metrics.max_drawdown_pct}%`} tone="down" />
                  <Metric label="Initial cash" value={formatUSD(metrics.initial_cash)} />
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-4">
                <div className="font-display font-semibold mb-2">Equity curve</div>
                <div className="h-[320px]" data-testid="backtest-equity-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equity}>
                      <defs>
                        <linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(188 92% 45%)" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="hsl(188 92% 45%)" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="time" hide />
                      <YAxis stroke="hsl(215 14% 70%)" fontSize={11} tickFormatter={(v) => `$${Math.round(v).toLocaleString()}`} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "hsl(220 18% 8%)", border: "1px solid hsl(220 14% 18%)", borderRadius: 8, fontSize: 12 }}
                        formatter={(v) => [formatUSD(v), "Equity"]}
                        labelFormatter={(t) => new Date(t * 1000).toLocaleString()}
                      />
                      <ReferenceLine y={metrics.initial_cash} stroke="hsl(215 14% 40%)" strokeDasharray="4 3" />
                      <Area type="monotone" dataKey="equity" stroke="hsl(188 92% 45%)" strokeWidth={2} fill="url(#eqfill)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card">
                <div className="px-4 py-3 border-b border-border font-display font-semibold">Trades ({r.trades?.length || 0})</div>
                {!r.trades?.length ? (
                  <div className="p-4 text-sm text-muted-foreground">No trades were executed for this strategy on this range.</div>
                ) : (
                  <div className="overflow-x-auto max-h-[400px]">
                    <Table data-testid="backtest-trades-table">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Time</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead className="text-right">Price</TableHead>
                          <TableHead className="text-right">Qty</TableHead>
                          <TableHead className="text-right">PnL</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {r.trades.slice().reverse().map((t, i) => (
                          <TableRow key={i}>
                            <TableCell className="text-muted-foreground text-xs">{new Date(t.time * 1000).toLocaleString()}</TableCell>
                            <TableCell><Badge variant="outline" className={t.side === "BUY" ? "text-[hsl(var(--up))] border-[hsl(var(--up))]/40" : "text-[hsl(var(--down))] border-[hsl(var(--down))]/40"}>{t.side}</Badge></TableCell>
                            <TableCell className="text-right font-mono tabular-nums">{formatUSD(t.price)}</TableCell>
                            <TableCell className="text-right font-mono tabular-nums">{t.qty}</TableCell>
                            <TableCell className={`text-right font-mono tabular-nums ${clsxColor(t.pnl)}`}>{t.pnl != null ? formatUSD(t.pnl) : "—"}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }) {
  const cls = tone === "up" ? "text-[hsl(var(--up))]" : tone === "down" ? "text-[hsl(var(--down))]" : "text-foreground";
  return (
    <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 font-mono tabular-nums text-base font-medium ${cls}`}>{value}</div>
    </div>
  );
}
