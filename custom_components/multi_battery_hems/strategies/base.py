"""
Abstract base class for HEMS strategies.
/ Abstracte basisklasse voor HEMS-strategieën.

To add a new strategy:
1. Create a new file in this directory (e.g. my_strategy.py)
2. Subclass BaseStrategy and implement all abstract methods
3. Add it to STRATEGY_MAP in strategies/__init__.py

Om een nieuwe strategie toe te voegen:
1. Maak een nieuw bestand in deze map (bijv. my_strategy.py)
2. Maak een subklasse van BaseStrategy en implementeer alle abstracte methoden
3. Voeg het toe aan STRATEGY_MAP in strategies/__init__.py
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from ..devices.base import BatteryDevice


@dataclass
class StrategyContext:
    """
    Runtime context provided to every strategy execution.
    / Runtime-context die bij elke strategie-uitvoering wordt meegegeven.
    """
    # P1 meter reading in watts
    # Positive  = consuming from grid  / Positief = verbruik uit net
    # Negative  = returning to grid    / Negatief = teruglevering aan net
    grid_power_w: float

    # Current electricity price in EUR/kWh
    # / Actuele elektriciteitsprijs in EUR/kWh
    current_price_eur: float

    # Today's hourly price list: [{"time": "HH:MM", "price": float}, ...]
    # / Prijslijst voor vandaag per uur: [{"time": "UU:MM", "price": float}, ...]
    prices_today: List[dict] = field(default_factory=list)

    # All active battery devices
    # / Alle actieve batterij-apparaten
    devices: List[BatteryDevice] = field(default_factory=list)


class BaseStrategy(ABC):
    """Abstract base for all HEMS strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-readable strategy identifier (matches STRATEGY_* constants)."""

    @property
    @abstractmethod
    def friendly_name(self) -> str:
        """Human-readable strategy name (used in UI)."""

    @abstractmethod
    async def execute(self, context: StrategyContext) -> None:
        """
        Execute this strategy for one control cycle.

        Args:
            context: Current grid state, prices and device list.

        / Voer deze strategie uit voor één regelcyclus.

        Args:
            context: Huidige netstatus, prijzen en apparatenlijst.
        """
