import React, { useState, useEffect, useRef, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { TrendingUp, Mail, Lock, UserPlus, User, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { getErrorMessage } from "@/lib/api";

const GOOGLE_CLIENT_ID = "152641593792-lk9n6hsi6d4k7uskr843h79cm09v9pdj.apps.googleusercontent.com";

export default function SignupPage() {
  const { signUp, signInDemo, signInWithGoogleToken } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
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
      nav("/dashboard", { replace: true });
    } catch (e) {
      toast.error(getErrorMessage(e, "Backend connection failed. Please ensure the backend is active."));
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
      toast.success("Welcome to SignalForge!");
      nav("/dashboard", { replace: true });
    } catch (e) {
      toast.error(getErrorMessage(e, "Google sign-in failed"));
    } finally {
      setBusy(false);
    }
  }, [signInWithGoogleToken, nav]);

  useEffect(() => {
    // Initialize Google Identity Services
    const initGoogle = () => {
      if (!window.google?.accounts?.id) {
        // GSI script not loaded yet, retry
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
          text: "continue_with",
          shape: "rectangular",
        });
      }
    };
    initGoogle();
  }, [handleGoogleResponse]);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (password.length < 6) return toast.error("Password must be at least 6 characters");
    setBusy(true);
    try {
      await signUp(email.trim(), password, name.trim() || null);
      toast.success("Welcome to SignalForge");
      nav("/dashboard", { replace: true });
    } catch (e) {
      toast.error(getErrorMessage(e, "Signup failed — check your connection to backend"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground grid lg:grid-cols-2">
      <div className="relative hidden lg:flex items-center justify-center p-12 border-r border-border">
        <div className="absolute inset-0 hero-glow" />
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="relative max-w-md">
          <Link to="/landing" className="flex items-center gap-2 mb-8">
            <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <span className="font-display font-semibold text-xl">SignalForge</span>
          </Link>
          <h1 className="font-display font-semibold text-3xl leading-tight">Start trading with an AI analyst — free.</h1>
          <p className="mt-3 text-muted-foreground">Get instant BUY / SELL / HOLD signals with reasoning, backtest strategies, and paper-trade $10,000 risk-free.</p>
          <div className="mt-8 space-y-3 text-sm text-muted-foreground">
            <div>→ Two AI models, one dashboard.</div>
            <div>→ Real market data, no delays, no mocks.</div>
            <div>→ Test strategies before you trust them.</div>
          </div>
        </motion.div>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="signup-form">
          <div className="lg:hidden flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="font-display font-semibold text-lg">SignalForge</span>
          </div>
          <div>
            <h2 className="font-display font-semibold text-2xl">Create your account</h2>
            <p className="text-sm text-muted-foreground mt-1">$10,000 paper account included. No credit card.</p>
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
              <Label htmlFor="signup-name">Name (optional)</Label>
              <div className="relative mt-1.5">
                <User className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input id="signup-name" data-testid="signup-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex" className="pl-10 h-11" />
              </div>
            </div>
            <div>
              <Label htmlFor="signup-email">Email</Label>
              <div className="relative mt-1.5">
                <Mail className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input id="signup-email" data-testid="signup-email-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="pl-10 h-11" />
              </div>
            </div>
            <div>
              <Label htmlFor="signup-password">Password</Label>
              <div className="relative mt-1.5">
                <Lock className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input id="signup-password" data-testid="signup-password-input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 6 characters" className="pl-10 h-11" />
              </div>
            </div>
          </div>

          <Button type="submit" className="w-full h-11" disabled={busy} data-testid="signup-submit-button">
            {busy ? <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Creating…</> : <><UserPlus className="h-4 w-4 mr-2" /> Create account</>}
          </Button>

          <div className="text-sm text-muted-foreground text-center">
            Already have an account? <Link to="/login" className="text-primary underline underline-offset-4">Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
