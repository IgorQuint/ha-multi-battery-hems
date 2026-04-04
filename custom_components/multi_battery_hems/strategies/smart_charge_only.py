"""
Smart Charge Only strategy.
/ Alleen laden strategie.

Like NOM but only charges — never discharges.
When solar / cheap grid power is available (grid export), the battery charges.
When the grid draws power (import), the battery stays idle rather than discharging.

Use case: solar self-consumption without grid support (e.g. when battery should
only absorb solar surplus, not discharge for household consumption).

Inspired by Gielz/zenSDK "Smart Charge Only" mode.

/ Net als NOM maar laadt alleen — ontlaadt nooit.
Bij beschikbare zonne-energie / goedkope stroom (netto teruglevering) laadt de batterij.
Bij netto netverbruik blijft de batterij inactief in plaats van te ontladen.

Gebruik: eigen verbruik zonne-energie zonder netondersteuning (bijv. wanneer de batterij
alleen zonne-overschot moet opslaan, niet ontladen voor huishoudelijk verbruik).
"""
from __future__ import annotations

import logging

from ..const import NOM_CHARGE_THRESHOLD_W, NOM_RAMP_FACTOR
from .base import BaseStrategy, StrategyContext
from .nom import _is_already_active

_LOGGER = logging.getLogger(__name__)


class SmartChargeOnlyStrategy(BaseStrategy):
    """NOM-style charging only — discharging is always blocked."""

    @property
    def name(self) -> str:
        return "smart_charge_only"

    @property
    def friendly_name(self) -> str:
        return "Alleen laden"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        grid_w = context.grid_power_w

        if grid_w >= -NOM_CHARGE_THRESHOLD_W:
            # Grid is balanced or consuming — do nothing, never discharge
            for device in devices:
                await device.set_standby()
            return

        # Grid is exporting (surplus) → charge
        for device in devices:
            last_state = context.device_states.get(device.device_id)
            already_charging = _is_already_active(last_state, -1)  # -1 = want to charge
            ramp = 1.0 if already_charging else NOM_RAMP_FACTOR

            target = (abs(grid_w) / len(devices)) * ramp - context.charge_margin_w
            power_w = min(max(target, 0), device.max_charge_power_w)

            _LOGGER.debug("SmartChargeOnly: %s → %.0fW", device.name, power_w)
            await device.set_charge(power_w)
