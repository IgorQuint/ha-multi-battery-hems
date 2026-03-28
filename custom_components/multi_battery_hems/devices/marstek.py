"""
Marstek Venus E battery device driver.
/ Driver voor Marstek Venus E batterij via marstek_local_api.

Controlled via the `marstek_local_api.set_passive_mode` HA service.
Power range: -2500 W (discharge) to +800 W (charge).
Duration is set to 120 s so the coordinator can refresh it every 60 s.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import (
    MARSTEK_MIN_POWER_W,
    MARSTEK_MAX_POWER_W,
    MARSTEK_DURATION_SECONDS,
)
from .base import BatteryDevice, BatteryState

_LOGGER = logging.getLogger(__name__)

_SERVICE_DOMAIN = "marstek_local_api"
_SERVICE_NAME = "set_passive_mode"


class MarstekDevice(BatteryDevice):
    """
    Driver for Marstek Venus E (5.12 kWh) via marstek_local_api integration.
    / Driver voor Marstek Venus E (5,12 kWh) via marstek_local_api integratie.
    """

    def __init__(self, hass: HomeAssistant, device_id: str) -> None:
        super().__init__("Marstek Venus E", hass)
        self._device_id = device_id
        self._current_power_w: float = 0.0

    # --- Identity ---

    @property
    def device_id(self) -> str:
        return self._device_id

    # --- Limits ---

    @property
    def max_charge_power_w(self) -> float:
        return MARSTEK_MAX_POWER_W

    @property
    def max_discharge_power_w(self) -> float:
        return abs(MARSTEK_MIN_POWER_W)

    # --- Control ---

    async def set_charge(self, power_w: float) -> None:
        """
        Send power setpoint to Marstek via HA service call.
        Value is clamped to device limits before sending.

        / Stuur vermogenssetpoint naar Marstek via HA service-aanroep.
        Waarde wordt begrensd tot apparaatlimieten vóór verzending.
        """
        clamped = max(MARSTEK_MIN_POWER_W, min(MARSTEK_MAX_POWER_W, power_w))
        _LOGGER.debug(
            "Marstek [%s]: set_charge requested=%sW clamped=%sW",
            self._device_id, power_w, clamped,
        )
        await self.hass.services.async_call(
            _SERVICE_DOMAIN,
            _SERVICE_NAME,
            {
                "device_id": self._device_id,
                "power": int(clamped),
                "duration": MARSTEK_DURATION_SECONDS,
            },
        )
        self._current_power_w = clamped

    async def set_standby(self) -> None:
        """
        Set Marstek to passive mode at 0 W (no charge, no discharge).
        / Zet Marstek op passieve modus op 0 W (niet laden, niet ontladen).
        """
        await self.set_charge(0)

    # --- Telemetry ---

    async def get_state(self) -> BatteryState:
        """
        Return current known state.
        Note: marstek_local_api does not expose a real-time SoC sensor yet,
        so soc_pct is None until that becomes available.

        / Geef huidige bekende toestand terug.
        Opmerking: marstek_local_api biedt nog geen real-time SoC-sensor,
        daarom is soc_pct None totdat dit beschikbaar komt.
        """
        return BatteryState(
            device_id=self._device_id,
            name=self.name,
            power_w=self._current_power_w,
            soc_pct=None,
            available=True,
        )
