"""
FastAPI server for the AI Crypto Trading platform.
Wires all sub-routers under the /api prefix.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ── MongoDB ────────────────────────────────────────────────────────────────
mongo_url = os.environ["MONGO_URL"]
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
    client.close()
