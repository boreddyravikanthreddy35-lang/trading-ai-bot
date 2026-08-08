import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { TrendingUp, Mail, Lock, LogIn } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const { signIn } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

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
      toast.error(e?.response?.data?.detail || "Invalid credentials");
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = () => {
    const redirect = `${window.location.origin}/oauth/callback`;
    const url = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
    window.location.href = url;
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

          <Button type="button" variant="outline" className="w-full h-11" onClick={googleLogin} data-testid="google-oauth-button">
            <GoogleIcon /> Continue with Google
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

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 mr-2" aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.9h5.4c-.2 1.5-1.7 4.4-5.4 4.4-3.2 0-5.9-2.7-5.9-6s2.7-6 5.9-6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.9 4 14.7 3 12 3 6.9 3 2.7 7.2 2.7 12.5S6.9 22 12 22c6.9 0 9.4-4.8 9.4-8.5 0-.6-.1-1-.1-1.3H12z"/>
      <path fill="#4285F4" d="M21.4 12.5c0-.6-.1-1-.1-1.3H12v3.9h5.4c-.2 1.5-1.7 4.4-5.4 4.4"/>
    </svg>
  );
}
