import React, { useEffect, useState } from "react";
import { NavLink, useLocation, Link } from "react-router-dom";
import {
  LayoutDashboard, Sparkles, FlaskConical, Wallet, Star, Bell, Settings as SettingsIcon,
  TrendingUp, LogOut, ChevronRight, Bot as BotIcon, Check, CreditCard, Crown, Zap
} from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { useSubscription } from "@/context/SubscriptionContext";
import { api } from "@/lib/api";
import { shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
  Popover, PopoverContent, PopoverTrigger
} from "@/components/ui/popover";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard-link" },
  { to: "/signals", label: "AI Signals", icon: Sparkles, testId: "nav-signals-link" },
  { to: "/bots", label: "AI Bots", icon: BotIcon, testId: "nav-bots-link" },
  { to: "/backtest", label: "Backtesting", icon: FlaskConical, testId: "nav-backtest-link" },
  { to: "/paper-trading", label: "Paper Trading", icon: Wallet, testId: "nav-paper-trading-link" },
  { to: "/watchlists", label: "Watchlists", icon: Star, testId: "nav-watchlists-link" },
  { to: "/alerts", label: "Alerts", icon: Bell, testId: "nav-alerts-link" },
  { to: "/pricing", label: "Pricing", icon: CreditCard, testId: "nav-pricing-link" },
  { to: "/settings", label: "Settings", icon: SettingsIcon, testId: "nav-settings-link" },
];

const planBadgeCfg = {
  free:  { icon: null,   cls: "text-muted-foreground border-border" },
  pro:   { icon: Zap,    cls: "text-primary border-primary/40 bg-primary/8" },
  elite: { icon: Crown,  cls: "text-[hsl(var(--warning))] border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/8" },
};

export function AppShell({ children }) {
  const { user, signOut } = useAuth();
  const { subscription } = useSubscription();
  const location = useLocation();
  const planId = subscription?.plan_id || "free";
  const planCfg = planBadgeCfg[planId] || planBadgeCfg.free;
  const PlanIcon = planCfg.icon;

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Left rail */}
      <aside className="hidden md:flex md:w-64 lg:w-72 flex-col border-r border-border bg-card/40 backdrop-blur-sm" data-testid="app-sidebar">
        <div className="px-5 py-5 border-b border-border">
          <NavLink to="/dashboard" className="flex items-center gap-2" data-testid="brand-link">
            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" strokeWidth={2.2} />
            </div>
            <div className="leading-tight">
              <div className="font-display text-lg font-semibold tracking-tight">SignalForge</div>
              <div className="text-[11px] text-muted-foreground uppercase tracking-wider">AI Crypto Desk</div>
            </div>
          </NavLink>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const active = location.pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={item.testId}
                className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  active ? "bg-muted/60 text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                }`}
              >
                {active && (
                  <motion.span layoutId="nav-indicator" className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full bg-primary" />
                )}
                <Icon className="h-[18px] w-[18px]" strokeWidth={1.8} />
                <span className="flex-1">{item.label}</span>
                {active && <ChevronRight className="h-4 w-4 text-muted-foreground/60" />}
              </NavLink>
            );
          })}
        </nav>

        <div className="px-3 py-3 border-t border-border">
          <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs text-muted-foreground">
            <div className="font-semibold text-foreground mb-1 font-display">AI Trading Bots</div>
            <div>Let Claude or Gemini trade for you on a schedule — fully configurable guardrails.</div>
          </div>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-40 h-14 border-b border-border bg-background/80 backdrop-blur-md flex items-center px-4 md:px-6" data-testid="app-topbar">
          <div className="md:hidden flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="font-display font-semibold">SignalForge</span>
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-[hsl(var(--success))] animate-pulse" />
              Live markets
            </div>
            <Link to="/pricing" data-testid="plan-badge">
              <Badge variant="outline" className={`gap-1 font-medium hover:opacity-90 ${planCfg.cls}`}>
                {PlanIcon ? <PlanIcon className="h-3 w-3" /> : null}
                {(subscription?.plan?.name) || "Free"}
              </Badge>
            </Link>
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-9 px-2 gap-2" data-testid="user-menu-trigger">
                  <Avatar className="h-7 w-7">
                    {user?.picture ? <AvatarImage src={user.picture} alt={user.name} /> : null}
                    <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                      {(user?.name || user?.email || "U").slice(0, 1).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline text-sm">{user?.name || user?.email}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{user?.name || "Trader"}</span>
                    <span className="text-xs text-muted-foreground">{user?.email}</span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => (window.location.href = "/pricing")} data-testid="user-menu-pricing">
                  <CreditCard className="h-4 w-4 mr-2" /> Pricing & plans
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => (window.location.href = "/settings")} data-testid="user-menu-settings">
                  <SettingsIcon className="h-4 w-4 mr-2" /> Settings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={signOut} data-testid="user-menu-logout" className="text-[hsl(var(--danger))]">
                  <LogOut className="h-4 w-4 mr-2" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Mobile nav bar */}
        <div className="md:hidden border-b border-border overflow-x-auto" data-testid="mobile-nav">
          <div className="flex gap-1 px-3 py-2 min-w-max">
            {NAV_ITEMS.map((item) => {
              const active = location.pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs whitespace-nowrap ${
                    active ? "bg-muted text-foreground" : "text-muted-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        </div>

        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}


function NotificationBell() {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/notifications", { params: { limit: 30 } });
      setItems(data.notifications || []);
      setUnread(data.unread_count || 0);
      return data;
    } catch { /* silent */ }
  };

  useEffect(() => {
    let prevUnread = 0;
    let cancelled = false;
    const poll = async () => {
      const data = await load();
      if (data && data.unread_count > prevUnread && prevUnread > 0) {
        // Show a toast for the newest triggered notification
        const latest = (data.notifications || []).find((n) => !n.read);
        if (latest) toast(latest.title, { description: latest.body });
      }
      prevUnread = data?.unread_count ?? prevUnread;
    };
    poll();
    const iv = setInterval(() => { if (!cancelled) poll(); }, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  const markAllRead = async () => {
    try { await api.post("/notifications/mark-read"); load(); } catch {}
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" data-testid="notifications-bell">
          <Bell className="h-4 w-4" />
          {unread > 0 ? (
            <span className="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 rounded-full bg-[hsl(var(--warning))] text-[10px] font-semibold text-black flex items-center justify-center" data-testid="notifications-unread-count">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0" data-testid="notifications-popover">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="font-display font-semibold">Notifications</div>
          {unread > 0 ? (
            <button onClick={markAllRead} className="text-xs text-primary hover:underline" data-testid="notifications-mark-read">
              <Check className="h-3 w-3 inline mr-0.5" /> Mark all read
            </button>
          ) : null}
        </div>
        {!items.length ? (
          <div className="p-6 text-center text-sm text-muted-foreground">No notifications yet.</div>
        ) : (
          <ScrollArea className="max-h-96">
            <div className="divide-y divide-border/60" data-testid="notifications-list">
              {items.map((n) => (
                <div key={n.id} className={`px-4 py-3 text-sm ${n.read ? "opacity-70" : ""}`}>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={`text-[10px] ${kindColor(n.kind)}`}>{n.kind}</Badge>
                    <div className="font-medium truncate flex-1">{n.title}</div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">{n.body}</div>
                  <div className="text-[10px] text-muted-foreground/70 mt-1">{shortDate(n.created_at)}</div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}

function kindColor(kind) {
  if (kind === "alert") return "text-[hsl(var(--warning))] border-[hsl(var(--warning))]/40";
  if (kind === "bot_trade") return "text-[hsl(var(--success))] border-[hsl(var(--success))]/40";
  if (kind === "bot_skip") return "text-muted-foreground";
  return "text-muted-foreground";
}
