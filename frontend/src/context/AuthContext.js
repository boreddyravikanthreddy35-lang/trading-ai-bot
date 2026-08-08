import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem("sf_token");
    if (!token) { setUser(null); setLoading(false); return; }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (e) {
      localStorage.removeItem("sf_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  const signIn = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("sf_token", data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const signUp = useCallback(async (email, password, name) => {
    const { data } = await api.post("/auth/signup", { email, password, name });
    localStorage.setItem("sf_token", data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const signInWithGoogleSession = useCallback(async (sessionId) => {
    const { data } = await api.post("/auth/google", { session_id: sessionId });
    localStorage.setItem("sf_token", data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem("sf_token");
    setUser(null);
    // Force navigation to landing to guarantee redirect from any protected route
    window.location.replace("/landing");
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signInWithGoogleSession, signOut, refresh: fetchMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
