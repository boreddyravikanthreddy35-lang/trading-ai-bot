import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, TrendingUp, TrendingDown, ArrowRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

import { api, getErrorMessage } from "@/lib/api";
import { formatUSD, formatCompact, formatPercent, clsxColor } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { Sparkline } from "@/components/Charts";
import { LoadingCard, ErrorState } from "@/components/States";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { SignalCard, SignalCardSkeleton } from "@/components/SignalCard";
import { UpgradeBanner } from "@/components/UpgradeBanner";
import { useSubscription } from "@/context/SubscriptionContext";

const QUICK_SYMBOLS = [
  { symbol: "BTCUSDT", label: "Bitcoin" },
  { symbol: "ETHUSDT", label: "Ethereum" },
  { symbol: "SOLUSDT", label: "Solana" },
];

export default function DashboardPage() {
  const nav = useNavigate();
  const [coins, setCoins] = useState(null);
  const [error, setError] = useState(null);
  const { subscription, refresh: refreshSub } = useSubscription();
  const signalsPerDay = subscription?.plan?.limits?.signals_per_day ?? 5;
  const signalsUsed = subscription?.usage?.signals_today ?? 0;
  const signalsRemaining = signalsPerDay === -1 ? "unlimited" : Math.max(0, signalsPerDay - signalsUsed);
  const overQuota = signalsPerDay !== -1 && signalsUsed >= signalsPerDay;

  const [quickSymbol, setQuickSymbol] = useState("BTCUSDT");
  const [quickModel, setQuickModel] = useState("claude");
  const [quickResult, setQuickResult] = useState(null);
  const [signalBusy, setSignalBusy] = useState(false);

  const load = async () => {
    setError(null);
    try {
      const { data } = await api.get("/market/overview", { params: { per_page: 25 } });
      setCoins(data.coins || []);
    } catch (e) {
      setError(getErrorMessage(e, "Failed to load market data"));
    }
  };

  useEffect(() => { load(); }, []);

  const { gainers, losers } = useMemo(() => {
    if (!coins) return { gainers: [], losers: [] };
    const withPct = coins.filter((c) => c.price_change_percentage_24h != null);
    const sorted = [...withPct].sort((a, b) => b.price_change_percentage_24h - a.price_change_percentage_24h);
    return { gainers: sorted.slice(0, 5), losers: sorted.slice(-5).reverse() };
  }, [coins]);

  const generateQuickSignal = async () => {
    if (signalBusy) return;
    setSignalBusy(true);
    setQuickResult(null);
    try {
      const { data } = await api.post("/ai/signal", {
        symbol: quickSymbol,
        timeframe: "1h",
        model: quickModel,
      });
      setQuickResult(data);
      toast.success("AI signal generated");
      refreshSub();
    } catch (e) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      if (status === 402) {
        toast.error(detail || "Daily signal limit reached — upgrade to unlock more");
      } else {
        toast.error(detail || "Signal failed");
      }
    } finally {
      setSignalBusy(false);
    }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 pb-24">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Markets Overview</h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time crypto prices — tap any coin for full chart + AI signal.</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-markets-btn">
          <RefreshCw className="h-4 w-4 mr-2" /> Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Left: main markets table */}
        <section className="lg:col-span-8">
          <div className="rounded-xl border border-border bg-card" data-testid="market-table-panel">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <div className="font-display font-semibold">Top by Market Cap</div>
              <div className="text-xs text-muted-foreground">Prices refresh every ~45s</div>
            </div>
            {error ? (
              <div className="p-4"><ErrorState message={error} onRetry={load} /></div>
            ) : !coins ? (
              <div className="p-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 flex items-center gap-3 border-b border-border/40">
                    <Skeleton className="h-7 w-7 rounded-full" />
                    <Skeleton className="h-4 w-24" />
                    <div className="flex-1" />
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table data-testid="market-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">#</TableHead>
                      <TableHead>Coin</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right hidden sm:table-cell">24h</TableHead>
                      <TableHead className="text-right hidden md:table-cell">7d</TableHead>
                      <TableHead className="text-right hidden lg:table-cell">Volume 24h</TableHead>
                      <TableHead className="text-right hidden md:table-cell">Chart 7d</TableHead>
                      <TableHead className="w-24"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {coins.map((c) => {
                      const symbolPair = pairFor(c.symbol);
                      const chg24 = c.price_change_percentage_24h;
                      const chg7d = c.price_change_percentage_7d_in_currency;
                      return (
                        <TableRow
                          key={c.id || c.symbol}
                          data-testid="market-table-row"
                          className="hover:bg-muted/30 cursor-pointer"
                          onClick={() => nav(`/coin/${symbolPair}`)}
                        >
                          <TableCell className="text-muted-foreground">{c.market_cap_rank || "—"}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {c.image ? <img src={c.image} alt="" className="h-6 w-6 rounded-full" /> : <div className="h-6 w-6 rounded-full bg-muted" />}
                              <div>
                                <div className="font-medium">{c.name}</div>
                                <div className="text-xs text-muted-foreground uppercase">{c.symbol}</div>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-mono tabular-nums" data-testid={`market-price-${c.symbol}`}>
                            {formatUSD(c.current_price)}
                          </TableCell>
                          <TableCell className={`text-right hidden sm:table-cell font-mono tabular-nums ${clsxColor(chg24)}`}>
                            {formatPercent(chg24)}
                          </TableCell>
                          <TableCell className={`text-right hidden md:table-cell font-mono tabular-nums ${clsxColor(chg7d)}`}>
                            {formatPercent(chg7d)}
                          </TableCell>
                          <TableCell className="text-right hidden lg:table-cell text-muted-foreground font-mono tabular-nums">
                            {formatCompact(c.total_volume)}
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            {c.sparkline_in_7d?.price?.length ? (
                              <Sparkline
                                points={c.sparkline_in_7d.price}
                                stroke={chg24 >= 0 ? "hsl(152 62% 45%)" : "hsl(0 72% 52%)"}
                                width={120} height={32}
                              />
                            ) : <span className="text-muted-foreground text-xs">n/a</span>}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" data-testid={`market-view-${c.symbol}`}>
                              View <ArrowRight className="h-3 w-3 ml-1" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </section>

        {/* Right: signal generator + movers */}
        <section className="lg:col-span-4 space-y-4 md:space-y-6">
          {overQuota ? (
            <UpgradeBanner
              title="Daily signal limit reached"
              body={`You've used ${signalsUsed}/${signalsPerDay} signals today. Upgrade to keep going.`}
              requiredPlan="Pro"
              testId="signal-quota-banner"
            />
          ) : null}
          <div className="rounded-xl border border-border bg-card p-4" data-testid="quick-signal-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <div className="font-display font-semibold">Generate an AI signal</div>
              </div>
              <div className="text-[11px] text-muted-foreground" data-testid="dashboard-signal-quota">
                {signalsPerDay === -1 ? "Unlimited" : `${signalsUsed}/${signalsPerDay} today`}
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Symbol</div>
                <Select value={quickSymbol} onValueChange={setQuickSymbol}>
                  <SelectTrigger data-testid="quick-signal-symbol"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {QUICK_SYMBOLS.map((q) => (
                      <SelectItem key={q.symbol} value={q.symbol}>{q.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Model</div>
                <Select value={quickModel} onValueChange={setQuickModel}>
                  <SelectTrigger data-testid="quick-signal-model"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="claude">Claude Sonnet 4.5</SelectItem>
                    <SelectItem value="gemini">Gemini 2.5 Pro</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button className="w-full mt-3" onClick={generateQuickSignal} disabled={signalBusy} data-testid="signal-generate-button">
              {signalBusy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Analyzing markets…</> : <><Sparkles className="h-4 w-4 mr-2" /> Generate signal</>}
            </Button>

            {signalBusy ? (
              <div className="mt-4 space-y-3">
                <SignalCardSkeleton />
                {quickModel === "both" ? <SignalCardSkeleton /> : null}
              </div>
            ) : quickResult?.results?.length ? (
              <div className="mt-4 space-y-3">
                {quickResult.results.map((r, i) => (
                  <SignalCard key={i} result={r} symbol={quickResult.symbol} timeframe={quickResult.timeframe} signalId={quickResult.id} />
                ))}
              </div>
            ) : null}
          </div>

          <MoversPanel title="Top Gainers 24h" data={gainers} icon={TrendingUp} testId="top-gainers" positive />
          <MoversPanel title="Top Losers 24h" data={losers} icon={TrendingDown} testId="top-losers" />
        </section>
      </div>
    </div>
  );
}

function MoversPanel({ title, data, icon: Icon, testId, positive = false }) {
  const nav = useNavigate();
  return (
    <div className="rounded-xl border border-border bg-card" data-testid={testId}>
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Icon className={`h-4 w-4 ${positive ? "text-[hsl(var(--up))]" : "text-[hsl(var(--down))]"}`} />
        <div className="font-display font-semibold">{title}</div>
      </div>
      {!data?.length ? (
        <div className="p-3 text-sm text-muted-foreground">No data yet.</div>
      ) : (
        <div className="divide-y divide-border/60">
          {data.map((c) => (
            <button
              key={c.id}
              onClick={() => nav(`/coin/${pairFor(c.symbol)}`)}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-muted/30 text-left"
            >
              {c.image ? <img src={c.image} alt="" className="h-6 w-6 rounded-full" /> : <div className="h-6 w-6 rounded-full bg-muted" />}
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{c.name}</div>
                <div className="text-xs text-muted-foreground uppercase">{c.symbol}</div>
              </div>
              <div className="text-right">
                <div className="font-mono tabular-nums text-sm">{formatUSD(c.current_price)}</div>
                <div className={`text-xs font-mono ${clsxColor(c.price_change_percentage_24h)}`}>{formatPercent(c.price_change_percentage_24h)}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function pairFor(sym) {
  return `${(sym || "").toUpperCase()}USDT`;
}
