"""
Abstract base class and context for HEMS strategies.
/ Abstracte basisklasse en context voor HEMS-strategieën.

StrategyContext carries all runtime state a strategy needs:
  - Grid power from P1 meter
  - Current price and today's price list
  - Device list with their current states
  - SoC limits and hysteresis margins from user config
  - Dynamic period settings for arbitrage
  - Manual power setpoint

SoC protection is enforced at the coordinator level *before* calling execute(),
so strategies do not need to implement their own SoC guards.

/ StrategyContext draagt alle runtime-toestand die een strategie nodig heeft:
  - Netvermogen van de P1-meter
  - Actuele prijs en prijslijst van vandaag
  - Apparatenlijst met hun huidige toestanden
  - SoC-limieten en hysteresismarges vanuit gebruikersconfiguratie
  - Dynamische periode-instellingen voor arbitrage
  - Handmatig vermogensinstellingspunt

SoC-bescherming wordt afgedwongen door de coördinator *vóór* het aanroepen van execute(),
zodat strategieën geen eigen SoC-bewakers hoeven te implementeren.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

from ..devices.base import BatteryDevice, BatteryState
from ..const import (
    DEFAULT_MIN_SOC_PCT,
    DEFAULT_MAX_SOC_PCT,
    DEFAULT_CHARGE_MARGIN_W,
    DEFAULT_DISCHARGE_MARGIN_W,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_EXPENSIVE_HOURS,
    DEFAULT_MIN_SPREAD_PCT,
    DEFAULT_MANUAL_POWER_W,
)


@dataclass
class StrategyContext:
    """
    Runtime context provided to every strategy execution.
    / Runtime-context die bij elke strategie-uitvoering wordt meegegeven.
    """

    # --- Grid & price ---
    # P1 meter in watts: positive = consuming, negative = returning
    # / P1-meter in watt: positief = verbruik, negatief = teruglevering
    grid_power_w: float

    # Current spot price in EUR/kWh
    current_price_eur: float

    # Today's hourly price list: [{"time": "HH:MM", "price": float}, ...]
    prices_today: List[dict] = field(default_factory=list)

    # --- Devices ---
    devices: List[BatteryDevice] = field(default_factory=list)

    # Last known state per device (device_id → BatteryState)
    # Used by NOM for ramp logic (were we already charging/discharging?)
    # / Laatste bekende toestand per apparaat (device_id → BatteryState)
    # Gebruikt door NOM voor ramp-logica (waren we al aan het laden/ontladen?)
    device_states: Dict[str, BatteryState] = field(default_factory=dict)

    # --- SoC protection ---
    # Hard limits — coordinator enforces these before calling execute()
    # / Harde limieten — coördinator dwingt deze af vóór execute() aanroep
    min_soc_pct: float = DEFAULT_MIN_SOC_PCT
    max_soc_pct: float = DEFAULT_MAX_SOC_PCT

    # --- NOM hysteresis margins ---
    # Prevents rapid on/off cycling of charge/discharge relay
    # / Voorkomt snel aan/uit-schakelen van laad/ontlaad-relay
    charge_margin_w: float = DEFAULT_CHARGE_MARGIN_W
    discharge_margin_w: float = DEFAULT_DISCHARGE_MARGIN_W

    # --- Dynamic period settings ---
    cheap_hours: int = DEFAULT_CHEAP_HOURS         # N cheapest hours per day
    expensive_hours: int = DEFAULT_EXPENSIVE_HOURS  # M most expensive hours per day
    min_spread_pct: float = DEFAULT_MIN_SPREAD_PCT  # Minimum spread % to justify trading

    # --- Manual strategy ---
    manual_power_w: float = DEFAULT_MANUAL_POWER_W  # Positive = charge, negative = discharge


class BaseStrategy(ABC):
    """Abstract base for all HEMS strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-readable identifier (matches STRATEGY_* constants)."""

    @property
    @abstractmethod
    def friendly_name(self) -> str:
        """Human-readable name (shown in UI)."""

    @abstractmethod
    async def execute(self, context: StrategyContext) -> None:
        """
        Execute one control cycle.
        SoC limits are already enforced by the coordinator before this is called.

        / Voer één regelcyclus uit.
        SoC-limieten zijn al afgedwongen door de coördinator voor deze aanroep.
        """


# ---------------------------------------------------------------------------
# Shared price helpers (used by multiple strategies)
# ---------------------------------------------------------------------------

def calculate_spread(prices: List[dict], cheap_hours: int, expensive_hours: int) -> dict:
    """
    Calculate the price spread between the N cheapest and M most expensive hours.
    Returns a dict with cheap_threshold, expensive_threshold, spread_pct, and viable flag.

    Methodology from Gielz/zenSDK:
    spread_pct = ((avg_expensive - avg_cheap) / avg_cheap) × 100
    Arbitrage is only viable when spread_pct >= configured minimum.

    / Berekent de prijsspread tussen de N goedkoopste en M duurste uren.
    Geeft een dict terug met cheap_threshold, expensive_threshold, spread_pct en viable-vlag.

    Methodiek van Gielz/zenSDK:
    spread_pct = ((gem_duur - gem_goedkoop) / gem_goedkoop) × 100
    Arbitrage is alleen zinvol als spread_pct >= geconfigureerd minimum.
    """
    values = sorted(p["price"] for p in prices if "price" in p)
    if not values:
        return {"cheap_threshold": 0, "expensive_threshold": 0, "spread_pct": 0, "viable": False}

    n_cheap = min(cheap_hours, len(values))
    n_expensive = min(expensive_hours, len(values))

    cheap_prices = values[:n_cheap]
    expensive_prices = values[-n_expensive:]

    avg_cheap = sum(cheap_prices) / len(cheap_prices)
    avg_expensive = sum(expensive_prices) / len(expensive_prices)

    spread_pct = ((avg_expensive - avg_cheap) / avg_cheap * 100) if avg_cheap > 0 else 0

    return {
        "cheap_threshold": cheap_prices[-1],      # Highest of the N cheap prices
        "expensive_threshold": expensive_prices[0],  # Lowest of the M expensive prices
        "avg_cheap": avg_cheap,
        "avg_expensive": avg_expensive,
        "spread_pct": spread_pct,
        "viable": True,  # Caller checks against min_spread_pct
    }
