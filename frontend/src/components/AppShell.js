import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Sparkles, FlaskConical, Wallet, Star, Bell, Settings as SettingsIcon,
  TrendingUp, LogOut, User as UserIcon, ChevronRight
} from "lucide-react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard-link" },
  { to: "/signals", label: "AI Signals", icon: Sparkles, testId: "nav-signals-link" },
  { to: "/backtest", label: "Backtesting", icon: FlaskConical, testId: "nav-backtest-link" },
  { to: "/paper-trading", label: "Paper Trading", icon: Wallet, testId: "nav-paper-trading-link" },
  { to: "/watchlists", label: "Watchlists", icon: Star, testId: "nav-watchlists-link" },
  { to: "/alerts", label: "Alerts", icon: Bell, testId: "nav-alerts-link" },
  { to: "/settings", label: "Settings", icon: SettingsIcon, testId: "nav-settings-link" },
];

export function AppShell({ children }) {
  const { user, signOut } = useAuth();
  const location = useLocation();

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
                  active
                    ? "bg-muted/60 text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="nav-indicator"
                    className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full bg-primary"
                  />
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
            <div className="font-semibold text-foreground mb-1 font-display">Paper Trading</div>
            <div>Start with a virtual $10,000. Test strategies risk-free.</div>
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

        <main className="flex-1 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
