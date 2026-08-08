import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, X, MessageCircle, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger, SheetDescription
} from "@/components/ui/sheet";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";

const DEFAULT_QUESTIONS = [
  "Why did you choose this action?",
  "What if the market drops 5% — what would you do?",
  "How should I size the trade?",
  "What's the biggest risk here?",
];

export function ChatDrawer({ signalId, defaultOpen = false, triggerLabel = "Chat with AI", triggerVariant = "outline" }) {
  const [open, setOpen] = useState(defaultOpen);
  const [model, setModel] = useState("claude");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/chat/${signalId}`);
      setMessages(data.conversation?.messages || []);
    } catch (e) {
      /* silent */
    }
  };

  useEffect(() => {
    if (open && signalId) load();
    // eslint-disable-next-line
  }, [open, signalId]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, busy]);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setBusy(true);
    // Optimistic user echo
    setMessages((m) => [...m, { role: "user", content, created_at: new Date().toISOString() }]);
    setInput("");
    try {
      const { data } = await api.post(`/chat/${signalId}/message`, { signal_id: signalId, model, message: content });
      setMessages(data.messages || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Chat failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant={triggerVariant} size="sm" data-testid="chat-open-button">
          <MessageCircle className="h-4 w-4 mr-2" /> {triggerLabel}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-md flex flex-col p-0" data-testid="chat-drawer">
        <SheetHeader className="px-5 py-4 border-b border-border">
          <SheetTitle className="flex items-center gap-2 font-display">
            <Sparkles className="h-4 w-4 text-primary" /> AI Analyst
          </SheetTitle>
          <SheetDescription className="text-xs">
            Ask follow-up questions grounded in this signal's data.
          </SheetDescription>
          <div className="mt-2 flex items-center gap-2">
            <div className="text-xs text-muted-foreground">Model:</div>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="h-8 w-40" data-testid="chat-model-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="claude">Claude Sonnet 4.5</SelectItem>
                <SelectItem value="gemini">Gemini 2.5 Pro</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </SheetHeader>

        {/* Message list */}
        <div ref={listRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4" data-testid="chat-messages">
          {messages.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              <div>Start a conversation about this signal. Try:</div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {DEFAULT_QUESTIONS.map((q) => (
                  <button key={q} onClick={() => send(q)} className="px-2.5 py-1 rounded-full text-xs border border-border hover:border-primary/40 hover:text-foreground text-muted-foreground text-left">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18 }}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-muted rounded-bl-sm"
                  }`}>
                    {m.role === "assistant" && m.model ? (
                      <div className="text-[10px] uppercase tracking-wider opacity-70 mb-1">{m.model === "gemini" ? "Gemini" : "Claude"}</div>
                    ) : null}
                    <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          {busy ? (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl rounded-bl-sm px-3.5 py-2.5 flex items-center gap-2 text-sm text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse [animation-delay:300ms]" />
                <span className="ml-1">Analyst is thinking…</span>
              </div>
            </div>
          ) : null}
        </div>

        {/* Composer */}
        <div className="border-t border-border p-3 flex items-end gap-2">
          <Textarea
            data-testid="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask about entry timing, risk, alternatives…"
            className="min-h-[44px] max-h-40 resize-none"
            rows={1}
          />
          <Button size="icon" onClick={() => send()} disabled={busy || !input.trim()} data-testid="chat-send-button">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
