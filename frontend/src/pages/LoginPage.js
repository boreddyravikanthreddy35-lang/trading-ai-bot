import React, { useState, useEffect, useRef, useCallback } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { TrendingUp, Mail, Lock, LogIn, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { getErrorMessage } from "@/lib/api";

const GOOGLE_CLIENT_ID = "152641593792-lk9n6hsi6d4k7uskr843h79cm09v9pdj.apps.googleusercontent.com";

export default function LoginPage() {
  const { signIn, signInDemo, signInWithGoogleToken } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const googleBtnRef = useRef(null);

  const handleDemoLogin = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await signInDemo();
      toast.success("Logged in as Demo Trader!");
      const dest = loc.state?.from?.pathname || "/dashboard";
      nav(dest, { replace: true });
    } catch (e) {
      toast.error(getErrorMessage(e, "Demo sign-in failed — please verify backend is awake"));
    } finally {
      setBusy(false);
    }
  };

  const handleGoogleResponse = useCallback(async (response) => {
    if (!response?.credential) {
      toast.error("Google sign-in failed — no credential received");
      return;
    }
    setBusy(true);
    try {
      await signInWithGoogleToken(response.credential);
      toast.success("Welcome back!");
      const dest = loc.state?.from?.pathname || "/dashboard";
      nav(dest, { replace: true });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Google sign-in failed");
    } finally {
      setBusy(false);
    }
  }, [signInWithGoogleToken, nav, loc.state]);

  useEffect(() => {
    const initGoogle = () => {
      if (!window.google?.accounts?.id) {
        setTimeout(initGoogle, 300);
        return;
      }
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
        auto_select: false,
      });
      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: "outline",
          size: "large",
          width: googleBtnRef.current.offsetWidth || 380,
          text: "signin_with",
          shape: "rectangular",
        });
      }
    };
    initGoogle();
  }, [handleGoogleResponse]);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      toast.success("Welcome back");
      const dest = loc.state?.from?.pathname || "/dashboard";
      nav(dest, { replace: true });
    } catch (e) {
      toast.error(getErrorMessage(e, "Invalid credentials or backend unreachable"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground grid lg:grid-cols-2">
      {/* Brand side */}
      <div className="relative hidden lg:flex items-center justify-center p-12 border-r border-border">
        <div className="absolute inset-0 hero-glow" />
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="relative max-w-md">
          <Link to="/landing" className="flex items-center gap-2 mb-8">
            <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <span className="font-display font-semibold text-xl">SignalForge</span>
          </Link>
          <h1 className="font-display font-semibold text-3xl leading-tight">Welcome back to your AI trading desk.</h1>
          <p className="mt-3 text-muted-foreground">Sign in to view market signals, run backtests, and manage your paper portfolio.</p>
          <ul className="mt-8 space-y-3 text-sm text-muted-foreground">
            <li className="flex items-start gap-2"><span className="text-primary">→</span> Real-time market data from CoinGecko + Kraken.</li>
            <li className="flex items-start gap-2"><span className="text-primary">→</span> Claude Sonnet 4.5 and Gemini 2.5 Pro dual-model signals.</li>
            <li className="flex items-start gap-2"><span className="text-primary">→</span> $10,000 paper account included.</li>
          </ul>
        </motion.div>
      </div>

      {/* Form */}
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="login-form">
          <div className="lg:hidden flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="font-display font-semibold text-lg">SignalForge</span>
          </div>

          <div>
            <h2 className="font-display font-semibold text-2xl">Sign in</h2>
            <p className="text-sm text-muted-foreground mt-1">Use your email or continue with Google.</p>
          </div>

          {/* Google Sign-In button rendered by GSI */}
          <div ref={googleBtnRef} className="w-full min-h-[44px] flex items-center justify-center" data-testid="google-oauth-button" />

          <Button
            type="button"
            variant="outline"
            onClick={handleDemoLogin}
            disabled={busy}
            className="w-full h-11 border-primary/40 bg-primary/10 hover:bg-primary/20 text-primary font-semibold flex items-center justify-center gap-2 transition-all shadow-sm"
          >
            <Zap className="h-4 w-4 text-primary animate-pulse" />
            1-Click Instant Trader Sign In (No Google needed)
          </Button>

          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">or with email</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="login-email">Email</Label>
              <div className="relative mt-1.5">
                <Mail className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  id="login-email" data-testid="login-email-input" type="email" required autoComplete="email"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com" className="pl-10 h-11"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="login-password">Password</Label>
              <div className="relative mt-1.5">
                <Lock className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  id="login-password" data-testid="login-password-input" type="password" required autoComplete="current-password"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••" className="pl-10 h-11"
                />
              </div>
            </div>
          </div>

          <Button type="submit" className="w-full h-11" disabled={busy} data-testid="login-submit-button">
            {busy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Signing in…</> : <><LogIn className="h-4 w-4 mr-2" /> Sign in</>}
          </Button>

          <div className="text-sm text-muted-foreground text-center">
            No account? <Link to="/signup" className="text-primary underline underline-offset-4">Create one</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
