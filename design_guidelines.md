{
  "brand": {
    "name": "(working) SignalForge",
    "attributes": [
      "authoritative",
      "quant-serious",
      "calm under volatility",
      "AI-analyst-first",
      "high-signal / low-noise",
      "trustworthy + testable"
    ],
    "north_star": "Make the AI Signal card feel like a professional research note: decisive headline, calibrated confidence, explicit risk, and transparent evidence."
  },

  "visual_personality": {
    "style_fusion": [
      "TradingView density + chart affordances",
      "Coinbase Advanced panel separation",
      "Robinhood simplicity for CTAs",
      "Subtle glassmorphism only on secondary surfaces (not text-heavy areas)",
      "Bento-grid dashboards with strong typographic hierarchy"
    ],
    "dark_mode_default": true,
    "gradient_policy": {
      "allowed": "Only as large background accents (hero/section), max 20% viewport, never on text-heavy surfaces.",
      "recommended": "Use near-black solids for most surfaces; add a mild teal→slate or cyan→graphite glow behind hero header only.",
      "prohibited": "No saturated purple/pink gradients; no gradients on small UI elements (<100px)."
    }
  },

  "typography": {
    "google_fonts_to_add": [
      {
        "family": "Space Grotesk",
        "weights": ["400", "500", "600", "700"],
        "usage": "Headings, navigation, key labels"
      },
      {
        "family": "IBM Plex Sans",
        "weights": ["400", "500", "600"],
        "usage": "Body, forms, tables"
      },
      {
        "family": "IBM Plex Mono",
        "weights": ["400", "500"],
        "usage": "Prices, PnL, timestamps, OHLC tooltips"
      }
    ],
    "font_pairing": {
      "display": "Space Grotesk",
      "body": "IBM Plex Sans",
      "mono": "IBM Plex Mono"
    },
    "text_size_hierarchy": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs"
    },
    "numeric_formatting": {
      "rule": "All price/PnL/percent values use tabular numerals + mono font.",
      "tailwind": "font-mono tabular-nums"
    }
  },

  "color_system": {
    "notes": "Dark mode is default. Palette avoids purple. Accents are ocean-teal + ice-cyan with restrained semantic reds/greens.",
    "tokens_css_custom_properties": {
      "base": {
        "--background": "220 18% 6%",
        "--foreground": "210 20% 96%",

        "--card": "220 18% 8%",
        "--card-foreground": "210 20% 96%",

        "--popover": "220 18% 8%",
        "--popover-foreground": "210 20% 96%",

        "--muted": "220 14% 14%",
        "--muted-foreground": "215 14% 70%",

        "--border": "220 14% 18%",
        "--input": "220 14% 18%",
        "--ring": "188 92% 45%",

        "--primary": "188 92% 45%",
        "--primary-foreground": "220 18% 8%",

        "--secondary": "220 14% 14%",
        "--secondary-foreground": "210 20% 96%",

        "--accent": "200 92% 55%",
        "--accent-foreground": "220 18% 8%",

        "--destructive": "0 72% 52%",
        "--destructive-foreground": "210 20% 96%",

        "--radius": "0.75rem"
      },
      "semantic": {
        "--success": "152 62% 45%",
        "--success-foreground": "210 20% 96%",
        "--warning": "38 92% 55%",
        "--warning-foreground": "220 18% 8%",
        "--danger": "0 72% 52%",
        "--danger-foreground": "210 20% 96%",

        "--up": "152 62% 45%",
        "--down": "0 72% 52%",
        "--flat": "215 14% 70%"
      },
      "chart": {
        "--chart-grid": "220 14% 16%",
        "--chart-axis": "215 14% 70%",
        "--chart-candle-up": "152 62% 45%",
        "--chart-candle-down": "0 72% 52%",
        "--chart-volume": "200 92% 55%"
      },
      "effects": {
        "--shadow-elev-1": "0 1px 0 hsl(220 14% 18% / 0.6), 0 10px 30px hsl(220 18% 2% / 0.35)",
        "--shadow-elev-2": "0 1px 0 hsl(220 14% 18% / 0.7), 0 18px 50px hsl(220 18% 2% / 0.45)",
        "--glass-bg": "hsl(220 18% 10% / 0.55)",
        "--glass-border": "hsl(210 20% 96% / 0.08)"
      }
    },
    "tailwind_usage_examples": {
      "app_shell": "bg-background text-foreground",
      "panel": "bg-card border border-border shadow-[var(--shadow-elev-1)]",
      "glass_panel": "bg-[var(--glass-bg)] backdrop-blur-md border border-[var(--glass-border)]",
      "primary_cta": "bg-primary text-primary-foreground hover:brightness-110",
      "focus_ring": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    },
    "allowed_gradients": {
      "hero_background_only": "radial-gradient(900px circle at 20% 10%, hsl(188 92% 45% / 0.18), transparent 55%), radial-gradient(700px circle at 80% 0%, hsl(200 92% 55% / 0.12), transparent 60%)"
    },
    "texture": {
      "noise_overlay_css": "background-image: url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22120%22%3E%3Cfilter id=%22n%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%222%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22120%22 height=%22120%22 filter=%22url(%23n)%22 opacity=%220.08%22/%3E%3C/svg%3E');"
    }
  },

  "layout_and_grid": {
    "app_shell": {
      "pattern": "Left rail (collapsible) + top bar + content canvas",
      "max_width": "No hard max-width on dashboards; use responsive container paddings instead.",
      "container_padding": "px-4 sm:px-6 lg:px-8",
      "content_gaps": "gap-4 md:gap-6",
      "bento_grid": "grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6"
    },
    "page_templates": {
      "landing": "Z-pattern hero + proof strip + feature bento + testimonials + CTA",
      "dashboard": "Bento: (12 cols) left 8 cols market table + right 4 cols signal generator + movers; below: charts + watchlist",
      "coin": "Chart (8 cols) + stats/signal sidebar (4 cols); below: recent signals + alerts",
      "backtest": "Form header + results bento + equity curve + trades table",
      "paper_trading": "Portfolio summary + holdings table + order ticket side panel",
      "auth": "Split layout: left brand/proof, right form card"
    },
    "spacing_scale_px": {
      "xs": 4,
      "sm": 8,
      "md": 12,
      "lg": 16,
      "xl": 24,
      "2xl": 32,
      "3xl": 48
    }
  },

  "components": {
    "component_path": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "drawer": "/app/frontend/src/components/ui/drawer.jsx",
      "sheet": "/app/frontend/src/components/ui/sheet.jsx",
      "tooltip": "/app/frontend/src/components/ui/tooltip.jsx",
      "progress": "/app/frontend/src/components/ui/progress.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "switch": "/app/frontend/src/components/ui/switch.jsx",
      "calendar": "/app/frontend/src/components/ui/calendar.jsx",
      "sonner_toast": "/app/frontend/src/components/ui/sonner.jsx",
      "navigation_menu": "/app/frontend/src/components/ui/navigation-menu.jsx",
      "dropdown_menu": "/app/frontend/src/components/ui/dropdown-menu.jsx",
      "scroll_area": "/app/frontend/src/components/ui/scroll-area.jsx",
      "resizable": "/app/frontend/src/components/ui/resizable.jsx"
    },

    "navigation": {
      "left_rail": {
        "use": ["Sheet", "NavigationMenu", "Button", "Tooltip"],
        "behavior": "Desktop: persistent rail (64px collapsed / 240px expanded). Mobile: Sheet slide-over.",
        "active_state": "Left border accent + subtle background: bg-muted/40 + border-l-2 border-primary",
        "data_testids": {
          "nav-dashboard": "nav-dashboard-link",
          "nav-signals": "nav-signals-link",
          "nav-backtest": "nav-backtest-link",
          "nav-paper": "nav-paper-trading-link",
          "nav-watchlists": "nav-watchlists-link",
          "nav-alerts": "nav-alerts-link",
          "nav-settings": "nav-settings-link"
        }
      },
      "top_bar": {
        "elements": [
          "Global search (Command component)",
          "Live connection indicator",
          "Theme toggle (Switch)",
          "User menu (DropdownMenu)"
        ],
        "micro_interactions": "Search opens with Cmd+K; top bar shadow increases on scroll (no transition:all)."
      }
    },

    "signal_card": {
      "purpose": "Hero component. Must be scannable in 3 seconds.",
      "structure": [
        "Header: coin + timeframe + model badge (Claude/Gemini/Both)",
        "Primary action badge: BUY/SELL/HOLD (large)",
        "Confidence meter: Progress + label (e.g., 0–100) with bucket text",
        "Risk pill: Low/Moderate/High",
        "Key levels: Entry / Stop / Take Profit (3-column)",
        "Evidence chips: Trend, Volatility, Volume, Momentum",
        "Reasoning preview (3–5 lines) + 'View full analysis'",
        "CTA row: Generate / Compare models / Paper trade"
      ],
      "visual_rules": {
        "badge_size": "BUY/SELL/HOLD uses uppercase tracking-wide text-sm inside a large pill; also show icon (lucide: TrendingUp/TrendingDown/Minus)",
        "confidence": "Use Progress with color mapping: <45 muted, 45–70 warning, >70 success. Always show text label to avoid color-only meaning.",
        "risk": "Badge variant with semantic background; keep it adjacent to CTA.",
        "levels": "Use mono font for numbers; show small helper labels; include copy-to-clipboard icon button.",
        "loading": "When generating (5–15s): show skeleton + animated 'analyzing' dots + disable CTA with spinner."
      },
      "tailwind_skeleton": {
        "card": "rounded-xl border border-border bg-card shadow-[var(--shadow-elev-1)]",
        "header": "flex items-start justify-between gap-3",
        "action_badge": "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold tracking-wide",
        "confidence_row": "mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3",
        "levels_grid": "mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3",
        "reasoning": "mt-4 text-sm text-muted-foreground leading-relaxed"
      },
      "data_testids": {
        "generate_button": "signal-generate-button",
        "model_select": "signal-model-select",
        "timeframe_select": "signal-timeframe-select",
        "action_badge": "signal-action-badge",
        "confidence_meter": "signal-confidence-meter",
        "risk_pill": "signal-risk-pill",
        "entry_value": "signal-entry-value",
        "stop_value": "signal-stop-loss-value",
        "take_profit_value": "signal-take-profit-value",
        "view_details": "signal-view-details-button",
        "compare_models": "signal-compare-models-button"
      }
    },

    "model_comparison": {
      "layout": "Two cards side-by-side on desktop; Tabs on mobile.",
      "use": ["Tabs", "Card", "Separator"],
      "diff_highlighting": "Highlight disagreements: outline ring-warning/40 + small 'Disagree' badge.",
      "data_testids": {
        "comparison_tabs": "model-comparison-tabs",
        "claude_panel": "model-comparison-claude-panel",
        "gemini_panel": "model-comparison-gemini-panel"
      }
    },

    "market_table": {
      "use": ["Table", "ScrollArea", "Skeleton", "Badge", "Tooltip"],
      "columns": ["Rank", "Coin", "Price", "24h%", "7d sparkline", "Volume"],
      "row_behavior": "Row hover: bg-muted/30; click navigates to /coin/:symbol.",
      "sparklines": "Use Recharts LineChart with stroke based on 7d change; keep minimal axes.",
      "data_testids": {
        "market-table": "market-table",
        "market-row": "market-table-row"
      }
    },

    "charts": {
      "library": {
        "recommended": "lightweight-charts for candlesticks (more trader-authentic). Recharts remains for sparklines + equity curve.",
        "install": "npm i lightweight-charts",
        "notes": "If staying with Recharts only, use ComposedChart with custom tooltip and OHLC mapping; but candlesticks are better with lightweight-charts."
      },
      "chart_container": {
        "style": "Card with tight header controls (timeframe, indicators, compare).",
        "header_controls": "Select + ToggleGroup for indicators (SMA/EMA/RSI/MACD).",
        "tooltip": "Use mono font; show OHLC + volume + indicator values.",
        "empty_state": "Show centered message + 'Add to watchlist' CTA."
      },
      "data_testids": {
        "coin-chart": "coin-price-chart",
        "timeframe": "coin-chart-timeframe-select",
        "indicator_toggle": "coin-chart-indicator-toggle"
      }
    },

    "backtest_results": {
      "use": ["Card", "Tabs", "Table", "Badge", "Skeleton"],
      "metrics_grid": "grid grid-cols-2 lg:grid-cols-4 gap-3",
      "equity_curve": "Recharts AreaChart with subtle fill (solid color with low opacity; no gradients beyond 20% viewport).",
      "trades_table": "Sticky header + ScrollArea; show entry/exit, size, pnl, duration.",
      "data_testids": {
        "backtest-run": "backtest-run-button",
        "backtest-strategy": "backtest-strategy-select",
        "backtest-results": "backtest-results-panel",
        "backtest-trades-table": "backtest-trades-table"
      }
    },

    "paper_trading": {
      "portfolio_summary": "Large equity number (mono) + daily PnL chip + drawdown chip.",
      "order_ticket": {
        "use": ["Card", "Tabs", "Input", "Select", "Button"],
        "layout": "Buy/Sell tabs; quantity input; estimated cost; submit.",
        "micro_interactions": "On submit: button press scale (0.98) + toast confirmation; optimistic UI for pending fill.",
        "data_testids": {
          "order-side-tabs": "order-ticket-side-tabs",
          "order-quantity-input": "order-ticket-quantity-input",
          "order-submit": "order-ticket-submit-button"
        }
      },
      "holdings_table": {
        "use": ["Table", "Badge"],
        "data_testids": {
          "holdings-table": "paper-holdings-table",
          "trade-history-table": "paper-trade-history-table"
        }
      }
    },

    "watchlists_and_alerts": {
      "watchlist_cards": "Card list with coin rows; add coin via Dialog + Command search.",
      "alerts": {
        "use": ["Dialog", "Input", "Select", "Switch", "Badge"],
        "states": "Active vs Triggered; triggered rows get subtle warning outline.",
        "data_testids": {
          "create-watchlist": "watchlist-create-button",
          "add-alert": "alert-add-button",
          "alert-threshold": "alert-threshold-input",
          "alerts-table": "alerts-table"
        }
      }
    },

    "auth": {
      "layout": "Split screen. Left: brand + proof + security note. Right: form card.",
      "google_oauth_button": "Use Button variant=secondary with Google icon; keep it full width.",
      "data_testids": {
        "login-email": "login-email-input",
        "login-password": "login-password-input",
        "login-submit": "login-submit-button",
        "google-auth": "google-oauth-button",
        "signup-submit": "signup-submit-button"
      }
    }
  },

  "motion_and_micro_interactions": {
    "principles": [
      "Prefer short, purposeful motion (120–220ms) with ease-out.",
      "No universal transition:all. Only transition color/opacity/shadow where needed.",
      "Use motion to communicate state: loading, success, error, live updates."
    ],
    "recommended_library": {
      "name": "framer-motion",
      "install": "npm i framer-motion",
      "usage": "Animate panel entrance, signal generation state, and list reordering (watchlists)."
    },
    "patterns": {
      "live_ticker": "Price cells flash background for 250ms on update: up uses success/10, down uses danger/10.",
      "signal_generation": "Card header shows animated shimmer skeleton; once complete, action badge pops in with scale 0.98→1 and opacity 0→1.",
      "order_fill": "Pending state chip pulses (opacity) until filled; toast on fill."
    }
  },

  "states": {
    "loading": {
      "rule": "Every data-heavy panel must have Skeleton state matching final layout.",
      "components": ["Skeleton", "Progress"],
      "copy": "Use calm language: 'Fetching market data…', 'Running backtest…', 'Generating signal…'"
    },
    "empty": {
      "rule": "Empty states must include a next action CTA.",
      "examples": {
        "signals": "No signals yet → 'Generate your first signal'",
        "watchlist": "No watchlists → 'Create watchlist'",
        "alerts": "No alerts → 'Add price alert'"
      }
    },
    "error": {
      "rule": "Show Alert component with retry button and a short technical hint.",
      "use": ["Alert", "Button"],
      "data_testids": {
        "error-banner": "error-banner",
        "retry": "retry-button"
      }
    }
  },

  "accessibility": {
    "wcag_target": "AA",
    "rules": [
      "Never rely on color alone for BUY/SELL/HOLD; always include text + icon.",
      "Focus states must be visible on all interactive elements (ring token).",
      "Use sufficient contrast for muted text; avoid ultra-low contrast grays.",
      "Respect prefers-reduced-motion: disable shimmer and large entrance animations."
    ],
    "keyboard": {
      "command_palette": "Cmd+K opens global search; Esc closes dialogs/sheets.",
      "tables": "Rows must be focusable when clickable; provide aria-label for row action."
    }
  },

  "iconography": {
    "library": "lucide-react",
    "rules": [
      "Use 18–20px icons in dense UI; 24px in marketing hero.",
      "Use consistent stroke width (default).",
      "No emoji icons."
    ],
    "suggested_icons": {
      "dashboard": "LayoutDashboard",
      "signals": "Sparkles",
      "backtest": "FlaskConical",
      "paper_trading": "Wallet",
      "watchlists": "Star",
      "alerts": "Bell",
      "settings": "Settings",
      "buy": "TrendingUp",
      "sell": "TrendingDown",
      "hold": "Minus"
    }
  },

  "image_urls": {
    "landing_hero_background": [
      {
        "url": "https://images.pexels.com/photos/32299941/pexels-photo-32299941.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "description": "Use as a subtle, blurred hero backdrop inside a masked container (opacity 0.18) behind the headline. Do not use as a full-page background.",
        "category": "marketing/hero"
      }
    ],
    "feature_section_visual": [
      {
        "url": "https://images.pexels.com/photos/38343510/pexels-photo-38343510.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "description": "Use as a small feature illustration card (aspect-video) for 'AI Signals' section; apply grayscale + low opacity overlay.",
        "category": "marketing/features"
      }
    ]
  },

  "implementation_notes_for_js": {
    "theme_toggle": {
      "rule": "Use 'dark' class on <html> or <body>. Persist in localStorage.",
      "snippet": "// setTheme(next) => document.documentElement.classList.toggle('dark', next==='dark'); localStorage.setItem('theme', next);"
    },
    "data_testid_rule": "All buttons/inputs/links/menus and key info (price, pnl, confidence) must include data-testid in kebab-case.",
    "avoid": [
      "Do not keep CRA default centered App styles (remove App-header centering).",
      "Do not use transition: all.",
      "Do not use purple gradients."
    ]
  },

  "instructions_to_main_agent": [
    "Update /app/frontend/src/index.css tokens: replace :root and .dark with the provided HSL tokens; keep shadcn variable names.",
    "Remove CRA demo styles in /app/frontend/src/App.css (App-header centering).",
    "Add Google Fonts (Space Grotesk, IBM Plex Sans, IBM Plex Mono) in public/index.html or via CSS import; set font-family in body and headings utilities.",
    "Implement layout shell: left rail + top bar + content using shadcn Sheet/NavigationMenu/DropdownMenu/Command.",
    "Build the SignalCard first (hero component) with strict hierarchy + skeleton state + model comparison view.",
    "Use lightweight-charts for candlesticks on /coin/:symbol; keep Recharts for sparklines and equity curve.",
    "Ensure every interactive element and key metric has data-testid attributes as specified.",
    "Add framer-motion for subtle entrance and state transitions; respect prefers-reduced-motion.",
    "Use Sonner for toasts (order fills, signal generated, alert created)."
  ]
}

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
    - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>
