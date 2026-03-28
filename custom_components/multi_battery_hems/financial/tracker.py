"""
Financial tracker for Multi Battery HEMS.
/ Financiële tracker voor Multi Battery HEMS.

Tracks per device and combined:
  - Total kWh charged / discharged (never reset, cumulative)
  - kWh charged / discharged per period (daily / weekly / monthly / yearly)
  - Profit per period in EUR
    = revenue from discharging − cost of charging at the actual spot price

Resets happen automatically at the correct calendar boundaries:
  daily   → midnight every day
  weekly  → Monday (ISO week boundary)
  monthly → 1st of each month
  yearly  → 1st January

Energy is estimated from commanded power × interval duration.
This is a best-effort approximation; integrating actual energy sensors
from each device is recommended when they become available.

/ Bijgehouden per apparaat en gecombineerd:
  - Totaal kWh geladen / ontladen (nooit gereset, cumulatief)
  - kWh geladen / ontladen per periode (dag / week / maand / jaar)
  - Winst per periode in EUR
    = opbrengst uit ontladen − kosten van laden op actuele spotprijs

Resets vinden automatisch plaats op de juiste kalendergrenzen:
  dag     → middernacht elke dag
  week    → maandag (ISO-weekgrens)
  maand   → 1e van elke maand
  jaar    → 1 januari

Energie wordt geschat op basis van opgedragen vermogen × intervalsduur.
Dit is een beste schatting; het integreren van werkelijke energiesensoren
per apparaat wordt aanbevolen zodra deze beschikbaar komen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional

from homeassistant.helpers.storage import Store

from ..const import STORAGE_KEY, STORAGE_VERSION, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

# One coordinator cycle expressed in hours
_CYCLE_HOURS = UPDATE_INTERVAL_SECONDS / 3600


@dataclass
class _PeriodStats:
    """Energy and profit accumulators for one time period."""
    kwh_charged: float = 0.0
    kwh_discharged: float = 0.0
    profit_eur: float = 0.0


@dataclass
class DeviceFinancials:
    """
    All financial state for a single device (or 'combined').
    / Alle financiële staat voor één apparaat (of 'gecombineerd').
    """
    device_id: str

    # Lifetime totals (never reset)
    # / Levenslange totalen (nooit gereset)
    total_kwh_charged: float = 0.0
    total_kwh_discharged: float = 0.0

    # Period stats
    daily: _PeriodStats = field(default_factory=_PeriodStats)
    weekly: _PeriodStats = field(default_factory=_PeriodStats)
    monthly: _PeriodStats = field(default_factory=_PeriodStats)
    yearly: _PeriodStats = field(default_factory=_PeriodStats)

    # Last reset markers (ISO strings) so we know when to reset next
    # / Laatste reset-markers (ISO-strings) zodat we weten wanneer we opnieuw moeten resetten
    last_day: Optional[str] = None        # "YYYY-MM-DD"
    last_iso_week: Optional[str] = None   # "YYYY-WW"
    last_month: Optional[str] = None      # "YYYY-MM"
    last_year: Optional[str] = None       # "YYYY"

    def to_dict(self) -> dict:
        """Serialise to plain dict for persistent storage."""
        return {
            "device_id": self.device_id,
            "total_kwh_charged": self.total_kwh_charged,
            "total_kwh_discharged": self.total_kwh_discharged,
            "daily": asdict(self.daily),
            "weekly": asdict(self.weekly),
            "monthly": asdict(self.monthly),
            "yearly": asdict(self.yearly),
            "last_day": self.last_day,
            "last_iso_week": self.last_iso_week,
            "last_month": self.last_month,
            "last_year": self.last_year,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceFinancials":
        """Deserialise from stored dict."""
        obj = cls(device_id=data["device_id"])
        obj.total_kwh_charged = data.get("total_kwh_charged", 0.0)
        obj.total_kwh_discharged = data.get("total_kwh_discharged", 0.0)
        obj.daily = _PeriodStats(**data.get("daily", {}))
        obj.weekly = _PeriodStats(**data.get("weekly", {}))
        obj.monthly = _PeriodStats(**data.get("monthly", {}))
        obj.yearly = _PeriodStats(**data.get("yearly", {}))
        obj.last_day = data.get("last_day")
        obj.last_iso_week = data.get("last_iso_week")
        obj.last_month = data.get("last_month")
        obj.last_year = data.get("last_year")
        return obj


class FinancialTracker:
    """
    Persistent financial tracker for all battery devices.
    / Persistente financiële tracker voor alle batterij-apparaten.

    Call `update(device_id, power_w, price_eur_kwh)` once per coordinator cycle
    for each device. Aggregates are automatically maintained, including a
    'combined' pseudo-device.

    / Roep `update(device_id, power_w, price_eur_kwh)` eens per coördinatorcyclus
    aan voor elk apparaat. Aggregaten worden automatisch bijgehouden, inclusief een
    'gecombineerd' pseudo-apparaat.
    """

    COMBINED_ID = "combined"

    def __init__(self, hass) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, DeviceFinancials] = {}

    # --- Lifecycle ---

    async def async_load(self) -> None:
        """Load persisted data from HA storage."""
        stored = await self._store.async_load()
        if stored:
            for device_id, raw in stored.items():
                self._data[device_id] = DeviceFinancials.from_dict(raw)
        _LOGGER.debug("FinancialTracker: loaded %d device records", len(self._data))

    async def async_save(self) -> None:
        """Persist current data to HA storage."""
        payload = {k: v.to_dict() for k, v in self._data.items()}
        await self._store.async_save(payload)

    # --- Update (called every coordinator cycle) ---

    def update(self, device_id: str, power_w: float, price_eur_kwh: float) -> None:
        """
        Record one cycle of operation for a device.

        Args:
            device_id:     Unique device identifier.
            power_w:       Commanded power (positive = charging, negative = discharging).
            price_eur_kwh: Current electricity price in EUR/kWh.

        / Registreer één cyclus van werking voor een apparaat.

        Args:
            device_id:     Unieke apparaat-ID.
            power_w:       Opgedragen vermogen (positief = laden, negatief = ontladen).
            price_eur_kwh: Actuele elektriciteitsprijs in EUR/kWh.
        """
        fin = self._get_or_create(device_id)
        self._apply_resets(fin)

        kwh = abs(power_w) / 1000.0 * _CYCLE_HOURS
        value_eur = kwh * max(0.0, price_eur_kwh)

        if power_w > 0:
            # Charging — costs money
            fin.total_kwh_charged += kwh
            for period_stats in self._all_periods(fin):
                period_stats.kwh_charged += kwh
                period_stats.profit_eur -= value_eur
        elif power_w < 0:
            # Discharging — earns money
            fin.total_kwh_discharged += kwh
            for period_stats in self._all_periods(fin):
                period_stats.kwh_discharged += kwh
                period_stats.profit_eur += value_eur

        # Update combined pseudo-device
        combined = self._get_or_create(self.COMBINED_ID)
        self._apply_resets(combined)
        if power_w > 0:
            combined.total_kwh_charged += kwh
            for period_stats in self._all_periods(combined):
                period_stats.kwh_charged += kwh
                period_stats.profit_eur -= value_eur
        elif power_w < 0:
            combined.total_kwh_discharged += kwh
            for period_stats in self._all_periods(combined):
                period_stats.kwh_discharged += kwh
                period_stats.profit_eur += value_eur

    # --- Accessors ---

    def get(self, device_id: str) -> DeviceFinancials:
        """Return financial data for a device (creates empty entry if absent)."""
        return self._get_or_create(device_id)

    def device_ids(self):
        """Return all tracked device IDs (excluding combined)."""
        return [k for k in self._data if k != self.COMBINED_ID]

    # --- Internal helpers ---

    def _get_or_create(self, device_id: str) -> DeviceFinancials:
        if device_id not in self._data:
            self._data[device_id] = DeviceFinancials(device_id=device_id)
        return self._data[device_id]

    @staticmethod
    def _all_periods(fin: DeviceFinancials):
        return [fin.daily, fin.weekly, fin.monthly, fin.yearly]

    @staticmethod
    def _apply_resets(fin: DeviceFinancials) -> None:
        """
        Reset accumulators when calendar period boundaries are crossed.
        / Reset accumulatoren wanneer kalenderperiodegrenzen worden overschreden.
        """
        now = datetime.now()

        day_key = now.strftime("%Y-%m-%d")
        if fin.last_day != day_key:
            fin.daily = _PeriodStats()
            fin.last_day = day_key

        iso_year, iso_week, _ = now.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        if fin.last_iso_week != week_key:
            fin.weekly = _PeriodStats()
            fin.last_iso_week = week_key

        month_key = now.strftime("%Y-%m")
        if fin.last_month != month_key:
            fin.monthly = _PeriodStats()
            fin.last_month = month_key

        year_key = now.strftime("%Y")
        if fin.last_year != year_key:
            fin.yearly = _PeriodStats()
            fin.last_year = year_key
