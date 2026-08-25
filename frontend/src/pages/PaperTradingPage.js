import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Wallet, RefreshCw, RotateCcw, TrendingUp, TrendingDown, Activity, Zap, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, getErrorMessage } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { EmptyState, ErrorState } from "@/components/States";
import { useSubscription } from "@/context/SubscriptionContext";

// Stablecoins / non-tradeable to exclude from paper trading
const STABLECOIN_IDS = new Set([
  "tether", "usd-coin", "dai", "usds", "usdd", "ethena-usde",
  "paypal-usd", "usd1-wlfi", "global-dollar", "hashnote-usyc",
  "ripple-usd", "ondo-us-dollar-yield", "tether-gold", "pax-gold",
  "blackrock-usd-institutional-digital-liquidity-fund",
  "figure-heloc", "rain", "leo-token", "whitebit", "canton-network",
  "htx-dao", "memecore", "world-liberty-financial", "aster-2",
]);

// symbol (e.g. "BTCUSDT") → coingecko id, built dynamically from market data
// Fallback static map for symbols we know
const STATIC_SYM_TO_CG = {
  BTCUSDT: "bitcoin", ETHUSDT: "ethereum", SOLUSDT: "solana",
  BNBUSDT: "binancecoin", XRPUSDT: "ripple", ADAUSDT: "cardano",
  DOGEUSDT: "dogecoin", AVAXUSDT: "avalanche-2", DOTUSDT: "polkadot",
  LINKUSDT: "chainlink", LTCUSDT: "litecoin", SHIBUSDT: "shiba-inu",
  NEARUSDT: "near", UNIUSDT: "uniswap", SUIUSDT: "sui",
  HBARUSDT: "hedera-hashgraph", TRXUSDT: "tron", XLMUSDT: "stellar",
  BCHUSDT: "bitcoin-cash", TAOUSDT: "bittensor",
  XMRUSDT: "monero", ZECUSDT: "zcash", CROUSDT: "crypto-com-chain",
  OKBUSDT: "okb", ONDOUSDT: "ondo-finance",
};

export default function PaperTradingPage() {
  const nav = useNavigate();
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState(null);
  const [error, setError] = useState(null);

  const [side, setSide] = useState("BUY");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [amount, setAmount] = useState(500);
  const [amountMode, setAmountMode] = useState("quote");
  const [useTestnet, setUseTestnet] = useState(false);
  const [testnetStatus, setTestnetStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const { subscription } = useSubscription();
  const testnetAllowed = !!subscription?.plan?.limits?.testnet;

  // Live market state
  const [marketCoins, setMarketCoins] = useState([]);
  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [flashMap, setFlashMap] = useState({});
  const [searchQuery, setSearchQuery] = useState("");
  const prevPrices = useRef({});
  const marketIntervalRef = useRef(null);
  const symToCg = useRef({ ...STATIC_SYM_TO_CG });

  const load = async () => {
    setError(null);
    try {
      const [p, t, s] = await Promise.all([
        api.get("/paper/portfolio"),
        api.get("/paper/trades", { params: { limit: 50 } }),
        api.get("/settings/exchange/binance-testnet"),
      ]);
      setPortfolio(p.data);
      setTrades(t.data.trades || []);
      setTestnetStatus(s.data);
    } catch (e) {
      setError(getErrorMessage(e, "Failed to load portfolio"));
    }
  };

  const loadMarket = async () => {
    try {
      const { data } = await api.get("/market/overview", { params: { per_page: 50 } });
      const rawCoins = data.coins || [];

      // Filter out stablecoins / non-tradeable
      const tradeable = rawCoins.filter((c) => !STABLECOIN_IDS.has(c.id));

      // Build dynamic sym→cg map
      tradeable.forEach((c) => {
        const sym = `${c.symbol.toUpperCase()}USDT`;
        symToCg.current[sym] = c.id;
      });

      // Detect price flashes
      const newFlash = {};
      tradeable.forEach((c) => {
        const sym = `${c.symbol.toUpperCase()}USDT`;
        const prev = prevPrices.current[sym];
        if (prev !== undefined && c.current_price !== prev) {
          newFlash[sym] = c.current_price > prev ? "up" : "down";
        }
        prevPrices.current[sym] = c.current_price;
      });
      if (Object.keys(newFlash).length) {
        setFlashMap(newFlash);
        setTimeout(() => setFlashMap({}), 900);
      }

      setMarketCoins(tradeable);
      setLastUpdated(new Date());
      setMarketError(null);
    } catch (e) {
      setMarketError("Failed to load live prices");
    } finally {
      setMarketLoading(false);
    }
  };

  useEffect(() => {
    load();
    loadMarket();
    marketIntervalRef.current = setInterval(loadMarket, 30000);
    return () => clearInterval(marketIntervalRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive tradeable SYMBOLS list from live market data
  const tradeableSymbols = marketCoins.length
    ? marketCoins.map((c) => `${c.symbol.toUpperCase()}USDT`)
    : Object.keys(STATIC_SYM_TO_CG);

  const placeOrder = async () => {
    if (busy) return;
    const value = parseFloat(amount);
    if (!value || value <= 0) return toast.error("Enter a valid amount");
    setBusy(true);
    try {
      const body = { symbol, side, use_testnet: useTestnet };
      if (amountMode === "quote") body.quote_amount = value; else body.quantity = value;
      const { data } = await api.post("/paper/order", body);
      const src = data.source === "binance_testnet" ? "TESTNET" : "PAPER";
      toast.success(`${src} ${data.side}: ${data.quantity.toFixed(6)} @ ${formatUSD(data.price)}`);
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

  const quickTrade = (sym, defaultSide = "BUY") => {
    setSymbol(sym);
    setSide(defaultSide);
    document.getElementById("order-ticket-top")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const viewCoin = (sym) => {
    nav(`/coin/${sym}`);
  };

  // Filtered coins for search
  const filteredCoins = searchQuery.trim()
    ? marketCoins.filter((c) =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.symbol.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : marketCoins;

  // Live price hint for selected symbol in order ticket
  const selectedCoin = marketCoins.find(
    (c) => `${c.symbol.toUpperCase()}USDT` === symbol
  );

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 pb-24">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Paper Trading</h1>
          <p className="text-sm text-muted-foreground mt-1">Practice with virtual $1,000,000 demo portfolio (10 Lakh USD). No real money.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            className="border-[hsl(var(--success))]/50 text-[hsl(var(--success))] hover:bg-[hsl(var(--success))]/10 font-semibold"
            onClick={async () => {
              try {
                const { data } = await api.post("/paper/add-funds", { amount: 1000000 });
                toast.success(`💰 Added $1,000,000 USD (10 Lakh USD) demo cash! Total cash: ${formatUSD(data.cash)}`);
                load();
              } catch (e) {
                toast.error("Failed to add demo cash");
              }
            }}
            data-testid="add-demo-funds-btn"
          >
            💰 +$1M Demo Cash (10 Lakh USD)
          </Button>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-portfolio-btn">
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={resetPortfolio} data-testid="reset-portfolio-btn">
            <RotateCcw className="h-4 w-4 mr-2" /> Reset $1M
          </Button>
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {/* Portfolio Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="portfolio-summary">
        <SummaryCard label="Equity" value={formatUSD(portfolio?.equity)} valueClass="text-2xl font-semibold" testId="portfolio-equity" />
        <SummaryCard label="Cash" value={formatUSD(portfolio?.cash)} testId="portfolio-cash" />
        <SummaryCard label="Total PnL" value={formatUSD(portfolio?.total_pnl)} tone={portfolio?.total_pnl >= 0 ? "up" : "down"} testId="portfolio-total-pnl" />
        <SummaryCard label="Return" value={portfolio ? formatPercent(portfolio.total_pnl_pct) : "—"} tone={portfolio?.total_pnl_pct >= 0 ? "up" : "down"} testId="portfolio-return" />
      </div>

      {/* ── Live Market Panel ───────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card mb-6" data-testid="live-market-panel">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border flex flex-wrap items-center gap-3 justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary animate-pulse" />
            <span className="font-display font-semibold">Live Market</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[hsl(var(--up))]/15 text-[hsl(var(--up))]">
              <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--up))] animate-pulse" />
              LIVE
            </span>
            {!marketLoading && (
              <span className="text-xs text-muted-foreground">
                {filteredCoins.length} coins
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <input
              type="text"
              placeholder="Search coin…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 w-36 rounded-lg border border-border bg-background/60 px-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            {lastUpdated && (
              <span className="text-[11px] text-muted-foreground hidden sm:block">
                {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setMarketLoading(true); loadMarket(); }}>
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* Table */}
        {marketError ? (
          <div className="p-4"><ErrorState message={marketError} onRetry={loadMarket} /></div>
        ) : (
          <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="sticky top-0 z-10 bg-card">
                <tr className="border-b border-border/60 text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 text-left font-medium w-8">#</th>
                  <th className="px-4 py-2.5 text-left font-medium">Coin</th>
                  <th className="px-4 py-2.5 text-right font-medium">Price</th>
                  <th className="px-4 py-2.5 text-right font-medium hidden sm:table-cell">24h %</th>
                  <th className="px-4 py-2.5 text-right font-medium hidden md:table-cell">7d %</th>
                  <th className="px-4 py-2.5 text-right font-medium hidden lg:table-cell">Volume 24h</th>
                  <th className="px-4 py-2.5 text-right font-medium hidden xl:table-cell">Market Cap</th>
                  <th className="px-4 py-2.5 text-center font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {marketLoading && !marketCoins.length
                  ? Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3"><Skeleton className="h-3 w-4" /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Skeleton className="h-7 w-7 rounded-full" />
                          <Skeleton className="h-4 w-24" />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                      <td className="px-4 py-3 text-right hidden sm:table-cell"><Skeleton className="h-4 w-14 ml-auto" /></td>
                      <td className="px-4 py-3 text-right hidden md:table-cell"><Skeleton className="h-4 w-14 ml-auto" /></td>
                      <td className="px-4 py-3 text-right hidden lg:table-cell"><Skeleton className="h-4 w-16 ml-auto" /></td>
                      <td className="px-4 py-3 text-right hidden xl:table-cell"><Skeleton className="h-4 w-20 ml-auto" /></td>
                      <td className="px-4 py-3"><Skeleton className="h-7 w-28 mx-auto" /></td>
                    </tr>
                  ))
                  : filteredCoins.map((c, idx) => {
                    const sym = `${c.symbol.toUpperCase()}USDT`;
                    const chg24 = c.price_change_percentage_24h;
                    const chg7d = c.price_change_percentage_7d_in_currency;
                    const flash = flashMap[sym];
                    const isSelected = symbol === sym;
                    return (
                      <tr
                        key={c.id || sym}
                        className={`transition-all duration-300 ${isSelected ? "bg-primary/5 border-l-2 border-l-primary" : "hover:bg-muted/20"}`}
                        style={{
                          background: flash === "up"
                            ? "hsl(152 62% 45% / 0.1)"
                            : flash === "down"
                              ? "hsl(0 72% 52% / 0.1)"
                              : isSelected ? undefined : undefined,
                        }}
                      >
                        {/* Rank */}
                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                          {c.market_cap_rank || idx + 1}
                        </td>
                        {/* Coin */}
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2.5">
                            {c.image
                              ? <img src={c.image} alt="" className="h-7 w-7 rounded-full flex-shrink-0" />
                              : <div className="h-7 w-7 rounded-full bg-muted flex-shrink-0" />}
                            <div>
                              <div className="font-medium leading-tight text-sm">{c.name}</div>
                              <div className="text-[11px] text-muted-foreground uppercase">{c.symbol}/USDT</div>
                            </div>
                          </div>
                        </td>
                        {/* Price */}
                        <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold text-sm transition-colors ${flash === "up" ? "text-[hsl(var(--up))]" : flash === "down" ? "text-[hsl(var(--down))]" : ""}`}>
                          {formatUSD(c.current_price)}
                        </td>
                        {/* 24h */}
                        <td className={`px-4 py-2.5 text-right font-mono tabular-nums text-xs hidden sm:table-cell ${clsxColor(chg24)}`}>
                          <div className="flex items-center justify-end gap-0.5">
                            {chg24 != null && (chg24 >= 0
                              ? <TrendingUp className="h-3 w-3 flex-shrink-0" />
                              : <TrendingDown className="h-3 w-3 flex-shrink-0" />)}
                            {formatPercent(chg24)}
                          </div>
                        </td>
                        {/* 7d */}
                        <td className={`px-4 py-2.5 text-right font-mono tabular-nums text-xs hidden md:table-cell ${clsxColor(chg7d)}`}>
                          {formatPercent(chg7d)}
                        </td>
                        {/* Volume */}
                        <td className="px-4 py-2.5 text-right text-xs text-muted-foreground font-mono hidden lg:table-cell">
                          {c.total_volume ? `$${(c.total_volume / 1e6).toFixed(0)}M` : "—"}
                        </td>
                        {/* Market Cap */}
                        <td className="px-4 py-2.5 text-right text-xs text-muted-foreground font-mono hidden xl:table-cell">
                          {c.market_cap ? `$${(c.market_cap / 1e9).toFixed(2)}B` : "—"}
                        </td>
                        {/* Actions */}
                        <td className="px-4 py-2.5">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => quickTrade(sym, "BUY")}
                              title={`Buy ${c.name}`}
                              className="px-2 py-1 text-[10px] font-bold rounded bg-[hsl(var(--up))]/15 text-[hsl(var(--up))] hover:bg-[hsl(var(--up))]/30 transition-colors"
                            >
                              Buy
                            </button>
                            <button
                              onClick={() => quickTrade(sym, "SELL")}
                              title={`Sell ${c.name}`}
                              className="px-2 py-1 text-[10px] font-bold rounded bg-[hsl(var(--down))]/15 text-[hsl(var(--down))] hover:bg-[hsl(var(--down))]/30 transition-colors"
                            >
                              Sell
                            </button>
                            <button
                              onClick={() => viewCoin(sym)}
                              title={`View ${c.name} chart`}
                              className="px-2 py-1 text-[10px] font-bold rounded bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground transition-colors flex items-center gap-0.5"
                            >
                              <ExternalLink className="h-2.5 w-2.5" />
                              View
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
            {!marketLoading && filteredCoins.length === 0 && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                No coins found for "{searchQuery}"
              </div>
            )}
          </div>
        )}
        <div className="px-4 py-2 border-t border-border/40 text-[11px] text-muted-foreground flex items-center gap-1">
          <Zap className="h-3 w-3 flex-shrink-0" />
          Buy/Sell pre-fills the order ticket · View opens the full chart · Prices auto-refresh every 30s
        </div>
      </div>

      {/* ── Order ticket + Holdings ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
        {/* Order ticket */}
        <section className="lg:col-span-4" id="order-ticket-top">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Wallet className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">Place Order</div>
            </div>

            {/* Buy / Sell tabs */}
            <div data-testid="order-ticket-side-tabs" className="grid grid-cols-2 rounded-lg bg-muted/40 p-1 mb-3">
              <button
                type="button"
                data-testid="order-tab-buy"
                onClick={() => setSide("BUY")}
                className={`h-9 rounded-md text-sm font-semibold transition-colors ${side === "BUY" ? "bg-[hsl(var(--up))]/15 text-[hsl(var(--up))]" : "text-muted-foreground hover:text-foreground"}`}
              >Buy</button>
              <button
                type="button"
                data-testid="order-tab-sell"
                onClick={() => setSide("SELL")}
                className={`h-9 rounded-md text-sm font-semibold transition-colors ${side === "SELL" ? "bg-[hsl(var(--down))]/15 text-[hsl(var(--down))]" : "text-muted-foreground hover:text-foreground"}`}
              >Sell</button>
            </div>

            <div className="space-y-3">
              {/* Symbol */}
              <div>
                <Label>Symbol</Label>
                <Select value={symbol} onValueChange={setSymbol}>
                  <SelectTrigger data-testid="order-symbol-select" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {tradeableSymbols.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Live price hint */}
              {selectedCoin && (
                <div className="flex items-center justify-between rounded-lg bg-muted/30 border border-border/60 px-3 py-2">
                  <div className="flex items-center gap-2">
                    {selectedCoin.image && (
                      <img src={selectedCoin.image} alt="" className="h-5 w-5 rounded-full" />
                    )}
                    <span className="text-xs text-muted-foreground">{selectedCoin.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono font-semibold">{formatUSD(selectedCoin.current_price)}</div>
                    <div className={`text-[11px] font-mono ${clsxColor(selectedCoin.price_change_percentage_24h)}`}>
                      {formatPercent(selectedCoin.price_change_percentage_24h)} 24h
                    </div>
                  </div>
                </div>
              )}

              {/* Amount */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>Amount</Label>
                  <div className="flex items-center gap-1.5">
                    <div className="flex rounded-md border border-border overflow-hidden text-[11px]">
                      <button
                        type="button"
                        onClick={() => setAmountMode("quote")}
                        className={`px-2 py-0.5 transition-colors font-medium ${amountMode === "quote" ? "bg-primary text-primary-foreground font-semibold" : "bg-muted/40 text-muted-foreground hover:text-foreground"}`}
                      >
                        USD ($)
                      </button>
                      <button
                        type="button"
                        onClick={() => setAmountMode("qty")}
                        className={`px-2 py-0.5 transition-colors font-medium ${amountMode === "qty" ? "bg-primary text-primary-foreground font-semibold" : "bg-muted/40 text-muted-foreground hover:text-foreground"}`}
                      >
                        Qty (Coins)
                      </button>
                    </div>
                  </div>
                </div>

                {/* Holding / Balance hint */}
                {side === "SELL" ? (
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground bg-muted/20 border border-border/50 px-2.5 py-1.5 rounded-lg mb-1.5">
                    <span>
                      Holding: <strong className="text-foreground">{portfolio?.holdings?.find(h => h.symbol === symbol)?.quantity ? portfolio.holdings.find(h => h.symbol === symbol).quantity.toFixed(6) : "0.000000"} {symbol.replace("USDT", "")}</strong>
                    </span>
                    {portfolio?.holdings?.find(h => h.symbol === symbol) && (
                      <button
                        type="button"
                        onClick={() => {
                          const h = portfolio.holdings.find(x => x.symbol === symbol);
                          setAmountMode("qty");
                          setAmount(h.quantity);
                        }}
                        className="text-xs font-bold text-primary hover:underline ml-2"
                      >
                        Sell 100% (MAX)
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground bg-muted/20 border border-border/50 px-2.5 py-1.5 rounded-lg mb-1.5">
                    <span>
                      Cash Avail: <strong className="text-foreground">{formatUSD(portfolio?.cash || 0)}</strong>
                    </span>
                  </div>
                )}

                <Input
                  data-testid="order-ticket-quantity-input"
                  type="number" min="0" step="any"
                  value={amount} onChange={(e) => setAmount(e.target.value)}
                  className="mt-1 font-mono" placeholder={amountMode === "quote" ? "USD amount to trade" : "Coin quantity"}
                />

                {/* Quick percentage buttons */}
                <div className="grid grid-cols-4 gap-1.5 mt-2">
                  {[25, 50, 75, 100].map((pct) => (
                    <button
                      key={pct}
                      type="button"
                      onClick={() => {
                        if (side === "SELL") {
                          const h = portfolio?.holdings?.find(x => x.symbol === symbol);
                          if (h && h.quantity > 0) {
                            setAmountMode("qty");
                            setAmount(pct === 100 ? h.quantity : Number((h.quantity * (pct / 100)).toFixed(6)));
                          } else {
                            toast.error(`No ${symbol} holding available to sell`);
                          }
                        } else {
                          const cash = portfolio?.cash || 0;
                          if (cash > 0) {
                            setAmountMode("quote");
                            setAmount(Math.floor(cash * (pct / 100)));
                          }
                        }
                      }}
                      className="py-1 px-1 text-xs font-mono font-semibold rounded border border-border/70 bg-muted/30 hover:bg-primary/15 hover:border-primary/40 hover:text-primary transition-colors text-center"
                    >
                      {pct === 100 ? "MAX" : `${pct}%`}
                    </button>
                  ))}
                </div>
              </div>

              {/* Testnet toggle */}
              <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2.5 flex items-center justify-between" data-testid="testnet-toggle-card">
                <div>
                  <div className="text-xs font-medium">Route via Binance testnet</div>
                  <div className="text-[11px] text-muted-foreground">
                    {!testnetAllowed
                      ? "Elite plan only"
                      : (testnetStatus?.enabled ? "Keys enabled" : (testnetStatus?.configured ? "Keys configured — enable in Settings" : "Add keys in Settings"))}
                  </div>
                </div>
                <Switch
                  checked={useTestnet}
                  onCheckedChange={(v) => {
                    if (v && !testnetAllowed) { toast.error("Testnet execution is an Elite plan feature"); return; }
                    if (v && !testnetStatus?.enabled) { toast.error("Enable Binance testnet in Settings first"); return; }
                    setUseTestnet(v);
                  }}
                  disabled={!testnetAllowed}
                  data-testid="paper-testnet-switch"
                />
              </div>

              {/* Manual Submit */}
              <Button
                className={`w-full font-semibold ${side === "BUY" ? "bg-[hsl(var(--up))] hover:bg-[hsl(var(--up))]/90 text-white" : "bg-[hsl(var(--down))] hover:bg-[hsl(var(--down))]/90 text-white"}`}
                onClick={placeOrder} disabled={busy} data-testid="order-ticket-submit-button"
              >
                {busy
                  ? <><span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" /> Placing…</>
                  : `${side} ${symbol}${useTestnet ? " (Testnet)" : ""}`}
              </Button>

              {/* AI Auto Buy/Sell/Hold Button */}
              <div className="pt-2 border-t border-border/50">
                <Button
                  variant="outline"
                  className="w-full font-semibold border-primary/50 text-primary hover:bg-primary/10 flex items-center justify-center gap-2"
                  onClick={async () => {
                    if (busy) return;
                    setBusy(true);
                    try {
                      toast.info(`Evaluating 5 AI Agents for ${symbol}…`);
                      const { data: sigData } = await api.post("/ai/signal", {
                        symbol,
                        timeframe: "1h",
                        model: "gemini",
                      });

                      const res0 = sigData?.results?.[0];
                      if (res0?.error) {
                        toast.error(`AI Model Error: ${res0.error}`);
                        return;
                      }

                      const intel = res0?.trade_intelligence || {};
                      const decision = intel.decision_engine || {};
                      const verdict = decision.verdict;
                      const action = decision.signal_action || "HOLD";
                      const score = decision.trade_score || 0;
                      const circuitBreaker = decision.circuit_breaker_tripped;

                      if (circuitBreaker || verdict === "NO TRADE") {
                        toast.warning(
                          `🔴 AI Auto-Trader: NO TRADE executed. Risk Circuit Breaker Active (Score: ${score}/100). ${decision.reason || ""}`,
                          { duration: 6000 }
                        );
                        return;
                      }

                      if (verdict === "WAIT" || action === "HOLD") {
                        toast.info(
                          `🟡 AI Auto-Trader: Decision HOLD/WAIT. Setup score ${score}/100. Capital preserved in cash.`,
                          { duration: 5000 }
                        );
                        return;
                      }

                      const sideToExecute = action === "SELL" ? "SELL" : "BUY";
                      const orderPayload = {
                        symbol,
                        side: sideToExecute,
                        quote_amount: Number(amount) || 500,
                        use_testnet: useTestnet,
                      };

                      const { data: trade } = await api.post("/paper/order", orderPayload);
                      toast.success(
                        `🟢 AI Auto-Trader: Executed ${trade.side} ${trade.quantity?.toFixed(6)} ${symbol} @ ${formatUSD(trade.price)} (Trade Quality Score: ${score}/100)!`
                      );
                      load();
                    } catch (e) {
                      toast.error(e?.response?.data?.detail || "AI Auto-Trade failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                  disabled={busy}
                  data-testid="ai-auto-trade-button"
                >
                  <Zap className="h-4 w-4 text-primary fill-primary/20" />
                  <span>⚡ AI Auto Buy / Sell / Hold Share Trader</span>
                </Button>
                <p className="text-[10px] text-muted-foreground text-center mt-1.5 leading-relaxed">
                  Evaluates Trend, Volume, Liquidity, Sentiment & Risk agents $\rightarrow$ Automatically places trade if 5-Agent Risk Gate approves setup.
                </p>
              </div>

              {/* View chart link */}
              <button
                onClick={() => viewCoin(symbol)}
                className="w-full flex items-center justify-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
              >
                <ExternalLink className="h-3 w-3" /> View full chart for {symbol}
              </button>
            </div>
          </div>
        </section>

        {/* Holdings + trades */}
        <section className="lg:col-span-8 space-y-4">
          {/* Holdings */}
          <div className="rounded-xl border border-border bg-card">
            <div className="px-4 py-3 border-b border-border font-display font-semibold">Holdings</div>
            {!portfolio?.holdings?.length ? (
              <div className="p-4">
                <EmptyState title="No positions yet" description="Place your first buy order to open a position." />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table data-testid="paper-holdings-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Avg Price</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                      <TableHead className="text-right">Unrealized PnL</TableHead>
                      <TableHead className="text-center">Actions</TableHead>
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
                          {formatUSD(h.unrealized_pnl)}{" "}
                          <span className="text-xs">({formatPercent(h.unrealized_pnl_pct)})</span>
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => {
                                setSymbol(h.symbol);
                                setSide("SELL");
                                setAmountMode("qty");
                                setAmount(h.quantity);
                                document.getElementById("order-ticket-top")?.scrollIntoView({ behavior: "smooth", block: "center" });
                              }}
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded bg-[hsl(var(--down))]/15 text-[hsl(var(--down))] hover:bg-[hsl(var(--down))]/25 transition-colors"
                            >
                              Sell
                            </button>
                            <button
                              type="button"
                              onClick={() => viewCoin(h.symbol)}
                              className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-semibold rounded bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/70 transition-colors"
                            >
                              <ExternalLink className="h-2.5 w-2.5" /> View
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          {/* Trade history */}
          <div className="rounded-xl border border-border bg-card">
            <div className="px-4 py-3 border-b border-border font-display font-semibold">Trade History</div>
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
                      <TableHead className="text-center">Chart</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell className="text-xs text-muted-foreground">{shortDate(t.created_at)}</TableCell>
                        <TableCell className="font-medium">{t.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={t.side === "BUY" ? "text-[hsl(var(--up))] border-[hsl(var(--up))]/40" : "text-[hsl(var(--down))] border-[hsl(var(--down))]/40"}>
                            {t.side}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{t.quantity.toFixed(6)}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">{formatUSD(t.price)}</TableCell>
                        <TableCell className={`text-right font-mono tabular-nums ${clsxColor(t.realized_pnl)}`}>
                          {t.realized_pnl ? formatUSD(t.realized_pnl) : "—"}
                        </TableCell>
                        <TableCell className="text-center">
                          <button
                            onClick={() => viewCoin(t.symbol)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-semibold rounded bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/70 transition-colors"
                          >
                            <ExternalLink className="h-2.5 w-2.5" /> View
                          </button>
                        </TableCell>
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
