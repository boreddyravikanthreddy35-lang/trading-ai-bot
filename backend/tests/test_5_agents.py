"""
Unit tests for 5-Agent Trade Intelligence Architecture & Risk Circuit Breaker.
"""
import pytest
from services.trade_intelligence import (
    evaluate_five_agents,
    evaluate_risk_execution_check,
    build_full_trade_intelligence,
)


def test_five_agents_structure():
    indicators = {"price": 100000.0, "sma20": 98000.0, "rsi": 62.0, "pct_change_24h": 2.5}
    coin_meta = {"total_volume": 600000000.0, "price_change_percentage_24h": 2.5}
    signal_dict = {
        "action": "BUY",
        "entry_price": 100000.0,
        "stop_loss": 98000.0,
        "take_profit": 105000.0,
        "risk_level": "low",
    }

    agents = evaluate_five_agents(indicators, coin_meta, signal_dict)

    # Check that all 5 agents exist
    assert "trend" in agents
    assert "liquidity" in agents
    assert "volume" in agents
    assert "sentiment" in agents
    assert "risk" in agents

    # Check scores are between 0 and 100
    for key, agent in agents.items():
        assert 0 <= agent["score"] <= 100
        assert "question" in agent
        assert "rationale" in agent


def test_circuit_breaker_forces_no_trade():
    """Verify that even with 85/100 Trend and 85/100 Volume, a low Risk score forces NO TRADE."""
    indicators = {"price": 100000.0, "sma20": 98000.0, "rsi": 60.0, "pct_change_24h": 2.5}
    coin_meta = {"total_volume": 600000000.0}
    
    # High risk profile + poor R:R ratio (SL close to TP)
    signal_dict = {
        "action": "BUY",
        "entry_price": 100000.0,
        "stop_loss": 99500.0,  # 0.5% risk
        "take_profit": 100500.0, # 0.5% reward -> R:R 1.0 (insufficient)
        "risk_level": "high",
    }

    intel = build_full_trade_intelligence(signal_dict, indicators, coin_meta)
    decision = intel["decision_engine"]

    assert decision["verdict"] == "NO TRADE"
    assert decision["circuit_breaker_tripped"] is True
    assert "RISK CIRCUIT BREAKER" in decision["reason"]


def test_trade_approved_when_all_agents_strong():
    indicators = {"price": 100000.0, "sma20": 95000.0, "rsi": 62.0, "pct_change_24h": 3.2}
    coin_meta = {"total_volume": 800000000.0, "price_change_percentage_24h": 3.2}
    signal_dict = {
        "action": "BUY",
        "entry_price": 100000.0,
        "stop_loss": 98000.0,   # 2% risk
        "take_profit": 105000.0,  # 5% reward -> R:R 2.5
        "risk_level": "low",
    }

    intel = build_full_trade_intelligence(signal_dict, indicators, coin_meta)
    decision = intel["decision_engine"]

    assert decision["verdict"] == "TRADE"
    assert decision["circuit_breaker_tripped"] is False
    assert decision["trade_score"] >= 75


def test_pre_execution_risk_check():
    signal_dict = {
        "entry_price": 100000.0,
        "stop_loss": 98000.0,
        "take_profit": 105000.0,
        "risk_level": "medium",
    }

    risk_check = evaluate_risk_execution_check(signal_dict, account_balance=10000.0)

    assert risk_check["status"] == "APPROVED"
    assert risk_check["checks"]["stop_loss_available"] is True
    assert risk_check["checks"]["take_profit_available"] is True
    assert risk_check["checks"]["enough_balance_ok"] is True
