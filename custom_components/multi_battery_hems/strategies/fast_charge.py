"""
Fast Charge strategy — charge all batteries at maximum power immediately.
/ Snel laden strategie — laad alle batterijen direct op maximaal vermogen.

Ignores grid power and price. Charges as fast as each device allows.
Useful for manually pre-charging before an expected expensive period.

Inspired by Gielz/zenSDK "Snel Laden" mode.

/ Negeert netvermogen en prijs. Laadt zo snel als elk apparaat toelaat.
Handig om handmatig voor te laden vóór een verwachte dure periode.
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class FastChargeStrategy(BaseStrategy):
    """Charge all devices at maximum power."""

    @property
    def name(self) -> str:
        return "fast_charge"

    @property
    def friendly_name(self) -> str:
        return "Snel laden"

    async def execute(self, context: StrategyContext) -> None:
        for device in context.devices:
            _LOGGER.debug("FastCharge: %s → %.0fW", device.name, device.max_charge_power_w)
            await device.set_charge(device.max_charge_power_w)
