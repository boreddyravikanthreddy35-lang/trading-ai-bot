import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  TrendingUp, Sparkles, FlaskConical, Wallet, Bell,
  ShieldCheck, ArrowRight, LineChart
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/landing" className="flex items-center gap-2" data-testid="landing-brand">
            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <span className="font-display font-semibold text-lg">SignalForge</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link to="/login"><Button variant="ghost" data-testid="landing-login-btn">Sign in</Button></Link>
            <Link to="/signup"><Button data-testid="landing-signup-btn">Get started</Button></Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 hero-glow pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-6 pt-20 pb-24">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="max-w-3xl"
          >
            <Badge className="mb-5 bg-primary/10 text-primary border-primary/30" variant="outline">
              <Sparkles className="h-3 w-3 mr-1" /> Powered by Claude Sonnet 4.5 + Gemini 2.5 Pro
            </Badge>
            <h1 className="font-display font-semibold text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight">
              Trade crypto with an AI analyst by your side.
            </h1>
            <p className="mt-5 text-base md:text-lg text-muted-foreground max-w-2xl leading-relaxed">
              SignalForge fuses real-time market data with two frontier LLMs to produce
              transparent BUY / SELL / HOLD signals — complete with reasoning, confidence,
              entry, stop, and take-profit levels. Backtest strategies, paper-trade risk-free,
              and get alerts when the market moves.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/signup">
                <Button size="lg" className="h-11 px-6" data-testid="hero-cta-signup">
                  Start free — $10,000 paper account <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline" className="h-11 px-6" data-testid="hero-cta-login">
                  Sign in
                </Button>
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-6 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-primary" /> No credit card required</div>
              <div className="flex items-center gap-1.5"><LineChart className="h-3.5 w-3.5 text-primary" /> Real market data from CoinGecko + Kraken</div>
              <div className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-primary" /> Claude vs Gemini comparison</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Feature bento */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.35, delay: i * 0.04 }}
                className="rounded-xl border border-border bg-card p-5"
              >
                <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div className="mt-4 font-display font-semibold text-lg">{f.title}</div>
                <div className="mt-1 text-sm text-muted-foreground leading-relaxed">{f.desc}</div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-8 md:p-12">
          <div className="absolute inset-0 hero-glow pointer-events-none" />
          <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
            <div>
              <h2 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Ship your first AI trade in 60 seconds.</h2>
              <p className="mt-2 text-muted-foreground max-w-xl">Create an account, ask the AI for a signal on Bitcoin, and place a paper trade — no keys, no risk.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/signup"><Button size="lg" data-testid="cta-bottom-signup">Create free account</Button></Link>
              <Link to="/login"><Button size="lg" variant="outline">Sign in</Button></Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-xs text-muted-foreground">
          <div>© {new Date().getFullYear()} SignalForge — AI Crypto Analyst</div>
          <div>Educational tool. Not financial advice.</div>
        </div>
      </footer>
    </div>
  );
}

const FEATURES = [
  { title: "AI Trading Signals", icon: Sparkles,
    desc: "Ask Claude, Gemini, or both. Get a structured recommendation with confidence, entry/stop/take-profit, and full reasoning." },
  { title: "Model Comparison", icon: TrendingUp,
    desc: "Run the same market context through both models side-by-side. See where they agree — and where they don't." },
  { title: "Strategy Backtesting", icon: FlaskConical,
    desc: "Test SMA crossovers, RSI mean reversion, and MACD strategies on real historical data. See PnL, win rate, and drawdown." },
  { title: "Paper Trading", icon: Wallet,
    desc: "Start with $10,000 virtual USD. Place market orders, watch your PnL, and simulate positions before risking a dollar." },
  { title: "Watchlists & Alerts", icon: Bell,
    desc: "Track coins you care about. Set threshold alerts — above or below — and act fast when they trigger." },
  { title: "Real Market Data", icon: LineChart,
    desc: "CoinGecko for market overview, Kraken/Bybit/KuCoin OHLCV klines. No mocks, no delays." },
];
