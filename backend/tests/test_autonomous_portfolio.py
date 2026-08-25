"""
Unit tests for Autonomous AI Crypto Portfolio Manager & 5-Brain Engine.
"""
import pytest
from services.autonomous_portfolio import map_score_to_decision, run_autonomous_cycle, DEFAULT_CAPITAL, MAX_POSITION_PCT


def test_score_to_decision_mapping():
    # 80-100: BUY
    d_buy = map_score_to_decision(85)
    assert d_buy["action"] == "BUY"
    assert "🟢" in d_buy["badge"]

    # 60-79: HOLD
    d_hold = map_score_to_decision(72)
    assert d_hold["action"] == "HOLD"
    assert "🟡" in d_hold["badge"]

    # 40-59: WAIT
    d_wait = map_score_to_decision(52)
    assert d_wait["action"] == "WAIT"
    assert "🟡" in d_wait["badge"]

    # 0-39: SELL
    d_sell = map_score_to_decision(28)
    assert d_sell["action"] == "SELL"
    assert "🔴" in d_sell["badge"]


def test_circuit_breaker_override_forces_sell():
    d_cb = map_score_to_decision(85, circuit_breaker=True)
    assert d_cb["action"] == "SELL"
    assert "CIRCUIT BREAKER" in d_cb["badge"]


def test_position_sizing_limits():
    capital = 1000.0
    max_trade = capital * MAX_POSITION_PCT
    assert max_trade == 300.0  # Max 30% per setup ($300 of $1,000)
