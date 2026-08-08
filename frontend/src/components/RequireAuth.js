import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Extra defensive: also check localStorage for token to guard against stale states
  const hasToken = typeof window !== "undefined" && !!localStorage.getItem("sf_token");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }
  if (!user || !hasToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}
