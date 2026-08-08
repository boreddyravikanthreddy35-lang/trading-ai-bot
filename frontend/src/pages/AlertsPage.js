import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Bell, Plus, Trash2, RefreshCw, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatUSD, shortDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { EmptyState, ErrorState } from "@/components/States";

const SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  const [symbol, setSymbol] = useState("BTCUSDT");
  const [condition, setCondition] = useState("above");
  const [threshold, setThreshold] = useState("");

  const load = async () => {
    setError(null);
    try {
      const { data } = await api.get("/watch/alerts");
      setAlerts(data.alerts || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load alerts");
    }
  };

  const check = async () => {
    try {
      const { data } = await api.post("/watch/alerts/check");
      if (data.triggered?.length) {
        toast.success(`${data.triggered.length} alert(s) triggered`);
      } else {
        toast.info(`Checked ${data.checked} alert(s). None triggered yet.`);
      }
      load();
    } catch (e) { toast.error("Check failed"); }
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    const th = parseFloat(threshold);
    if (!th || isNaN(th)) return toast.error("Enter a valid threshold");
    try {
      await api.post("/watch/alerts", { symbol, condition, threshold: th });
      toast.success("Alert created");
      setOpen(false); setThreshold("");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Create failed"); }
  };

  const del = async (id) => {
    try { await api.delete(`/watch/alerts/${id}`); load(); }
    catch { toast.error("Delete failed"); }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Price Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">Get notified when a coin crosses your threshold.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={check} data-testid="check-alerts-btn"><RefreshCw className="h-4 w-4 mr-2" /> Check now</Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="alert-add-button"><Plus className="h-4 w-4 mr-2" /> New alert</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Create alert</DialogTitle></DialogHeader>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Label>Symbol</Label>
                  <Select value={symbol} onValueChange={setSymbol}>
                    <SelectTrigger className="mt-1" data-testid="alert-symbol-select"><SelectValue /></SelectTrigger>
                    <SelectContent className="max-h-64">
                      {SYMBOLS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Condition</Label>
                  <Select value={condition} onValueChange={setCondition}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="above">Price is above</SelectItem>
                      <SelectItem value="below">Price is below</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Threshold ($)</Label>
                  <Input
                    data-testid="alert-threshold-input"
                    type="number" step="any" value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                    className="mt-1"
                    placeholder="e.g. 70000"
                  />
                </div>
              </div>
              <DialogFooter><Button onClick={create} data-testid="alert-submit-button">Create alert</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {alerts === null ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : alerts.length === 0 ? (
        <EmptyState title="No alerts yet" description="Add a price alert to be notified when a coin crosses your threshold." />
      ) : (
        <div className="rounded-xl border border-border bg-card divide-y divide-border/60" data-testid="alerts-table">
          {alerts.map((a) => (
            <div key={a.id} className="px-4 py-3 flex items-center gap-4">
              <Bell className={`h-4 w-4 ${a.triggered ? "text-[hsl(var(--warning))]" : "text-muted-foreground"}`} />
              <div className="flex-1 min-w-0">
                <div className="font-medium">{a.symbol} <span className="text-xs text-muted-foreground uppercase">{a.condition}</span> <span className="font-mono tabular-nums">{formatUSD(a.threshold)}</span></div>
                <div className="text-xs text-muted-foreground">Created {shortDate(a.created_at)} {a.triggered ? `· Triggered ${shortDate(a.triggered_at)} at ${formatUSD(a.triggered_price)}` : ""}</div>
              </div>
              {a.triggered ? (
                <Badge variant="outline" className="text-[hsl(var(--warning))] border-[hsl(var(--warning))]/50">
                  <CheckCircle2 className="h-3 w-3 mr-1" /> Triggered
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[hsl(var(--success))] border-[hsl(var(--success))]/40">Active</Badge>
              )}
              <Button variant="ghost" size="icon" onClick={() => del(a.id)} aria-label="Delete alert"><Trash2 className="h-4 w-4 text-muted-foreground" /></Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
