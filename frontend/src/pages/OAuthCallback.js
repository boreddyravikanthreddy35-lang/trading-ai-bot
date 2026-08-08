import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export default function OAuthCallback() {
  const { signInWithGoogleSession } = useAuth();
  const nav = useNavigate();
  const [status, setStatus] = useState("Signing you in…");

  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const params = new URLSearchParams(hash);
    const sid = params.get("session_id");
    if (!sid) {
      setStatus("Missing session. Redirecting…");
      const t = setTimeout(() => nav("/login", { replace: true }), 1200);
      return () => clearTimeout(t);
    }
    (async () => {
      try {
        await signInWithGoogleSession(sid);
        toast.success("Signed in with Google");
        nav("/dashboard", { replace: true });
      } catch (e) {
        setStatus("Google sign-in failed");
        toast.error(e?.response?.data?.detail || "OAuth failed");
        setTimeout(() => nav("/login", { replace: true }), 1500);
      }
    })();
  }, [nav, signInWithGoogleSession]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <div className="text-sm text-muted-foreground">{status}</div>
      </div>
    </div>
  );
}
