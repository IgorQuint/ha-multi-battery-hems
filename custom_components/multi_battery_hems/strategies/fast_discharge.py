"""
Fast Discharge strategy — discharge all batteries at maximum power immediately.
/ Snel ontladen strategie — ontlaad alle batterijen direct op maximaal vermogen.

Ignores grid power and price. Discharges as fast as each device allows.
Useful for manually emptying batteries before a cheap charging window.

Inspired by Gielz/zenSDK "Snel Ontladen" mode.

/ Negeert netvermogen en prijs. Ontlaadt zo snel als elk apparaat toelaat.
Handig om batterijen handmatig leeg te maken vóór een goedkoop laadvenster.
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class FastDischargeStrategy(BaseStrategy):
    """Discharge all devices at maximum power."""

    @property
    def name(self) -> str:
        return "fast_discharge"

    @property
    def friendly_name(self) -> str:
        return "Snel ontladen"

    async def execute(self, context: StrategyContext) -> None:
        for device in context.devices:
            _LOGGER.debug("FastDischarge: %s → -%.0fW", device.name, device.max_discharge_power_w)
            await device.set_charge(-device.max_discharge_power_w)
