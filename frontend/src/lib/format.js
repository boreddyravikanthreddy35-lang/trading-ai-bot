export function formatUSD(n, opts = {}) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const abs = Math.abs(n);
  const digits = opts.digits ?? (abs >= 1000 ? 2 : abs >= 1 ? 2 : 6);
  return Number(n).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatNumber(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatCompact(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(n);
}

export function formatPercent(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${Number(n).toFixed(digits)}%`;
}

export function clsxColor(n) {
  if (n === null || n === undefined || isNaN(n)) return "text-muted-foreground";
  if (n > 0) return "text-[hsl(var(--up))]";
  if (n < 0) return "text-[hsl(var(--down))]";
  return "text-muted-foreground";
}

export function symbolToPair(sym) {
  if (!sym) return "";
  return sym.replace("USDT", "/USDT");
}

export function shortDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}
