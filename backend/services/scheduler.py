"""Background scheduler for auto-trading bots and alert checks.

Uses APScheduler AsyncIOScheduler.
Each bot has an interval_minutes; a job is registered per bot when the app starts.
On create/pause/delete, we sync the scheduler.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services import market_data as md
from services.notifications import make_notification
from services.bot_runner import run_bot_once

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None
_db = None


def _job_id(bot_id: str) -> str:
    return f"bot-{bot_id}"


async def _bot_job(bot_id: str):
    if _db is None:
        return
    bot = await _db.bots.find_one({"id": bot_id, "active": True}, {"_id": 0})
    if not bot:
        # Bot no longer active — remove job
        try:
            _scheduler.remove_job(_job_id(bot_id))
        except Exception:
            pass
        return
    try:
        await run_bot_once(_db, bot)
    except Exception as e:
        logger.exception("Bot %s run failed: %s", bot_id, e)


def schedule_bot(bot: Dict[str, Any]):
    """Register (or re-register) a scheduled job for a bot."""
    if _scheduler is None:
        return
    job_id = _job_id(bot["id"])
    interval_min = max(1, int(bot.get("interval_minutes", 15)))
    trigger = IntervalTrigger(minutes=interval_min)
    try:
        _scheduler.add_job(
            _bot_job, trigger, id=job_id, args=[bot["id"]],
            replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=datetime.now(tz=timezone.utc),
        )
    except Exception as e:
        logger.exception("Failed to schedule bot %s: %s", bot["id"], e)


def unschedule_bot(bot_id: str):
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(_job_id(bot_id))
    except Exception:
        pass


async def _alerts_job():
    """Check all active alerts across all users; fire notifications when triggered."""
    if _db is None:
        return
    active = await _db.alerts.find({"triggered": False}, {"_id": 0}).to_list(2000)
    if not active:
        return

    # Group by symbol so we hit ticker once per symbol
    symbols = sorted({a["symbol"] for a in active})
    prices: Dict[str, float] = {}
    try:
        tickers, _src = await md.ticker_24hr(symbols)
        for t in tickers:
            prices[t["symbol"]] = float(t["lastPrice"])
    except Exception:
        # Fallback per-symbol via klines
        for s in symbols:
            try:
                df, _ = await md.get_klines(s, "1m", 3)
                if not df.empty:
                    prices[s] = float(df.iloc[-1]["close"])
            except Exception:
                continue

    now = datetime.now(tz=timezone.utc).isoformat()
    for a in active:
        p = prices.get(a["symbol"])
        if p is None:
            continue
        hit = (a["condition"] == "above" and p >= a["threshold"]) or \
              (a["condition"] == "below" and p <= a["threshold"])
        if not hit:
            continue
        await _db.alerts.update_one(
            {"id": a["id"]},
            {"$set": {"triggered": True, "triggered_at": now, "triggered_price": p}},
        )
        await _db.notifications.insert_one(dict(make_notification(
            user_id=a["user_id"],
            kind="alert",
            title=f"{a['symbol']} {a['condition']} ${a['threshold']}",
            body=f"Price reached ${p:,.4f}".rstrip("0").rstrip("."),
            payload={"alert_id": a["id"], "symbol": a["symbol"], "price": p},
        )))


async def _auto_ai_trader_job():
    """Background continuous AI trading job running automatically every 60s."""
    if _db is None:
        return
    try:
        from services.auto_ai_trader import scan_coins, get_user_coins, get_ai_enabled
        # Scan active user (prevent duplicate concurrent user scans)
        for user_id in ["aabf552e-7359-40b0-95ce-2d6e046022f4", "default_user"]:
            if get_ai_enabled(user_id):
                coins = get_user_coins(user_id)
                if coins:
                    try:
                        await scan_coins(_db, user_id, coins)
                    except Exception as e:
                        logger.warning(f"Background AI scan error for {user_id}: {e}")
                break
    except Exception as e:
        logger.exception("Auto AI Trader background job error: %s", e)


async def start(db):
    """Start the scheduler and schedule all currently-active bots + alerts poller."""
    global _scheduler, _db
    _db = db
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.start()

    # Global alerts poller — every 60s
    _scheduler.add_job(_alerts_job, IntervalTrigger(seconds=60), id="alerts-check", replace_existing=True, max_instances=1, coalesce=True)

    # Auto AI Trader continuous background job — every 60s
    _scheduler.add_job(_auto_ai_trader_job, IntervalTrigger(seconds=60), id="auto-ai-trader-poll", replace_existing=True, max_instances=1, coalesce=True)

    # Schedule active bots
    active_bots = await db.bots.find({"active": True}, {"_id": 0}).to_list(500)
    for bot in active_bots:
        schedule_bot(bot)
    logger.info("Scheduler started; %d active bots + alerts + continuous Auto AI Trader poller", len(active_bots))


def shutdown():
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        pass
    _scheduler = None
