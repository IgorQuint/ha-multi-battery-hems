"""
NOM — Nul op de Meter strategy (improved).
/ NOM — Nul-op-de-Meter strategie (verbeterd).

Methodology based on Gielz/zenSDK analysis:

1. Threshold triggers: only react when grid power exceeds a meaningful threshold.
   Prevents unnecessary relay switching for tiny imbalances.
   - Only start discharging when grid consumption > NOM_DISCHARGE_THRESHOLD_W
   - Only start charging when grid export > NOM_CHARGE_THRESHOLD_W

2. Ramp factor: when first activating charge or discharge, use 75% of target power.
   Once the device is already active in that direction, switch to 100%.
   This prevents overshoot and relay chatter.

3. Hysteresis margins: configurable charge_margin_w and discharge_margin_w
   subtract a small buffer from the target to avoid constant micro-corrections.

4. Power distribution: divide the net target evenly across all devices,
   then clamp each device to its individual max limits.

/ Methodiek gebaseerd op Gielz/zenSDK analyse:

1. Drempelwaarden: alleen reageren wanneer netvermogen een zinvolle drempel overschrijdt.
   Voorkomt onnodige relaisschakelingen voor kleine onevenwichtigheden.
   - Pas ontladen als netverbruik > NOM_DISCHARGE_THRESHOLD_W
   - Pas laden als netto teruglevering > NOM_CHARGE_THRESHOLD_W

2. Ramp-factor: bij eerste activering laad/ontlaad 75% van doelvermogen gebruiken.
   Zodra het apparaat al actief is in die richting, overschakelen naar 100%.
   Voorkomt overschieten en relay-gezwabber.

3. Hysteresismarges: configureerbare charge_margin_w en discharge_margin_w
   trekken een kleine buffer af van het doel om constante micro-correcties te vermijden.

4. Vermogensverdeling: netto doel gelijkmatig verdelen over alle apparaten,
   daarna begrenzen naar individuele apparaatlimieten.
"""
from __future__ import annotations

import logging

from ..const import NOM_DISCHARGE_THRESHOLD_W, NOM_CHARGE_THRESHOLD_W, NOM_RAMP_FACTOR
from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class NomStrategy(BaseStrategy):
    """Nul op de Meter (NOM) with ramp logic and hysteresis margins."""

    @property
    def name(self) -> str:
        return "nom"

    @property
    def friendly_name(self) -> str:
        return "Nul op de Meter (NOM)"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        grid_w = context.grid_power_w

        # --- Threshold check: ignore small imbalances ---
        if abs(grid_w) < min(NOM_DISCHARGE_THRESHOLD_W, NOM_CHARGE_THRESHOLD_W):
            _LOGGER.debug("NOM: grid=%.0fW below threshold, standby", grid_w)
            for device in devices:
                await device.set_standby()
            return

        # --- Determine target per device with ramp logic ---
        # grid_w > 0 → consuming → discharge (negative power)
        # grid_w < 0 → returning → charge (positive power)
        for device in devices:
            last_state = context.device_states.get(device.device_id)
            already_active_in_direction = _is_already_active(last_state, grid_w)

            ramp = 1.0 if already_active_in_direction else NOM_RAMP_FACTOR

            if grid_w > NOM_DISCHARGE_THRESHOLD_W:
                # Consuming from grid → discharge
                target = (grid_w / len(devices)) * ramp - context.discharge_margin_w
                power_w = max(-target, -device.max_discharge_power_w)
            elif grid_w < -NOM_CHARGE_THRESHOLD_W:
                # Returning to grid → charge
                target = (abs(grid_w) / len(devices)) * ramp - context.charge_margin_w
                power_w = min(target, device.max_charge_power_w)
            else:
                # Between thresholds → standby
                await device.set_standby()
                continue

            _LOGGER.debug(
                "NOM: grid=%.0fW %s ramp=%.0f%% → %.0fW",
                grid_w, device.name, ramp * 100, power_w,
            )
            await device.set_charge(power_w)


def _is_already_active(state, grid_w: float) -> bool:
    """
    Return True if the device is already running in the direction we need.
    grid_w > 0 → we want to discharge → check if currently discharging (power_w < 0)
    grid_w < 0 → we want to charge   → check if currently charging   (power_w > 0)
    """
    if state is None:
        return False
    if grid_w > 0:
        return state.power_w < -50   # Already discharging
    return state.power_w > 50        # Already charging
