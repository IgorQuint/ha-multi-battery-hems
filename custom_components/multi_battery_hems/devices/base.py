"""
Abstract base class for battery devices.
/ Abstracte basisklasse voor batterij-apparaten.

To add a new battery brand:
1. Create a new file in this directory (e.g. my_brand.py)
2. Subclass BatteryDevice and implement all abstract methods
3. Register it in coordinator.py

Om een nieuw batterijmerk toe te voegen:
1. Maak een nieuw bestand in deze map (bijv. my_brand.py)
2. Maak een subklasse van BatteryDevice en implementeer alle abstracte methoden
3. Registreer het in coordinator.py
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class BatteryState:
    """
    Snapshot of a battery device's current state.
    / Momentopname van de huidige toestand van een batterij-apparaat.
    """
    device_id: str
    name: str
    # Positive = charging (W), Negative = discharging (W)
    # Positief = laden (W), Negatief = ontladen (W)
    power_w: float = 0.0
    soc_pct: Optional[float] = None   # State of Charge 0–100 %
    available: bool = True


class BatteryDevice(ABC):
    """
    Abstract base class for all battery device drivers.
    / Abstracte basisklasse voor alle batterij-apparaat-drivers.
    """

    def __init__(self, name: str, hass) -> None:
        self.name = name
        self.hass = hass

    # --- Identity ---

    @property
    @abstractmethod
    def device_id(self) -> str:
        """Stable unique identifier for this device instance."""

    # --- Control ---

    @abstractmethod
    async def set_charge(self, power_w: float) -> None:
        """
        Command the device to charge or discharge.

        Args:
            power_w: Target power in watts.
                     Positive  →  charge (draw from grid / solar).
                     Negative  →  discharge (feed into home / grid).

        / Stuur het apparaat opdracht om te laden of ontladen.

        Args:
            power_w: Doelvermogen in watt.
                     Positief  →  laden (stroom uit net / zon).
                     Negatief  →  ontladen (stroom naar huis / net).
        """

    @abstractmethod
    async def set_standby(self) -> None:
        """
        Put device in standby — no charge, no discharge.
        / Zet het apparaat in stand-by — niet laden, niet ontladen.
        """

    # --- Telemetry ---

    @abstractmethod
    async def get_state(self) -> BatteryState:
        """
        Return current device state.
        / Geef de huidige toestand van het apparaat terug.
        """

    # --- Limits (used by strategies for safe clamping) ---

    @property
    @abstractmethod
    def max_charge_power_w(self) -> float:
        """Maximum charge power in watts (positive)."""

    @property
    @abstractmethod
    def max_discharge_power_w(self) -> float:
        """Maximum discharge power in watts (positive value)."""
