import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { Star, Plus, Trash2, Bell } from "lucide-react";
import { api } from "@/lib/api";
import { formatUSD, formatPercent, clsxColor, symbolToPair } from "@/lib/format";
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

const SUPPORTED_SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
];

export default function WatchlistsPage() {
  const [lists, setLists] = useState(null);
  const [error, setError] = useState(null);

  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSyms, setNewSyms] = useState(["BTCUSDT", "ETHUSDT"]);

  const load = async () => {
    setError(null);
    try {
      const { data } = await api.get("/watch/lists");
      setLists(data.watchlists || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load watchlists");
    }
  };

  useEffect(() => { load(); }, []);

  const createList = async () => {
    if (!newName.trim()) return toast.error("Name required");
    try {
      await api.post("/watch/lists", { name: newName.trim(), symbols: newSyms });
      toast.success("Watchlist created");
      setOpen(false); setNewName(""); setNewSyms(["BTCUSDT", "ETHUSDT"]);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to create"); }
  };

  const deleteList = async (id) => {
    if (!window.confirm("Delete this watchlist?")) return;
    try { await api.delete(`/watch/lists/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error("Delete failed"); }
  };

  const toggleSym = (sym) => {
    setNewSyms((cur) => (cur.includes(sym) ? cur.filter((s) => s !== sym) : [...cur, sym]));
  };

  const removeSymbol = async (list, sym) => {
    try {
      const symbols = (list.symbols || []).filter((s) => s !== sym);
      await api.patch(`/watch/lists/${list.id}`, { symbols });
      load();
    } catch (e) { toast.error("Update failed"); }
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-display font-semibold text-2xl md:text-3xl tracking-tight">Watchlists</h1>
          <p className="text-sm text-muted-foreground mt-1">Track the coins you care about with live prices.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="watchlist-create-button"><Plus className="h-4 w-4 mr-2" /> New watchlist</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create a watchlist</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Name</Label>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="My favorites" className="mt-1" data-testid="new-watchlist-name" />
              </div>
              <div>
                <Label>Symbols</Label>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {SUPPORTED_SYMBOLS.map((s) => {
                    const on = newSyms.includes(s);
                    return (
                      <button key={s} onClick={() => toggleSym(s)} className={`px-2.5 py-1 rounded-full text-xs border ${on ? "bg-primary/15 text-primary border-primary/40" : "border-border text-muted-foreground"}`}>{s}</button>
                    );
                  })}
                </div>
              </div>
            </div>
            <DialogFooter><Button onClick={createList} data-testid="new-watchlist-submit">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {lists === null ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : lists.length === 0 ? (
        <EmptyState title="No watchlists yet" description="Create your first watchlist to track live prices for your favorite coins." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="watchlists-grid">
          {lists.map((wl) => (
            <WatchlistCard key={wl.id} wl={wl} onDelete={() => deleteList(wl.id)} onRemove={(s) => removeSymbol(wl, s)} />
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistCard({ wl, onDelete, onRemove }) {
  const nav = useNavigate();
  return (
    <div className="rounded-xl border border-border bg-card" data-testid={`watchlist-${wl.id}`}>
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Star className="h-4 w-4 text-primary" />
          <div className="font-display font-semibold">{wl.name}</div>
          <Badge variant="outline" className="text-xs">{wl.symbols?.length || 0}</Badge>
        </div>
        <Button variant="ghost" size="icon" onClick={onDelete} data-testid="watchlist-delete"><Trash2 className="h-4 w-4 text-muted-foreground" /></Button>
      </div>
      {!wl.symbols?.length ? (
        <div className="p-4 text-sm text-muted-foreground">No symbols. Edit this list to add coins.</div>
      ) : (
        <div className="divide-y divide-border/60">
          {wl.symbols.map((s) => {
            const p = wl.live?.[s];
            return (
              <div key={s} className="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/30 group">
                <button onClick={() => nav(`/coin/${s}`)} className="flex-1 flex items-center gap-3 text-left">
                  <div className="font-medium">{s}</div>
                  <div className="flex-1" />
                  <div className="font-mono tabular-nums text-sm">{p ? formatUSD(p.price) : "—"}</div>
                  <div className={`text-xs font-mono ${clsxColor(p?.change_pct)}`}>{p ? formatPercent(p.change_pct) : "—"}</div>
                </button>
                <button onClick={() => onRemove(s)} className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground" aria-label={`Remove ${s}`}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
