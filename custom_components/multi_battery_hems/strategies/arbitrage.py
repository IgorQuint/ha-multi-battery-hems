"""
Arbitrage strategy.
/ Arbitrage-strategie.

Charge at maximum power during the N cheapest hours of the day.
Discharge at maximum power during the M most expensive hours of the day.
Standby during all other hours.

Uses today's price list (sensor attribute) to determine hours.
The current price is compared against the threshold prices for today's
cheapest/most-expensive buckets, so the strategy self-adapts as new
price data arrives.

/ Laad met maximaal vermogen gedurende de N goedkoopste uren van de dag.
Ontlaad met maximaal vermogen gedurende de M duurste uren van de dag.
Stand-by tijdens alle overige uren.

Gebruikt de prijslijst van vandaag (sensor-attribuut) om uren te bepalen.
De actuele prijs wordt vergeleken met de drempelwaarden voor de goedkoopste/
duurste buckets van vandaag, zodat de strategie zich aanpast als nieuwe
prijsdata binnenkomt.
"""
from __future__ import annotations

import logging
from typing import List

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)

# Number of cheapest hours to charge / goedkoopste uren om te laden
_CHEAP_HOURS = 3
# Number of most expensive hours to discharge / duurste uren om te ontladen
_EXPENSIVE_HOURS = 4


class ArbitrageStrategy(BaseStrategy):
    """
    Arbitrage: charge cheap, discharge expensive.
    / Arbitrage: laden bij goedkoop, ontladen bij duur.
    """

    @property
    def name(self) -> str:
        return "arbitrage"

    @property
    def friendly_name(self) -> str:
        return "Arbitrage"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        if not context.prices_today:
            _LOGGER.warning(
                "Arbitrage: no price data available, falling back to standby"
            )
            for device in devices:
                await device.set_standby()
            return

        action = self._determine_action(
            context.current_price_eur, context.prices_today
        )
        _LOGGER.debug(
            "Arbitrage: price=%.4f EUR → action=%s", context.current_price_eur, action
        )

        for device in devices:
            if action == "charge":
                await device.set_charge(device.max_charge_power_w)
            elif action == "discharge":
                await device.set_charge(-device.max_discharge_power_w)
            else:
                await device.set_standby()

    @staticmethod
    def _determine_action(current_price: float, prices: List[dict]) -> str:
        """
        Determine whether to charge, discharge, or stay in standby
        based on where the current price falls in today's sorted price list.

        / Bepaal of geladen, ontladen of stand-by gehouden moet worden
        op basis van de positie van de actuele prijs in de gesorteerde prijslijst.
        """
        price_values = sorted(
            p["price"] for p in prices if "price" in p
        )
        if not price_values:
            return "standby"

        # Threshold prices (inclusive)
        cheap_limit = price_values[min(_CHEAP_HOURS, len(price_values)) - 1]
        expensive_limit = price_values[max(0, len(price_values) - _EXPENSIVE_HOURS)]

        # Discharge takes priority over charge if both thresholds overlap
        if current_price >= expensive_limit:
            return "discharge"
        if current_price <= cheap_limit:
            return "charge"
        return "standby"
