import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Check, Sparkles, ShieldCheck, Zap, Crown, ArrowRight, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useSubscription } from "@/context/SubscriptionContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const planIconMap = {
  free: ShieldCheck,
  pro: Zap,
  elite: Crown,
};

export default function PricingPage() {
  const [plans, setPlans] = useState(null);
  const [busyPlan, setBusyPlan] = useState(null);
  const { user } = useAuth();
  const { subscription, refresh } = useSubscription();
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/payments/plans");
        setPlans(data.plans || []);
      } catch { setPlans([]); }
    })();
  }, []);

  const startCheckout = async (planId) => {
    if (!user) return nav("/signup", { state: { from: { pathname: "/pricing" } } });
    setBusyPlan(planId);
    try {
      const { data } = await api.post("/payments/checkout", {
        plan_id: planId,
        origin_url: window.location.origin,
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        toast.error("Failed to start checkout");
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Checkout failed");
    } finally { setBusyPlan(null); }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative">
        <div className="absolute inset-0 hero-glow pointer-events-none" />

        {/* Header */}
        <header className="relative border-b border-border/60">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" /> Back
            </Link>
            <div className="text-xs text-muted-foreground">Emergent-managed Stripe sandbox — use test card 4242 4242 4242 4242</div>
          </div>
        </header>

        <div className="relative max-w-6xl mx-auto px-6 pt-14 pb-8 text-center">
          <Badge className="mb-4 bg-primary/10 text-primary border-primary/30" variant="outline">
            <Sparkles className="h-3 w-3 mr-1" /> Choose your plan
          </Badge>
          <h1 className="font-display font-semibold text-3xl md:text-5xl leading-tight tracking-tight">Trade smarter with an AI analyst.</h1>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
            Every plan includes real-time market data, both Claude &amp; Gemini models, and the paper trading portfolio. Upgrade to unlock daily signal capacity, more bots, and testnet execution.
          </p>
          {subscription ? (
            <div className="mt-4 text-xs text-muted-foreground">
              Currently on <span className="text-foreground font-medium">{subscription.plan.name}</span>
              {subscription.expires_at ? ` · renews ${new Date(subscription.expires_at).toLocaleDateString()}` : ""}
            </div>
          ) : null}
        </div>
      </div>

      {/* Plan cards */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        {!plans ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="rounded-2xl border border-border bg-card p-6 h-80 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.map((p) => {
              const Icon = planIconMap[p.id] || ShieldCheck;
              const isCurrent = subscription?.plan_id === p.id;
              const isPro = p.id === "pro";
              return (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 8 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3 }}
                  className={`relative rounded-2xl border ${isPro ? "border-primary/60 ring-1 ring-primary/40" : "border-border"} bg-card p-6 flex flex-col`}
                  data-testid={`pricing-card-${p.id}`}
                >
                  {isPro ? (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-primary text-primary-foreground">Most popular</Badge>
                    </div>
                  ) : null}
                  {isCurrent ? (
                    <div className="absolute -top-3 right-4">
                      <Badge variant="outline" className="bg-background text-[hsl(var(--success))] border-[hsl(var(--success))]/40">Current plan</Badge>
                    </div>
                  ) : null}
                  <div className="flex items-center gap-2">
                    <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <div className="font-display text-lg font-semibold">{p.name}</div>
                      <div className="text-xs text-muted-foreground">{p.description}</div>
                    </div>
                  </div>
                  <div className="mt-5 flex items-baseline gap-1">
                    <span className="font-display text-4xl font-semibold">
                      ${Number(p.price_monthly).toFixed(0)}
                    </span>
                    <span className="text-sm text-muted-foreground">/ month</span>
                  </div>
                  <ul className="mt-5 space-y-2 flex-1">
                    {p.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6">
                    {p.id === "free" ? (
                      <Button variant="outline" className="w-full" disabled={isCurrent} onClick={() => nav(user ? "/dashboard" : "/signup")} data-testid="pricing-cta-free">
                        {isCurrent ? "You're on Free" : (user ? "Go to dashboard" : "Sign up free")}
                      </Button>
                    ) : (
                      <Button
                        className="w-full"
                        disabled={isCurrent || busyPlan === p.id}
                        onClick={() => startCheckout(p.id)}
                        data-testid={`pricing-cta-${p.id}`}
                      >
                        {isCurrent ? "Current plan" : busyPlan === p.id ? (
                          <><span className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" /> Starting checkout…</>
                        ) : (
                          <>Upgrade to {p.name} <ArrowRight className="h-4 w-4 ml-1" /></>
                        )}
                      </Button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* FAQ / small print */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <FaqCard title="Is this real money?" body="No — we use Emergent's managed Stripe sandbox. Charges are simulated with test cards. Great for trying the flow risk-free." />
          <FaqCard title="Can I cancel anytime?" body="Yes. Your plan remains active until the end of the current 30-day cycle, then you're moved back to Free automatically." />
          <FaqCard title="Which test card should I use?" body="Use 4242 4242 4242 4242 with any future expiry and any 3-digit CVC. No email or real details required." />
        </div>
      </section>
    </div>
  );
}

function FaqCard({ title, body }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="font-display font-semibold">{title}</div>
      <div className="mt-1 text-muted-foreground text-sm">{body}</div>
    </div>
  );
}
