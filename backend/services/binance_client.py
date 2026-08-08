"""
Binance Testnet signed REST client.
Endpoints: https://testnet.binance.vision

Usage:
    client = BinanceTestnetClient(api_key, api_secret)
    await client.ping()
    await client.account()
    await client.market_order("BTCUSDT", "BUY", quote_amount=50.0)

Note: Binance/Testnet may be geo-restricted (HTTP 451). Consumers should
catch GeoRestrictedError and fall back to paper trading.
"""
import hmac
import hashlib
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

BINANCE_TESTNET_BASE = "https://testnet.binance.vision"


class BinanceError(Exception):
    pass


class GeoRestrictedError(BinanceError):
    pass


class BinanceTestnetClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = BINANCE_TESTNET_BASE):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base = base_url.rstrip("/")

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Any:
        url = f"{self.base}{path}"
        headers = {"X-MBX-APIKEY": self.api_key} if self.api_key else {}
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params["signature"] = self._sign(params)
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                r = await client.request(method, url, params=params)
        except httpx.HTTPError as e:
            raise BinanceError(f"Network error: {e}")
        if r.status_code == 451:
            raise GeoRestrictedError("Binance testnet is geo-restricted from this environment")
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise BinanceError(f"HTTP {r.status_code}: {detail}")
        return r.json()

    # ---- Public
    async def ping(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v3/ping")

    async def server_time(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v3/time")

    async def exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        params = {"symbol": symbol} if symbol else None
        return await self._request("GET", "/api/v3/exchangeInfo", params=params)

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> Any:
        return await self._request("GET", "/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})

    # ---- Private (signed)
    async def account(self) -> Dict[str, Any]:
        """Get account balances."""
        return await self._request("GET", "/api/v3/account", signed=True)

    async def market_order(self, symbol: str, side: str, quantity: Optional[float] = None, quote_amount: Optional[float] = None) -> Dict[str, Any]:
        """Place a market order. Provide either quantity (base) or quote_amount (USDT)."""
        params: Dict[str, Any] = {"symbol": symbol, "side": side.upper(), "type": "MARKET"}
        if quantity is not None:
            params["quantity"] = f"{float(quantity):.6f}".rstrip("0").rstrip(".") or "0"
        elif quote_amount is not None:
            params["quoteOrderQty"] = f"{float(quote_amount):.2f}"
        else:
            raise BinanceError("quantity or quote_amount required")
        return await self._request("POST", "/api/v3/order", params=params, signed=True)

    async def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return await self._request("GET", "/api/v3/order", params={"symbol": symbol, "orderId": order_id}, signed=True)

    async def open_orders(self, symbol: Optional[str] = None) -> Any:
        params = {"symbol": symbol} if symbol else None
        return await self._request("GET", "/api/v3/openOrders", params=params, signed=True)

    async def my_trades(self, symbol: str, limit: int = 50) -> Any:
        return await self._request("GET", "/api/v3/myTrades", params={"symbol": symbol, "limit": limit}, signed=True)
