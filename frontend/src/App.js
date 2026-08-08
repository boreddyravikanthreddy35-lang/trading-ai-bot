import React, { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";

import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import OAuthCallback from "@/pages/OAuthCallback";
import DashboardPage from "@/pages/DashboardPage";
import CoinPage from "@/pages/CoinPage";
import SignalsPage from "@/pages/SignalsPage";
import BacktestPage from "@/pages/BacktestPage";
import PaperTradingPage from "@/pages/PaperTradingPage";
import WatchlistsPage from "@/pages/WatchlistsPage";
import AlertsPage from "@/pages/AlertsPage";
import SettingsPage from "@/pages/SettingsPage";

function Shell({ children }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/dashboard" : "/landing"} replace />;
}

function App() {
  useEffect(() => {
    // Enforce dark mode as default per design guidelines
    document.documentElement.classList.add("dark");
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />

          <Route path="/dashboard" element={<Shell><DashboardPage /></Shell>} />
          <Route path="/coin/:symbol" element={<Shell><CoinPage /></Shell>} />
          <Route path="/signals" element={<Shell><SignalsPage /></Shell>} />
          <Route path="/backtest" element={<Shell><BacktestPage /></Shell>} />
          <Route path="/paper-trading" element={<Shell><PaperTradingPage /></Shell>} />
          <Route path="/watchlists" element={<Shell><WatchlistsPage /></Shell>} />
          <Route path="/alerts" element={<Shell><AlertsPage /></Shell>} />
          <Route path="/settings" element={<Shell><SettingsPage /></Shell>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" theme="dark" />
    </AuthProvider>
  );
}

export default App;
