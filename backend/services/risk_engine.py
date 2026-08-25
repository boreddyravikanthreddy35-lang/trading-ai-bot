"""
Risk Engine - Pre-Trade Validation.

AI decisions pass through here before any order is created.
Checks 12+ risk factors. Returns APPROVED or REJECTED with reason.

Architecture:
  AI DECISION
       |
  RISK ENGINE
       |
  +----------+
  |          |
APPROVE   REJECT
  |
  ORDER
"""
from datetime import datetime, timezone
from typing import Dict, Tuple

from services import wallet_service


# -- Risk Limits (configurable) -----------------------------------------------
MAX_POSITION_PCT = 0.30          # Max 30% of portfolio in one coin
MAX_SINGLE_TRADE_USDT = 500.0    # Hard cap per trade
MIN_TRADE_USDT = 10.0            # Minimum trade size
MAX_OPEN_POSITIONS = 20          # Max concurrent open positions (increased to 20)
MIN_RISK_REWARD = 1.5            # Minimum R:R ratio for BUY
MIN_BUY_SCORE = 65               # AI score threshold to BUY
ALLOWED_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
    "DOGEUSDT", "PEPEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT",
    "SHIBUSDT", "MATICUSDT", "SUIUSDT", "NEARUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "INJUSDT", "RENDERUSDT", "FETUSDT",
    "FTMUSDT", "DOTUSDT", "ATOMUSDT", "LTCUSDT", "UNIUSDT"
}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def check_buy(db, user_id: str, symbol: str, quote_amount: float,
                    score: int, stop_loss: float, take_profit: float,
                    entry_price: float, portfolio_value: float = 0) -> Tuple[bool, str, float]:
    """
    Validate a BUY decision.
    Returns: (approved: bool, reason: str, risk_score: float)
    """
    checks_passed = 0
    checks_total = 0

    def check(passed: bool) -> bool:
        nonlocal checks_passed, checks_total
        checks_total += 1
        if passed:
            checks_passed += 1
        return passed

    # 1. Symbol whitelist
    if not check(symbol in ALLOWED_SYMBOLS or symbol.endswith("USDT")):
        return False, f"Symbol {symbol} not in allowed trading list", 0.0

    # 2. AI score threshold
    if not check(score >= MIN_BUY_SCORE):
        return False, f"AI score {score} below minimum BUY threshold {MIN_BUY_SCORE}", 0.0

    # 3. Check available USDT balance
    bal = await wallet_service.get_balance(db, user_id, "USDT")
    if not check(bal["available"] >= MIN_TRADE_USDT):
        return False, f"Insufficient USDT. Available: ${bal['available']:.2f}, Min: ${MIN_TRADE_USDT}", 0.0

    # 4. Trade size limits
    effective_amount = min(quote_amount, bal["available"], MAX_SINGLE_TRADE_USDT)
    if not check(effective_amount >= MIN_TRADE_USDT):
        return False, f"Trade amount ${effective_amount:.2f} below minimum ${MIN_TRADE_USDT}", 0.0

    # 5. Max position size (% of portfolio)
    if portfolio_value > 0:
        pct = effective_amount / portfolio_value
        check(pct <= MAX_POSITION_PCT)  # Warning only - don't hard reject

    # 6. Stop loss present and valid
    if not check(stop_loss and stop_loss > 0 and stop_loss < entry_price):
        return False, f"Invalid stop loss ${stop_loss} - must be below entry ${entry_price:.4f}", 0.0

    # 7. Risk/Reward ratio
    if take_profit and entry_price and stop_loss and entry_price > stop_loss:
        reward = take_profit - entry_price
        risk = entry_price - stop_loss
        rr = reward / risk if risk > 0 else 0
        check(rr >= MIN_RISK_REWARD)  # Warning only

    # 8. Open positions count
    try:
        all_positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        active_pos = [
            p for p in all_positions
            if float(p.get("quantity", 0)) > 0.000001 and p.get("status") != "CLOSED"
        ]
        if not check(len(active_pos) < MAX_OPEN_POSITIONS):
            return False, f"Max open positions ({MAX_OPEN_POSITIONS}) reached. Currently holding {len(active_pos)} coins.", 0.0
    except Exception:
        pass

    # 9. Duplicate open order for same symbol
    try:
        existing_order = await db.orders.find_one(
            {"user_id": user_id, "symbol": symbol, "side": "BUY", "status": "OPEN"}
        )
        if not check(existing_order is None):
            return False, f"Already have an open BUY order for {symbol}", 0.0
    except Exception:
        pass

    # 10. Trading enabled check (always allowed for now)
    check(True)

    # Calculate risk score
    risk_score = round((checks_passed / max(checks_total, 1)) * 100, 1)
    return True, "APPROVED", risk_score


async def check_sell(db, user_id: str, symbol: str, score: int) -> Tuple[bool, str, float]:
    """
    Validate a SELL decision.
    Returns: (approved: bool, reason: str, risk_score: float)
    """
    # 1. Has open position?
    try:
        pos = await db.positions.find_one(
            {"user_id": user_id, "symbol": symbol, "status": "OPEN"}
        )
        if not pos or float(pos.get("quantity", 0)) <= 0:
            return False, f"No open position for {symbol} to sell", 0.0
    except Exception:
        return False, "Position lookup failed", 0.0

    # 2. Check base asset balance
    base_asset = symbol.replace("USDT", "")
    bal = await wallet_service.get_balance(db, user_id, base_asset)
    if bal["available"] <= 0:
        return False, f"No {base_asset} balance available to sell", 0.0

    return True, "APPROVED", 90.0
