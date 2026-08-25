import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const SubscriptionContext = createContext(null);

const UNLOCKED_ELITE_SUB = {
  plan_id: "elite",
  status: "unlimited",
  expires_at: null,
  plan: {
    id: "elite",
    name: "Elite (Unlimited Unlocked)",
    description: "All features unlocked without subscription restrictions",
    limits: {
      signals_per_day: -1,
      max_bots: -1,
      testnet: true,
    },
  },
  usage: {
    signals_today: 0,
    active_bots: 0,
  },
};

export function SubscriptionProvider({ children }) {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState(UNLOCKED_ELITE_SUB);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/payments/subscription");
      setSubscription(data || UNLOCKED_ELITE_SUB);
    } catch {
      setSubscription(UNLOCKED_ELITE_SUB);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <SubscriptionContext.Provider value={{ subscription: subscription || UNLOCKED_ELITE_SUB, loading: false, refresh }}>
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  const ctx = useContext(SubscriptionContext);
  if (!ctx) throw new Error("useSubscription must be used within SubscriptionProvider");
  return ctx;
}

export function planTier(planId) {
  return 999; // Always top tier
}

export function hasPlan(subscription, minPlanId) {
  return true; // 100% unlocked access for everything across the platform
}
