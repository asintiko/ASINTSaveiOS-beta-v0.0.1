"""CryptoBot payment gateway integration helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp


@dataclass(frozen=True)
class CryptoInvoice:
    """Details returned by CryptoBot when an invoice is created."""

    invoice_id: str
    plan_key: str
    asset: str
    amount: float
    description: str
    payload: str
    pay_url: str


class CryptoBotGateway:
    """Lightweight API client for @CryptoBot."""

    _API_BASE = "https://pay.crypt.bot/api/"

    def __init__(self, token: Optional[str]) -> None:
        self._token = token

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    async def create_invoice(
        self,
        user_id: int,
        plan_key: str,
        asset: str,
        amount: float,
        description: str,
        payload: str,
    ) -> CryptoInvoice:
        if not self._token:
            raise RuntimeError("CryptoBot token is not configured")

        request_payload = {
            "asset": asset,
            "amount": amount,
            "description": description,
            "payload": payload,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._API_BASE}createInvoice",
                json=request_payload,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                data = await response.json()

        if not data.get("ok"):
            raise RuntimeError(f"CryptoBot error: {data}")

        result = data["result"]
        return CryptoInvoice(
            invoice_id=str(result["invoice_id"]),
            plan_key=plan_key,
            asset=asset,
            amount=amount,
            description=description,
            payload=payload,
            pay_url=result["pay_url"],
        )

    async def poll_until_paid(
        self,
        invoice_id: str,
        interval: float,
        timeout: float,
    ) -> bool:
        if not self._token:
            return False

        deadline = asyncio.get_running_loop().time() + timeout
        async with aiohttp.ClientSession() as session:
            while asyncio.get_running_loop().time() < deadline:
                status = await self._get_invoice_status(session, invoice_id)
                if status == "paid":
                    return True
                if status in {"expired", "cancelled"}:
                    return False
                await asyncio.sleep(interval)
        return False

    async def _get_invoice_status(self, session: aiohttp.ClientSession, invoice_id: str) -> Optional[str]:
        async with session.get(
            f"{self._API_BASE}getInvoices",
            params={"invoice_ids": invoice_id},
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            data = await response.json()
        if not data.get("ok"):
            return None
        items = data["result"].get("items", [])
        if not items:
            return None
        return items[0].get("status")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Crypto-Pay-API-Token": self._token or "",
        }
