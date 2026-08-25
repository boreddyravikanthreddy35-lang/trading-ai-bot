"""
FastAPI server for the AI Crypto Trading platform.
Wires all sub-routers under the /api prefix.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except Exception:  # pragma: no cover - optional dependency for Firebase-only setups
    AsyncIOMotorClient = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ── Database ─────────────────────────────────────────────────────────────
if os.environ.get("USE_SUPABASE", "false").lower() == "true":
    # ── Supabase (PostgreSQL) — primary database ──────────────────────────
    from services.supabase_db import create_db as _create_supabase_db
    db = _create_supabase_db()
    client = None
    import logging as _log
    _log.getLogger(__name__).info("Database: Supabase (PostgreSQL)")

elif os.environ.get("USE_FIREBASE", "false").lower() == "true":
    # ── Firebase / Firestore ──────────────────────────────────────────────
    from services.firebase_db import create_db as _create_firebase_db
    db = _create_firebase_db()
    client = None

else:
    # ── MongoDB (legacy fallback) ─────────────────────────────────────────
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    if AsyncIOMotorClient is None:
        raise RuntimeError(
            "No database configured. Set USE_SUPABASE=true in backend/.env "
            "or install motor for MongoDB."
        )
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get("DB_NAME", "signalforge")]

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="SignalForge — AI Crypto Trading Platform", version="1.1.0")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"name": "SignalForge API", "status": "ok", "version": "1.1.0"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


# Import routers after `db` is defined (they reference `server.db` lazily)
from api.market import router as market_router  # noqa: E402
from api.ai import router as ai_router  # noqa: E402
from api.backtest import router as backtest_router  # noqa: E402
from api.paper import router as paper_router  # noqa: E402
from api.watch import router as watch_router  # noqa: E402
from api.auth_routes import router as auth_router  # noqa: E402
from api.settings import router as settings_router  # noqa: E402
from api.chat import router as chat_router  # noqa: E402
from api.notifications import router as notif_router  # noqa: E402
from api.presets import router as presets_router  # noqa: E402
from api.bots import router as bots_router  # noqa: E402
from api.payments import router as payments_router, webhook_router as stripe_webhook_router  # noqa: E402
from api.auto_trader import router as auto_trader_router  # noqa: E402
from api.continuous_trader import router as continuous_trader_router  # noqa: E402
from api.wallet import router as wallet_router  # noqa: E402
from api.orders_api import router as orders_router  # noqa: E402
from api.ai_decisions_api import router as ai_decisions_router  # noqa: E402
from api.reconciliation_api import router as reconciliation_router  # noqa: E402
from api.custody_api import router as custody_router  # noqa: E402
from api.withdrawal_api import router as withdrawal_router  # noqa: E402
from api.razorpay_api import router as payment_gateway_router  # noqa: E402

api_router.include_router(market_router)
api_router.include_router(ai_router)
api_router.include_router(backtest_router)
api_router.include_router(paper_router)
api_router.include_router(watch_router)
api_router.include_router(auth_router)
api_router.include_router(settings_router)
api_router.include_router(chat_router)
api_router.include_router(notif_router)
api_router.include_router(presets_router)
api_router.include_router(bots_router)
api_router.include_router(payments_router)
api_router.include_router(auto_trader_router)
api_router.include_router(continuous_trader_router)
api_router.include_router(wallet_router)
api_router.include_router(orders_router)
api_router.include_router(ai_decisions_router)
api_router.include_router(reconciliation_router)
api_router.include_router(custody_router)
api_router.include_router(withdrawal_router)
api_router.include_router(payment_gateway_router)
api_router.include_router(stripe_webhook_router)  # /webhook/stripe → /api/webhook/stripe

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Background scheduler (auto-trading bots + alert checks) ────────────────
from services import scheduler as sched  # noqa: E402


@app.on_event("startup")
async def start_scheduler():
    try:
        await sched.start(db)
        logger.info("Background scheduler started")
    except Exception as e:
        logger.exception("Scheduler start failed: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        sched.shutdown()
    except Exception:
        pass
    if client is not None:
        client.close()
