import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { TrendingUp, Mail, Lock, UserPlus, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SignupPage() {
  const { signUp } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

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
      toast.error(e?.response?.data?.detail || "Signup failed");
    } finally {
      setBusy(false);
    }
  };

  const googleSignup = () => {
    const redirect = `${window.location.origin}/oauth/callback`;
    const url = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
    window.location.href = url;
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

          <Button type="button" variant="outline" className="w-full h-11" onClick={googleSignup} data-testid="google-oauth-button">
            <GoogleIcon /> Continue with Google
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

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 mr-2" aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.9h5.4c-.2 1.5-1.7 4.4-5.4 4.4-3.2 0-5.9-2.7-5.9-6s2.7-6 5.9-6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.9 4 14.7 3 12 3 6.9 3 2.7 7.2 2.7 12.5S6.9 22 12 22c6.9 0 9.4-4.8 9.4-8.5 0-.6-.1-1-.1-1.3H12z"/>
    </svg>
  );
}
