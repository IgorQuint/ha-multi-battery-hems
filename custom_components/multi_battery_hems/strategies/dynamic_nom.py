"""
Dynamic NOM strategy (improved).
/ Dynamisch NOM strategie (verbeterd).

Enhanced NOM with time-of-use pricing overlay.

Inspired by Gielz/zenSDK "Dynamic NOM" mode:
  - During cheap hours: charge extra beyond NOM (even without solar surplus)
  - During expensive hours: discharge extra beyond NOM
  - Normal hours: pure NOM behaviour with ramp + margin logic

Key improvement over basic Dynamic NOM:
  - Spread validation: extra trading only activates if the price spread
    between cheap and expensive hours is large enough to justify battery cycling.
  - Uses the same ramp factor and hysteresis margins as the improved NOM strategy.

/ Verbeterde NOM met tijdgebaseerde prijsoverlay.

Geïnspireerd door Gielz/zenSDK "Dynamisch NOM" modus:
  - Tijdens goedkope uren: extra laden bovenop NOM (ook zonder zonne-overschot)
  - Tijdens dure uren: extra ontladen bovenop NOM
  - Normale uren: puur NOM-gedrag met ramp + margelogica

Belangrijke verbetering ten opzichte van basis Dynamisch NOM:
  - Spread-validatie: extra handel activeert alleen als de prijsspread
    tussen goedkope en dure uren groot genoeg is om batterijcycli te rechtvaardigen.
  - Gebruikt dezelfde ramp-factor en hysteresismarges als de verbeterde NOM-strategie.
"""
from __future__ import annotations

import logging
from typing import List

from ..const import NOM_DISCHARGE_THRESHOLD_W, NOM_CHARGE_THRESHOLD_W, NOM_RAMP_FACTOR
from .base import BaseStrategy, StrategyContext, calculate_spread
from .nom import _is_already_active

_LOGGER = logging.getLogger(__name__)

_EXTRA_POWER_FRACTION = 0.50  # Extra power as fraction of total device capacity


class DynamicNomStrategy(BaseStrategy):
    """Dynamic NOM: NOM + spread-validated time-of-use price optimisation."""

    @property
    def name(self) -> str:
        return "dynamic_nom"

    @property
    def friendly_name(self) -> str:
        return "Dynamisch NOM"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        grid_w = context.grid_power_w

        # Calculate spread and check viability
        spread_data = calculate_spread(
            context.prices_today, context.cheap_hours, context.expensive_hours
        )
        spread_viable = spread_data["spread_pct"] >= context.min_spread_pct

        modifier = "normal"
        if spread_viable and context.prices_today:
            modifier = _price_modifier(
                context.current_price_eur,
                spread_data["cheap_threshold"],
                spread_data["expensive_threshold"],
            )

        _LOGGER.debug(
            "DynamicNOM: grid=%.0fW price=%.4f spread=%.1f%% viable=%s modifier=%s",
            grid_w, context.current_price_eur, spread_data["spread_pct"],
            spread_viable, modifier,
        )

        # Base NOM target
        nom_target = -grid_w

        # Price overlay
        if modifier == "cheap":
            extra = sum(d.max_charge_power_w for d in devices) * _EXTRA_POWER_FRACTION
            total_target = nom_target + extra
        elif modifier == "expensive":
            extra = sum(d.max_discharge_power_w for d in devices) * _EXTRA_POWER_FRACTION
            total_target = nom_target - extra
        else:
            total_target = nom_target

        target_per_device = total_target / len(devices)

        for device in devices:
            last_state = context.device_states.get(device.device_id)
            already_active = _is_already_active(last_state, -total_target)
            ramp = 1.0 if already_active else NOM_RAMP_FACTOR

            if target_per_device >= 0:
                power_w = min(target_per_device * ramp - context.charge_margin_w,
                              device.max_charge_power_w)
                power_w = max(power_w, 0)
            else:
                power_w = max(target_per_device * ramp + context.discharge_margin_w,
                              -device.max_discharge_power_w)
                power_w = min(power_w, 0)

            _LOGGER.debug("DynamicNOM: %s → %.0fW (ramp=%.0f%%)", device.name, power_w, ramp * 100)
            await device.set_charge(power_w)


def _price_modifier(current: float, cheap_threshold: float, expensive_threshold: float) -> str:
    """Map current price to 'cheap', 'expensive', or 'normal'."""
    if current <= cheap_threshold:
        return "cheap"
    if current >= expensive_threshold:
        return "expensive"
    return "normal"
