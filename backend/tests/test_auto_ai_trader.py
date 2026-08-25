"""Unit tests for Automatic AI Trader & Custom Coin Analysis.
"""
import pytest
from services.auto_ai_trader import map_score_to_action


def test_score_to_action_mapping():
    # 80-100: BUY
    a_buy = map_score_to_action(88)
    assert a_buy["action"] == "BUY"
    assert "🟢" in a_buy["badge"]

    # 60-79: HOLD
    a_hold = map_score_to_action(68)
    assert a_hold["action"] == "HOLD"
    assert "🟡" in a_hold["badge"]

    # 40-59: WAIT
    a_wait = map_score_to_action(45)
    assert a_wait["action"] == "WAIT"
    assert "🟡" in a_wait["badge"]

    # 0-39: SELL
    a_sell = map_score_to_action(25)
    assert a_sell["action"] == "SELL"
    assert "🔴" in a_sell["badge"]


def test_circuit_breaker_override():
    a_cb = map_score_to_action(95, circuit_breaker=True)
    assert a_cb["action"] == "SELL"
    assert "CIRCUIT BREAKER" in a_cb["badge"]
