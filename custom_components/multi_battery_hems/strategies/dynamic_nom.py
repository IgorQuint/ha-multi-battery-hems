"""
Dynamic NOM strategy.
/ Dynamisch NOM strategie.

Like NOM but overlays time-of-use pricing:
  - Cheap hours  (< 85 % of day average)  →  charge extra beyond NOM
  - Expensive hours (> 115 % of day average) →  discharge extra beyond NOM
  - Normal hours  →  pure NOM behaviour

Extra power in cheap/expensive hours is 50 % of total device capacity,
added on top of the NOM correction. This can be tuned via the constants below.

/ Net als NOM maar voegt tijdgebaseerde prijsoptimalisatie toe:
  - Goedkope uren  (< 85 % van daggemiddelde)  →  extra laden bovenop NOM
  - Dure uren (> 115 % van daggemiddelde)       →  extra ontladen bovenop NOM
  - Normale uren  →  puur NOM-gedrag

Extra vermogen in goedkope/dure uren is 50 % van totale apparaatcapaciteit,
bovenop de NOM-correctie. Dit kan worden afgesteld via de constanten hieronder.
"""
from __future__ import annotations

import logging
from typing import List

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)

# Thresholds relative to day-average price
# / Drempelwaarden relatief ten opzichte van de daggemiddelde prijs
_CHEAP_RATIO = 0.85
_EXPENSIVE_RATIO = 1.15

# Fraction of total device capacity used as extra charge/discharge in peak hours
# / Fractie van totale apparaatcapaciteit die wordt gebruikt als extra laad-/ontlaadvermogen
_EXTRA_POWER_FRACTION = 0.50


class DynamicNomStrategy(BaseStrategy):
    """
    Dynamic NOM: NOM + time-of-use price optimisation.
    / Dynamisch NOM: NOM + tijdgebaseerde prijsoptimalisatie.
    """

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
        nom_target_total = -grid_w

        modifier = self._price_modifier(context.current_price_eur, context.prices_today)
        _LOGGER.debug(
            "DynamicNOM: grid=%.0fW price=%.4f EUR modifier=%s",
            grid_w, context.current_price_eur, modifier,
        )

        if modifier == "cheap":
            extra = sum(d.max_charge_power_w for d in devices) * _EXTRA_POWER_FRACTION
            total_target = nom_target_total + extra
        elif modifier == "expensive":
            extra = sum(d.max_discharge_power_w for d in devices) * _EXTRA_POWER_FRACTION
            total_target = nom_target_total - extra
        else:
            total_target = nom_target_total

        target_per_device = total_target / len(devices)

        for device in devices:
            if target_per_device >= 0:
                power_w = min(target_per_device, device.max_charge_power_w)
            else:
                power_w = max(target_per_device, -device.max_discharge_power_w)

            _LOGGER.debug(
                "DynamicNOM: %s → %.0fW", device.name, power_w
            )
            await device.set_charge(power_w)

    @staticmethod
    def _price_modifier(current_price: float, prices: List[dict]) -> str:
        """
        Return 'cheap', 'expensive', or 'normal' based on today's price list.
        / Geeft 'cheap', 'expensive' of 'normal' terug op basis van de prijslijst van vandaag.
        """
        if not prices:
            return "normal"

        values = [p["price"] for p in prices if "price" in p]
        if not values:
            return "normal"

        avg = sum(values) / len(values)
        if current_price < avg * _CHEAP_RATIO:
            return "cheap"
        if current_price > avg * _EXPENSIVE_RATIO:
            return "expensive"
        return "normal"
