import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, Crown, Lock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function UpgradeBanner({ title, body, requiredPlan = "Pro", cta = "Upgrade", inline = false, testId = "upgrade-banner" }) {
  const Icon = requiredPlan.toLowerCase() === "elite" ? Crown : Sparkles;
  return (
    <div
      data-testid={testId}
      className={`rounded-xl border border-primary/40 bg-primary/8 p-4 flex items-start gap-3 ${inline ? "" : "mb-4"}`}
    >
      <div className="h-9 w-9 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="font-display font-semibold">{title}</div>
          <Badge className="bg-primary/15 text-primary border-primary/30" variant="outline">{requiredPlan}+</Badge>
        </div>
        <div className="mt-1 text-sm text-muted-foreground">{body}</div>
      </div>
      <Link to="/pricing">
        <Button size="sm" data-testid={`${testId}-cta`}>
          {cta} <ArrowRight className="h-4 w-4 ml-1" />
        </Button>
      </Link>
    </div>
  );
}

export function LockedFeature({ title, description, requiredPlan = "Pro", testId = "locked-feature" }) {
  return (
    <div data-testid={testId} className="rounded-xl border border-dashed border-primary/30 bg-card p-6 text-center">
      <div className="mx-auto h-10 w-10 rounded-full bg-primary/15 border border-primary/30 flex items-center justify-center">
        <Lock className="h-4 w-4 text-primary" />
      </div>
      <div className="mt-3 font-display font-semibold">{title}</div>
      <div className="mt-1 text-sm text-muted-foreground">{description}</div>
      <div className="mt-4 flex items-center justify-center gap-2">
        <Badge className="bg-primary/15 text-primary border-primary/30" variant="outline">Requires {requiredPlan}</Badge>
        <Link to="/pricing">
          <Button size="sm">See plans <ArrowRight className="h-4 w-4 ml-1" /></Button>
        </Link>
      </div>
    </div>
  );
}
