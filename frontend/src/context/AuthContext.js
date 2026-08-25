import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const FIREBASE_ENABLED = Boolean(process.env.REACT_APP_FIREBASE_ENABLED === "true");

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
      if (data?.id) localStorage.setItem("user_id", data.id);
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
    if (data.user?.id) localStorage.setItem("user_id", data.user.id);
    setUser(data.user);
    return data.user;
  }, []);

  const signUp = useCallback(async (email, password, name) => {
    const { data } = await api.post("/auth/signup", { email, password, name });
    localStorage.setItem("sf_token", data.token);
    if (data.user?.id) localStorage.setItem("user_id", data.user.id);
    setUser(data.user);
    return data.user;
  }, []);

  const signInWithGoogleSession = useCallback(async (sessionId) => {
    const { data } = await api.post("/auth/google", { session_id: sessionId });
    localStorage.setItem("sf_token", data.token);
    if (data.user?.id) localStorage.setItem("user_id", data.user.id);
    setUser(data.user);
    return data.user;
  }, []);

  const signInWithFirebase = useCallback(async (idToken) => {
    const { data } = await api.post("/auth/firebase", { id_token: idToken });
    localStorage.setItem("sf_token", data.token);
    if (data.user?.id) localStorage.setItem("user_id", data.user.id);
    setUser(data.user);
    return data.user;
  }, []);

  const signInWithGoogleToken = useCallback(async (credential) => {
    const { data } = await api.post("/auth/google-token", { credential });
    localStorage.setItem("sf_token", data.token);
    if (data.user?.id) localStorage.setItem("user_id", data.user.id);
    setUser(data.user);
    return data.user;
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem("sf_token");
    localStorage.removeItem("user_id");
    setUser(null);
    window.location.replace("/landing");
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signInWithGoogleSession, signInWithGoogleToken, signInWithFirebase, signOut, refresh: fetchMe, firebaseEnabled: FIREBASE_ENABLED }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
