import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, RefreshCw, LineChart } from "lucide-react";
import { api } from "@/lib/api";
import { shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { SignalCard, SignalCardSkeleton } from "@/components/SignalCard";
import { EmptyState, ErrorState } from "@/components/States";

const SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT", "LTCUSDT",
];
const TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"];

export default function SignalsPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [tf, setTf] = useState("1h");
  const [model, setModel] = useState("both");
  const [busy, setBusy] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);

  const [history, setHistory] = useState(null);
  const [historyErr, setHistoryErr] = useState(null);

  const loadHistory = async () => {
    setHistoryErr(null);
    try {
      const { data } = await api.get("/ai/history", { params: { limit: 20 } });
      setHistory(data.signals || []);
    } catch (e) {
      setHistoryErr(e?.response?.data?.detail || "Failed to load history");
    }
  };

  useEffect(() => { loadHistory(); }, []);

  const generate = async () => {
    if (busy) return;
    setBusy(true); setCurrentResult(null);
    try {
      const { data } = await api.post("/ai/signal", { symbol, timeframe: tf, model });
      setCurrentResult(data);
      toast.success("Signal generated");
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Signal failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">AI Trading Signals</h1>
          <p className="text-sm text-muted-foreground mt-1">Compare Claude Sonnet 4.5 and Gemini 2.5 Pro on live market data.</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadHistory} data-testid="refresh-history-btn"><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Generator + result */}
        <section className="lg:col-span-8 space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">New signal</div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Symbol</div>
                <Select value={symbol} onValueChange={setSymbol}>
                  <SelectTrigger data-testid="signals-symbol-select"><SelectValue /></SelectTrigger>
                  <SelectContent className="max-h-72">
                    {SYMBOLS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Timeframe</div>
                <Select value={tf} onValueChange={setTf}>
                  <SelectTrigger data-testid="signal-timeframe-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Model</div>
                <Select value={model} onValueChange={setModel}>
                  <SelectTrigger data-testid="signal-model-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="claude">Claude Sonnet 4.5</SelectItem>
                    <SelectItem value="gemini">Gemini 2.5 Pro</SelectItem>
                    <SelectItem value="both">Both — side by side</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button className="mt-4 w-full md:w-auto" onClick={generate} disabled={busy} data-testid="signal-generate-button">
              {busy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Analyzing markets…</> : <><Sparkles className="h-4 w-4 mr-2" /> Generate signal</>}
            </Button>
          </div>

          {busy ? (
            <div className={`grid gap-4 ${model === "both" ? "grid-cols-1 xl:grid-cols-2" : "grid-cols-1"}`}>
              <SignalCardSkeleton />
              {model === "both" ? <SignalCardSkeleton /> : null}
            </div>
          ) : currentResult ? (
            <div className={`grid gap-4 ${currentResult.results?.length > 1 ? "grid-cols-1 xl:grid-cols-2" : "grid-cols-1"}`} data-testid="model-comparison-tabs">
              {currentResult.results.map((r, i) => (
                <div key={i} data-testid={`model-comparison-${r.model_key}-panel`}>
                  <SignalCard result={r} symbol={currentResult.symbol} timeframe={currentResult.timeframe} signalId={currentResult.id} />
                </div>
              ))}
            </div>
          ) : null}
        </section>

        {/* History */}
        <section className="lg:col-span-4">
          <div className="rounded-xl border border-border bg-card">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <LineChart className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">Your recent signals</div>
            </div>
            {historyErr ? (
              <div className="p-4"><ErrorState message={historyErr} onRetry={loadHistory} /></div>
            ) : history === null ? (
              <div className="p-4 text-sm text-muted-foreground">Loading…</div>
            ) : history.length === 0 ? (
              <div className="p-4"><EmptyState title="No signals yet" description="Generate your first signal to see it here." /></div>
            ) : (
              <div className="divide-y divide-border/60 max-h-[560px] overflow-y-auto" data-testid="signal-history-list">
                {history.map((h) => {
                  const first = h.results?.[0]?.signal;
                  const action = first?.action || "—";
                  return (
                    <div key={h.id} className="px-4 py-3 text-sm">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">{h.symbol} <span className="text-xs text-muted-foreground uppercase">{h.timeframe}</span></div>
                        <Badge variant="outline" className={actionCls(action)}>{action}</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">{h.model} · {shortDate(h.created_at)}</div>
                      {first?.reasoning ? <div className="mt-1 text-xs text-muted-foreground line-clamp-2">{first.reasoning}</div> : null}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function actionCls(a) {
  if (a === "BUY") return "text-[hsl(var(--up))] border-[hsl(var(--up))]/40";
  if (a === "SELL") return "text-[hsl(var(--down))] border-[hsl(var(--down))]/40";
  return "text-muted-foreground";
}
