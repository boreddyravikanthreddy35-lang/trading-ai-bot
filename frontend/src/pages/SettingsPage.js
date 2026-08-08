import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Settings as SettingsIcon, Key, Shield, LogOut, User as UserIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/States";

export default function SettingsPage() {
  const { user, signOut } = useAuth();
  const [settings, setSettings] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setError(null);
    try {
      const { data } = await api.get("/settings/exchange/binance-testnet");
      setSettings(data);
      setEnabled(!!data.enabled);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load settings");
    }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!apiKey.trim() || !apiSecret.trim()) return toast.error("API key and secret required");
    try {
      await api.post("/settings/exchange/binance-testnet", { api_key: apiKey.trim(), api_secret: apiSecret.trim(), enabled });
      toast.success("Binance testnet keys saved");
      setApiKey(""); setApiSecret("");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const clearKeys = async () => {
    if (!window.confirm("Remove Binance testnet keys?")) return;
    try {
      await api.delete("/settings/exchange/binance-testnet");
      toast.success("Keys removed");
      load();
    } catch (e) { toast.error("Delete failed"); }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account and exchange integration.</p>
      </div>

      <div className="space-y-6">
        {/* Profile */}
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <UserIcon className="h-4 w-4 text-primary" />
            <div className="font-display font-semibold">Profile</div>
          </div>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <Row label="Name" value={user?.name || "—"} />
            <Row label="Email" value={user?.email} />
            <Row label="Provider" value={user?.provider?.toUpperCase() || "EMAIL"} />
            <Row label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"} />
          </div>
          <div className="mt-4">
            <Button variant="outline" onClick={signOut} data-testid="settings-logout-btn"><LogOut className="h-4 w-4 mr-2" /> Sign out</Button>
          </div>
        </section>

        {/* Binance Testnet */}
        <section className="rounded-xl border border-border bg-card p-5" data-testid="binance-testnet-panel">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-primary" />
              <div className="font-display font-semibold">Binance Testnet Integration</div>
            </div>
            {settings?.configured ? (
              <Badge variant="outline" className={settings.enabled ? "text-[hsl(var(--success))] border-[hsl(var(--success))]/40" : "text-muted-foreground"}>
                {settings.enabled ? "Enabled" : "Configured"}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground">Not configured</Badge>
            )}
          </div>

          <div className="mt-2 flex items-start gap-2 rounded-lg bg-muted/30 border border-border/60 p-3 text-xs text-muted-foreground">
            <Shield className="h-4 w-4 text-primary shrink-0" />
            <div>
              Add your Binance <strong className="text-foreground">testnet</strong> API key + secret to enable simulated live-execution. This is a placeholder for future live trading — orders still route through paper trading until fully enabled.
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label>Testnet API key</Label>
              <Input
                data-testid="binance-api-key-input"
                value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                placeholder={settings?.api_key_masked || "Paste API key"}
                className="mt-1 font-mono text-xs"
              />
            </div>
            <div>
              <Label>Testnet API secret</Label>
              <Input
                data-testid="binance-api-secret-input"
                type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Paste API secret"
                className="mt-1 font-mono text-xs"
              />
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch checked={enabled} onCheckedChange={setEnabled} data-testid="binance-enabled-switch" />
              <span className="text-sm text-muted-foreground">Route future orders through Binance testnet (when live)</span>
            </div>
            <div className="flex items-center gap-2">
              {settings?.configured ? (
                <Button variant="outline" onClick={clearKeys} data-testid="binance-clear-btn">Remove keys</Button>
              ) : null}
              <Button onClick={save} data-testid="binance-save-btn">Save keys</Button>
            </div>
          </div>

          {error ? <div className="mt-3"><ErrorState message={error} onRetry={load} /></div> : null}
        </section>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5">{value ?? "—"}</div>
    </div>
  );
}
