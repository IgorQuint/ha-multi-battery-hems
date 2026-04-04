"""
Smart Discharge Only strategy.
/ Alleen ontladen strategie.

Like NOM but only discharges — never charges.
When household consumption draws from the grid, the battery discharges to cover it.
When there is surplus solar / grid export, the battery stays idle rather than charging.

Use case: covering household consumption without accepting grid / solar charging
(e.g. battery is being charged by a separate controller and HEMS only handles discharge).

Inspired by Gielz/zenSDK "Smart Discharge Only" mode.

/ Net als NOM maar ontlaadt alleen — laadt nooit.
Bij huishoudelijk netverbruik ontlaadt de batterij om dit te dekken.
Bij zonne-overschot / teruglevering blijft de batterij inactief.

Gebruik: huishoudelijk verbruik dekken zonder laden via net of zon
(bijv. batterij wordt door een aparte controller geladen en HEMS beheert alleen ontladen).
"""
from __future__ import annotations

import logging

from ..const import NOM_DISCHARGE_THRESHOLD_W, NOM_RAMP_FACTOR
from .base import BaseStrategy, StrategyContext
from .nom import _is_already_active

_LOGGER = logging.getLogger(__name__)


class SmartDischargeOnlyStrategy(BaseStrategy):
    """NOM-style discharging only — charging is always blocked."""

    @property
    def name(self) -> str:
        return "smart_discharge_only"

    @property
    def friendly_name(self) -> str:
        return "Alleen ontladen"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        grid_w = context.grid_power_w

        if grid_w <= NOM_DISCHARGE_THRESHOLD_W:
            # Grid balanced or exporting — do nothing, never charge
            for device in devices:
                await device.set_standby()
            return

        # Grid is consuming → discharge
        for device in devices:
            last_state = context.device_states.get(device.device_id)
            already_discharging = _is_already_active(last_state, 1)  # 1 = want to discharge
            ramp = 1.0 if already_discharging else NOM_RAMP_FACTOR

            target = (grid_w / len(devices)) * ramp - context.discharge_margin_w
            power_w = max(min(target, device.max_discharge_power_w), 0)

            _LOGGER.debug("SmartDischargeOnly: %s → -%.0fW", device.name, power_w)
            await device.set_charge(-power_w)
