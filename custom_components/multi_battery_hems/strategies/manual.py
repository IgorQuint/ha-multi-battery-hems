"""
Manual strategy — user-defined power setpoint.
/ Handmatige strategie — door gebruiker ingesteld vermogenspunt.

The user sets a fixed power value (in watts) in the config / options flow.
  positive value → charge all batteries at that power
  negative value → discharge all batteries at that power
  zero          → standby

Power is distributed equally across all devices and clamped to device limits.

Inspired by Gielz/zenSDK "Manual" mode.

/ De gebruiker stelt een vast vermogen (in watt) in via de configuratie.
  positieve waarde → laad alle batterijen op dat vermogen
  negatieve waarde → ontlaad alle batterijen op dat vermogen
  nul              → stand-by

Vermogen wordt gelijk verdeeld over alle apparaten en begrensd tot apparaatlimieten.
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class ManualStrategy(BaseStrategy):
    """User-defined fixed power setpoint, distributed across all devices."""

    @property
    def name(self) -> str:
        return "manual"

    @property
    def friendly_name(self) -> str:
        return "Handmatig"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        total_w = context.manual_power_w
        per_device_w = total_w / len(devices)

        for device in devices:
            if per_device_w > 0:
                power_w = min(per_device_w, device.max_charge_power_w)
            elif per_device_w < 0:
                power_w = max(per_device_w, -device.max_discharge_power_w)
            else:
                await device.set_standby()
                continue

            _LOGGER.debug("Manual: %s → %.0fW", device.name, power_w)
            await device.set_charge(power_w)
