"""
Arbitrage strategy (improved).
/ Arbitrage-strategie (verbeterd).

Charge at maximum power during the N cheapest hours of the day.
Discharge at maximum power during the M most expensive hours.
Standby during all other hours.

Key improvement over v0.1:
  - Spread validation: arbitrage only activates when the price difference between
    cheap and expensive hours is at least min_spread_pct (default 10%).
    Below this threshold the round-trip losses make trading uneconomical.
  - Configurable N and M (cheap_hours, expensive_hours) from config flow.
  - Shared calculate_spread() helper ensures consistent price analysis across strategies.

Methodology from Gielz/zenSDK:
  spread_pct = ((avg_expensive - avg_cheap) / avg_cheap) × 100

/ Laad met maximaal vermogen gedurende de N goedkoopste uren van de dag.
Ontlaad met maximaal vermogen gedurende de M duurste uren.
Stand-by tijdens alle overige uren.

Belangrijke verbetering ten opzichte van v0.1:
  - Spread-validatie: arbitrage activeert alleen als het prijsverschil tussen
    goedkope en dure uren minstens min_spread_pct (standaard 10%) is.
    Onder deze drempel zijn omrekeningsverliezen groter dan de winst.
  - Configureerbaar N en M (cheap_hours, expensive_hours) vanuit config flow.
  - Gedeelde calculate_spread()-helper zorgt voor consistente prijsanalyse.

Methodiek van Gielz/zenSDK:
  spread_pct = ((gem_duur - gem_goedkoop) / gem_goedkoop) × 100
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext, calculate_spread

_LOGGER = logging.getLogger(__name__)


class ArbitrageStrategy(BaseStrategy):
    """Arbitrage: charge cheap, discharge expensive — with spread validation."""

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
            _LOGGER.warning("Arbitrage: no price data — falling back to standby")
            for device in devices:
                await device.set_standby()
            return

        spread = calculate_spread(
            context.prices_today, context.cheap_hours, context.expensive_hours
        )

        # Spread check: is arbitrage economically viable?
        if spread["spread_pct"] < context.min_spread_pct:
            _LOGGER.info(
                "Arbitrage: spread=%.1f%% < minimum %.1f%% — standby (not economical)",
                spread["spread_pct"], context.min_spread_pct,
            )
            for device in devices:
                await device.set_standby()
            return

        action = _determine_action(
            context.current_price_eur,
            spread["cheap_threshold"],
            spread["expensive_threshold"],
        )

        _LOGGER.debug(
            "Arbitrage: price=%.4f cheap≤%.4f expensive≥%.4f spread=%.1f%% → %s",
            context.current_price_eur,
            spread["cheap_threshold"],
            spread["expensive_threshold"],
            spread["spread_pct"],
            action,
        )

        for device in devices:
            if action == "charge":
                await device.set_charge(device.max_charge_power_w)
            elif action == "discharge":
                await device.set_charge(-device.max_discharge_power_w)
            else:
                await device.set_standby()


def _determine_action(current: float, cheap_threshold: float, expensive_threshold: float) -> str:
    """
    Discharge takes priority when price qualifies for both windows simultaneously
    (can happen on days with very few price levels).
    / Ontladen heeft prioriteit als prijs voor beide vensters in aanmerking komt.
    """
    if current >= expensive_threshold:
        return "discharge"
    if current <= cheap_threshold:
        return "charge"
    return "standby"
