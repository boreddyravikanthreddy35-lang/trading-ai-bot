import React from "react";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingCard({ height = "h-40", className = "" }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-4 ${className}`}>
      <Skeleton className="h-5 w-1/3 mb-4" />
      <Skeleton className={`w-full ${height}`} />
    </div>
  );
}

export function LoadingRow() {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-border/60">
      <Skeleton className="h-8 w-8 rounded-full" />
      <Skeleton className="h-4 w-24" />
      <div className="flex-1" />
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-4 w-16" />
    </div>
  );
}

export function ErrorState({ message = "Something went wrong", onRetry, testId = "error-banner" }) {
  return (
    <div data-testid={testId} className="rounded-xl border border-[hsl(var(--danger))]/40 bg-[hsl(var(--danger))]/8 p-4">
      <div className="text-sm text-[hsl(var(--danger))] font-medium">{message}</div>
      {onRetry ? (
        <button data-testid="retry-button" onClick={onRetry} className="mt-2 text-xs underline text-muted-foreground hover:text-foreground">
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="rounded-xl border border-dashed border-border p-8 text-center">
      <div className="font-display text-lg font-semibold">{title}</div>
      {description ? <div className="text-sm text-muted-foreground mt-1">{description}</div> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
