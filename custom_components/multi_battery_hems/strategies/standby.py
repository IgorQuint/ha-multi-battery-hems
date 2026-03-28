"""
Standby strategy — all batteries off.
/ Standby-strategie — alle batterijen uit.
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class StandbyStrategy(BaseStrategy):
    """
    Put every device in standby.
    No charging or discharging takes place.

    / Zet elk apparaat in stand-by.
    Er wordt niet geladen of ontladen.
    """

    @property
    def name(self) -> str:
        return "standby"

    @property
    def friendly_name(self) -> str:
        return "Standby"

    async def execute(self, context: StrategyContext) -> None:
        for device in context.devices:
            _LOGGER.debug("Standby: disabling %s", device.name)
            await device.set_standby()
