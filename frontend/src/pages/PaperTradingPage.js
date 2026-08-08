import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Wallet, RefreshCw, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Tabs, TabsList, TabsTrigger, TabsContent
} from "@/components/ui/tabs";
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

export default function PaperTradingPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState(null);
  const [error, setError] = useState(null);

  const [side, setSide] = useState("BUY");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [amount, setAmount] = useState(500);
  const [amountMode, setAmountMode] = useState("quote"); // quote (USD) | qty
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setError(null);
    try {
      const [p, t] = await Promise.all([
        api.get("/paper/portfolio"),
        api.get("/paper/trades", { params: { limit: 50 } }),
      ]);
      setPortfolio(p.data);
      setTrades(t.data.trades || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load portfolio");
    }
  };

  useEffect(() => { load(); }, []);

  const placeOrder = async () => {
    if (busy) return;
    const value = parseFloat(amount);
    if (!value || value <= 0) return toast.error("Enter a valid amount");
    setBusy(true);
    try {
      const body = { symbol, side };
      if (amountMode === "quote") body.quote_amount = value; else body.quantity = value;
      const { data } = await api.post("/paper/order", body);
      toast.success(`${data.side} filled: ${data.quantity.toFixed(6)} @ ${formatUSD(data.price)}`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Order failed");
    } finally { setBusy(false); }
  };

  const resetPortfolio = async () => {
    if (!window.confirm("Reset portfolio to $10,000 and clear all trades?")) return;
    try {
      await api.post("/paper/reset");
      toast.success("Portfolio reset");
      load();
    } catch (e) { toast.error("Reset failed"); }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Paper Trading</h1>
          <p className="text-sm text-muted-foreground mt-1">Practice with virtual $10,000. No real money.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-portfolio-btn"><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
          <Button variant="outline" size="sm" onClick={resetPortfolio} data-testid="reset-portfolio-btn"><RotateCcw className="h-4 w-4 mr-2" /> Reset</Button>
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6" data-testid="portfolio-summary">
        <SummaryCard label="Equity" value={formatUSD(portfolio?.equity)} valueClass="text-2xl font-semibold" testId="portfolio-equity" />
        <SummaryCard label="Cash" value={formatUSD(portfolio?.cash)} testId="portfolio-cash" />
        <SummaryCard label="Total PnL" value={formatUSD(portfolio?.total_pnl)} tone={portfolio?.total_pnl >= 0 ? "up" : "down"} testId="portfolio-total-pnl" />
        <SummaryCard label="Return" value={portfolio ? formatPercent(portfolio.total_pnl_pct) : "—"} tone={portfolio?.total_pnl_pct >= 0 ? "up" : "down"} testId="portfolio-return" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Order ticket */}
        <section className="lg:col-span-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Wallet className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">Place order</div>
            </div>
            <Tabs value={side} onValueChange={setSide} data-testid="order-ticket-side-tabs">
              <TabsList className="grid grid-cols-2">
                <TabsTrigger value="BUY" data-testid="order-tab-buy" className="data-[state=active]:bg-[hsl(var(--up))]/15 data-[state=active]:text-[hsl(var(--up))]">Buy</TabsTrigger>
                <TabsTrigger value="SELL" data-testid="order-tab-sell" className="data-[state=active]:bg-[hsl(var(--down))]/15 data-[state=active]:text-[hsl(var(--down))]">Sell</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="mt-3 space-y-3">
              <div>
                <Label>Symbol</Label>
                <Select value={symbol} onValueChange={setSymbol}>
                  <SelectTrigger data-testid="order-symbol-select" className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent className="max-h-64">
                    {SYMBOLS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <Label>Amount</Label>
                  <div className="flex rounded-md border border-border overflow-hidden text-[11px]">
                    <button onClick={() => setAmountMode("quote")} className={`px-2 py-1 ${amountMode === "quote" ? "bg-muted text-foreground" : "text-muted-foreground"}`}>USD</button>
                    <button onClick={() => setAmountMode("qty")} className={`px-2 py-1 ${amountMode === "qty" ? "bg-muted text-foreground" : "text-muted-foreground"}`}>Qty</button>
                  </div>
                </div>
                <Input
                  data-testid="order-ticket-quantity-input"
                  type="number" min="0" step="any"
                  value={amount} onChange={(e) => setAmount(e.target.value)}
                  className="mt-1" placeholder={amountMode === "quote" ? "USD amount" : "Coin qty"}
                />
              </div>
              <Button className={`w-full ${side === "BUY" ? "bg-[hsl(var(--up))] hover:bg-[hsl(var(--up))]/90 text-white" : "bg-[hsl(var(--down))] hover:bg-[hsl(var(--down))]/90 text-white"}`}
                onClick={placeOrder} disabled={busy} data-testid="order-ticket-submit-button">
                {busy ? <><span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" /> Placing…</> : `${side} ${symbol}`}
              </Button>
            </div>
          </div>
        </section>

        {/* Holdings + trades */}
        <section className="lg:col-span-8 space-y-4">
          <div className="rounded-xl border border-border bg-card">
            <div className="px-4 py-3 border-b border-border font-display font-semibold">Holdings</div>
            {!portfolio?.holdings?.length ? (
              <div className="p-4"><EmptyState title="No positions yet" description="Place your first buy order to open a position." /></div>
            ) : (
              <div className="overflow-x-auto">
                <Table data-testid="paper-holdings-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Avg price</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                      <TableHead className="text-right">Unrealized PnL</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {portfolio.holdings.map((h) => (
                      <TableRow key={h.symbol}>
                        <TableCell className="font-medium">{h.symbol}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{h.quantity.toFixed(6)}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{formatUSD(h.avg_price)}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{formatUSD(h.current_price)}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{formatUSD(h.market_value)}</TableCell>
                        <TableCell className={`text-right font-mono tabular-nums ${clsxColor(h.unrealized_pnl)}`}>
                          {formatUSD(h.unrealized_pnl)} <span className="text-xs">({formatPercent(h.unrealized_pnl_pct)})</span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-border bg-card">
            <div className="px-4 py-3 border-b border-border font-display font-semibold">Trade history</div>
            {!trades?.length ? (
              <div className="p-4 text-sm text-muted-foreground">No trades yet.</div>
            ) : (
              <div className="overflow-x-auto max-h-[420px]">
                <Table data-testid="paper-trade-history-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>When</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Realized PnL</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell className="text-xs text-muted-foreground">{shortDate(t.created_at)}</TableCell>
                        <TableCell className="font-medium">{t.symbol}</TableCell>
                        <TableCell><Badge variant="outline" className={t.side === "BUY" ? "text-[hsl(var(--up))] border-[hsl(var(--up))]/40" : "text-[hsl(var(--down))] border-[hsl(var(--down))]/40"}>{t.side}</Badge></TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{t.quantity.toFixed(6)}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{formatUSD(t.price)}</TableCell>
                        <TableCell className={`text-right font-mono tabular-nums ${clsxColor(t.realized_pnl)}`}>{t.realized_pnl ? formatUSD(t.realized_pnl) : "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, tone, testId, valueClass = "" }) {
  const cls = tone === "up" ? "text-[hsl(var(--up))]" : tone === "down" ? "text-[hsl(var(--down))]" : "text-foreground";
  return (
    <div data-testid={testId} className="rounded-xl border border-border bg-card p-4">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1.5 font-mono tabular-nums ${valueClass || "text-xl font-semibold"} ${cls}`}>{value ?? "—"}</div>
    </div>
  );
}
