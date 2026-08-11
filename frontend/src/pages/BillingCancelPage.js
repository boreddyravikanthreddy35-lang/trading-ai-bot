import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function BillingCancelPage() {
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 text-center" data-testid="billing-cancel-card">
        <XCircle className="h-10 w-10 text-muted-foreground mx-auto" />
        <h1 className="mt-4 font-display font-semibold text-2xl">Checkout cancelled</h1>
        <p className="mt-2 text-sm text-muted-foreground">No worries — nothing was charged. You can pick a plan whenever you're ready.</p>
        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={() => nav("/pricing")}>Back to pricing</Button>
          <Button variant="outline" onClick={() => nav("/dashboard")}>Back to dashboard</Button>
        </div>
      </div>
    </div>
  );
}
