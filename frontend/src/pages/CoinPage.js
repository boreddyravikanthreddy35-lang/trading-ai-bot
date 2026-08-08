import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, RefreshCw, Sparkles, Star, Bell } from "lucide-react";
import { api } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, formatCompact, symbolToPair } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { PriceChart } from "@/components/Charts";
import { ErrorState, LoadingCard } from "@/components/States";
import { SignalCard, SignalCardSkeleton } from "@/components/SignalCard";

const SYMBOL_TO_CG = {
  BTCUSDT: "bitcoin", ETHUSDT: "ethereum", SOLUSDT: "solana",
  BNBUSDT: "binancecoin", XRPUSDT: "ripple", ADAUSDT: "cardano",
  DOGEUSDT: "dogecoin", AVAXUSDT: "avalanche-2", DOTUSDT: "polkadot",
  LINKUSDT: "chainlink", MATICUSDT: "polygon-ecosystem-token", LTCUSDT: "litecoin",
};

const TIMEFRAMES = [
  { label: "5m", value: "5m" },
  { label: "15m", value: "15m" },
  { label: "1h", value: "1h" },
  { label: "4h", value: "4h" },
  { label: "1d", value: "1d" },
];

export default function CoinPage() {
  const { symbol } = useParams();
  const upperSym = (symbol || "").toUpperCase();
  const nav = useNavigate();

  const [meta, setMeta] = useState(null);
  const [tf, setTf] = useState("1h");
  const [chartData, setChartData] = useState(null);
  const [chartErr, setChartErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const [model, setModel] = useState("claude");
  const [signalRes, setSignalRes] = useState(null);
  const [signalBusy, setSignalBusy] = useState(false);

  const cgId = SYMBOL_TO_CG[upperSym];

  const loadMeta = async () => {
    if (!cgId) { setMeta({ name: upperSym, symbol: upperSym }); return; }
    try {
      const { data } = await api.get(`/market/coin/${cgId}`);
      setMeta(data);
    } catch { setMeta({ name: upperSym, symbol: upperSym }); }
  };

  const loadChart = async () => {
    setBusy(true);
    setChartErr(null);
    try {
      const { data } = await api.get("/market/klines", {
        params: { symbol: upperSym, interval: tf, limit: 300, with_indicators: true },
      });
      setChartData(data);
    } catch (e) {
      setChartErr(e?.response?.data?.detail || "Chart data unavailable");
    } finally { setBusy(false); }
  };

  useEffect(() => { loadMeta(); }, [upperSym]);
  useEffect(() => { loadChart(); }, [upperSym, tf]);

  const generateSignal = async () => {
    if (signalBusy) return;
    setSignalBusy(true); setSignalRes(null);
    try {
      const { data } = await api.post("/ai/signal", { symbol: upperSym, timeframe: tf, model });
      setSignalRes(data);
      toast.success("AI signal generated");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Signal failed");
    } finally { setSignalBusy(false); }
  };

  const addAlert = async () => {
    const price = chartData?.indicators?.price || meta?.current_price;
    if (!price) return toast.error("Price unavailable");
    const thStr = prompt(`Alert threshold for ${upperSym} (current: $${price})`, price.toFixed(2));
    if (!thStr) return;
    const threshold = parseFloat(thStr);
    if (!threshold || isNaN(threshold)) return toast.error("Invalid threshold");
    const condition = threshold > price ? "above" : "below";
    try {
      await api.post("/watch/alerts", { symbol: upperSym, threshold, condition });
      toast.success(`Alert set: ${upperSym} ${condition} $${threshold}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create alert");
    }
  };

  const overlays = useMemo(() => {
    const s = chartData?.indicator_series;
    return s ? { sma_20: s.sma_20 || [], sma_50: s.sma_50 || [] } : {};
  }, [chartData]);

  const ind = chartData?.indicators;

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => nav(-1)} data-testid="back-button"><ArrowLeft className="h-4 w-4" /></Button>
          <div>
            <div className="flex items-center gap-2">
              {meta?.image ? <img src={meta.image} alt="" className="h-7 w-7 rounded-full" /> : null}
              <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight" data-testid="coin-title">{meta?.name || upperSym}</h1>
              <Badge variant="outline" className="text-xs uppercase tracking-wider">{symbolToPair(upperSym)}</Badge>
            </div>
            <div className="mt-1 text-sm text-muted-foreground">{meta?.market_cap_rank ? `Rank #${meta.market_cap_rank}` : "—"} · Source: {chartData?.source || "—"}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={addAlert} data-testid="quick-add-alert"><Bell className="h-4 w-4 mr-2" /> Add alert</Button>
          <Button variant="outline" size="sm" onClick={loadChart} data-testid="refresh-chart"><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Chart column */}
        <section className="lg:col-span-8">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Price</div>
                <div className="flex items-center gap-3">
                  <div className="font-mono tabular-nums text-2xl font-semibold" data-testid="coin-current-price">
                    {formatUSD(ind?.price ?? meta?.current_price)}
                  </div>
                  {ind?.pct_change_24h != null ? (
                    <div className={`text-sm font-mono ${clsxColor(ind.pct_change_24h)}`}>
                      {formatPercent(ind.pct_change_24h)} <span className="text-muted-foreground">24h</span>
                    </div>
                  ) : null}
                </div>
              </div>
              <Select value={tf} onValueChange={setTf}>
                <SelectTrigger className="w-28" data-testid="coin-chart-timeframe-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIMEFRAMES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="mt-2 border-t border-border pt-3" data-testid="chart-container">
              {chartErr ? (
                <ErrorState message={chartErr} onRetry={loadChart} />
              ) : busy && !chartData ? (
                <Skeleton className="w-full h-[420px]" />
              ) : chartData?.candles?.length ? (
                <PriceChart candles={chartData.candles} overlays={overlays} height={420} />
              ) : (
                <div className="h-[420px] flex items-center justify-center text-sm text-muted-foreground">No chart data.</div>
              )}
            </div>

            {/* Indicators strip */}
            {ind ? (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="indicators-strip">
                <Stat label="RSI 14" value={ind.rsi_14?.toFixed?.(2)} tone={ind.rsi_14 > 70 ? "warn" : ind.rsi_14 < 30 ? "warn" : "neutral"} />
                <Stat label="SMA 20" value={formatUSD(ind.sma_20)} tone="neutral" />
                <Stat label="SMA 50" value={formatUSD(ind.sma_50)} tone="neutral" />
                <Stat label="MACD" value={ind.macd?.toFixed?.(4)} tone={ind.macd >= 0 ? "up" : "down"} />
              </div>
            ) : null}
          </div>

          {meta?.description ? (
            <div className="rounded-xl border border-border bg-card p-4 mt-4">
              <div className="font-display font-semibold mb-1">About {meta.name}</div>
              <p className="text-sm text-muted-foreground leading-relaxed">{meta.description}</p>
            </div>
          ) : null}
        </section>

        {/* AI signal column */}
        <section className="lg:col-span-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">AI Trading Signal</div>
            </div>
            <div className="mt-3">
              <div className="text-xs text-muted-foreground mb-1">Model</div>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger data-testid="signal-model-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude">Claude Sonnet 4.5</SelectItem>
                  <SelectItem value="gemini">Gemini 2.5 Pro</SelectItem>
                  <SelectItem value="both">Both (compare)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button className="w-full mt-3" onClick={generateSignal} disabled={signalBusy} data-testid="signal-generate-button">
              {signalBusy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Analyzing…</> : <><Sparkles className="h-4 w-4 mr-2" /> Generate signal ({tf})</>}
            </Button>

            <div className="mt-4 space-y-3">
              {signalBusy ? (
                <>
                  <SignalCardSkeleton />
                  {model === "both" ? <SignalCardSkeleton /> : null}
                </>
              ) : signalRes?.results?.length ? (
                signalRes.results.map((r, i) => (
                  <SignalCard key={i} result={r} symbol={signalRes.symbol} timeframe={signalRes.timeframe} signalId={signalRes.id} />
                ))
              ) : (
                <div className="text-xs text-muted-foreground">Choose a model and generate a signal to see AI reasoning here.</div>
              )}
            </div>
          </div>

          {meta ? (
            <div className="rounded-xl border border-border bg-card p-4 mt-4">
              <div className="font-display font-semibold mb-2">Key stats</div>
              <div className="space-y-2 text-sm">
                <Row label="Market cap" value={formatCompact(meta.market_cap)} />
                <Row label="24h volume" value={formatCompact(meta.total_volume)} />
                <Row label="24h high" value={formatUSD(meta.high_24h)} />
                <Row label="24h low" value={formatUSD(meta.low_24h)} />
                <Row label="7d change" value={formatPercent(meta.price_change_percentage_7d)} valueClass={clsxColor(meta.price_change_percentage_7d)} />
                <Row label="ATH" value={formatUSD(meta.ath)} />
                <Row label="ATL" value={formatUSD(meta.atl)} />
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }) {
  const toneClass = tone === "up" ? "text-[hsl(var(--up))]" : tone === "down" ? "text-[hsl(var(--down))]" : tone === "warn" ? "text-[hsl(var(--warning))]" : "text-foreground";
  return (
    <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 font-mono tabular-nums text-sm font-medium ${toneClass}`}>{value ?? "—"}</div>
    </div>
  );
}

function Row({ label, value, valueClass = "" }) {
  return (
    <div className="flex justify-between items-center">
      <div className="text-muted-foreground">{label}</div>
      <div className={`font-mono tabular-nums ${valueClass}`}>{value ?? "—"}</div>
    </div>
  );
}
