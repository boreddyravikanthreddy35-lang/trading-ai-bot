import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, ArrowRight, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useSubscription } from "@/context/SubscriptionContext";
import { Button } from "@/components/ui/button";

const POLL_INTERVAL_MS = 2000;
const MAX_ATTEMPTS = 15; // ~30s total

export default function BillingSuccessPage() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const nav = useNavigate();
  const { refresh } = useSubscription();

  const [status, setStatus] = useState("polling"); // polling | success | failed | timeout
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!sessionId) { setStatus("failed"); return; }
    let attempts = 0;
    let timer;

    const poll = async () => {
      attempts += 1;
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        setDetail(data);
        if (data.payment_status === "paid") {
          setStatus("success");
          toast.success(`Welcome to ${data.plan_id?.toUpperCase()}!`);
          refresh();
          return;
        }
        if (["expired", "failed"].includes(data.payment_status) || ["expired", "failed"].includes(data.status)) {
          setStatus("failed");
          return;
        }
      } catch (e) {
        /* transient — keep polling */
      }
      if (attempts >= MAX_ATTEMPTS) {
        setStatus("timeout");
        return;
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    };
    poll();
    return () => timer && clearTimeout(timer);
    // eslint-disable-next-line
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-md rounded-2xl border border-border bg-card p-8 text-center relative overflow-hidden"
        data-testid="billing-status-card"
      >
        <div className="absolute inset-0 hero-glow pointer-events-none" />
        <div className="relative">
          {status === "polling" && (
            <>
              <Loader2 className="h-10 w-10 text-primary animate-spin mx-auto" />
              <h1 className="mt-4 font-display font-semibold text-2xl">Confirming your payment…</h1>
              <p className="mt-2 text-sm text-muted-foreground">This usually takes a few seconds.</p>
            </>
          )}
          {status === "success" && (
            <>
              <CheckCircle2 className="h-12 w-12 text-[hsl(var(--success))] mx-auto" />
              <h1 className="mt-4 font-display font-semibold text-2xl">Welcome to {detail?.plan_id?.toUpperCase() || "the plan"}!</h1>
              <p className="mt-2 text-sm text-muted-foreground">Your plan is active. Enjoy the new capacity.</p>
              <div className="mt-5 flex flex-col gap-2">
                <Button onClick={() => nav("/dashboard")} data-testid="billing-success-continue">
                  <Sparkles className="h-4 w-4 mr-2" /> Go to dashboard
                </Button>
                <Button variant="outline" onClick={() => nav("/bots")}>Create your first bot <ArrowRight className="h-4 w-4 ml-1" /></Button>
              </div>
            </>
          )}
          {status === "failed" && (
            <>
              <XCircle className="h-12 w-12 text-[hsl(var(--danger))] mx-auto" />
              <h1 className="mt-4 font-display font-semibold text-2xl">Payment not completed</h1>
              <p className="mt-2 text-sm text-muted-foreground">Your card wasn't charged. You can try again anytime.</p>
              <div className="mt-5 flex flex-col gap-2">
                <Button onClick={() => nav("/pricing")}>Try again</Button>
                <Button variant="outline" onClick={() => nav("/dashboard")}>Back to dashboard</Button>
              </div>
            </>
          )}
          {status === "timeout" && (
            <>
              <Loader2 className="h-10 w-10 text-muted-foreground mx-auto" />
              <h1 className="mt-4 font-display font-semibold text-2xl">Still processing…</h1>
              <p className="mt-2 text-sm text-muted-foreground">Your payment may still be confirming. You can safely close this page — we'll upgrade you as soon as it clears.</p>
              <div className="mt-5">
                <Button variant="outline" onClick={() => nav("/dashboard")}>Back to dashboard</Button>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
