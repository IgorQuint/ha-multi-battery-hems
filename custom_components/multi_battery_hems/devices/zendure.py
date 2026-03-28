"""
Zendure SolarFlow battery device driver.
/ Driver voor Zendure SolarFlow batterij via HA number-entiteiten.

Controlled via two `number` entities:
  - Charge limit  : 0–1000 W
  - Discharge limit: 0–800 W

Strategy: when charging, set charge limit and zero discharge limit.
          When discharging, set discharge limit and zero charge limit.
          This prevents conflicting simultaneous commands.

/ Aangestuurd via twee `number`-entiteiten:
  - Laadlimiet     : 0–1000 W
  - Ontlaadlimiet  : 0–800 W

Strategie: bij laden, stel laadlimiet in en zet ontlaadlimiet op nul.
           Bij ontladen, stel ontlaadlimiet in en zet laadlimiet op nul.
           Dit voorkomt conflicterende gelijktijdige opdrachten.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import ZENDURE_MAX_CHARGE_W, ZENDURE_MAX_DISCHARGE_W
from .base import BatteryDevice, BatteryState

_LOGGER = logging.getLogger(__name__)


class ZendureDevice(BatteryDevice):
    """
    Driver for Zendure SolarFlow via Home Assistant number entities.
    / Driver voor Zendure SolarFlow via Home Assistant number-entiteiten.

    Multiple Zendure units can be added by creating multiple instances
    with different entity IDs.
    / Meerdere Zendure-eenheden kunnen worden toegevoegd door meerdere
    instanties te maken met verschillende entiteit-ID's.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        charge_limit_entity: str,
        discharge_limit_entity: str,
    ) -> None:
        super().__init__(name, hass)
        self._charge_entity = charge_limit_entity
        self._discharge_entity = discharge_limit_entity
        self._current_power_w: float = 0.0

    # --- Identity ---

    @property
    def device_id(self) -> str:
        # Use the charge entity ID as unique device identifier
        # / Gebruik het laad-entiteit-ID als unieke apparaat-identifier
        return self._charge_entity

    # --- Limits ---

    @property
    def max_charge_power_w(self) -> float:
        return ZENDURE_MAX_CHARGE_W

    @property
    def max_discharge_power_w(self) -> float:
        return ZENDURE_MAX_DISCHARGE_W

    # --- Control ---

    async def set_charge(self, power_w: float) -> None:
        """
        Set charge or discharge power by adjusting the appropriate limit entity.

        power_w > 0  →  charging  : set charge limit, disable discharge
        power_w < 0  →  discharging: set discharge limit, disable charging
        power_w == 0 →  standby   : both limits to 0

        / Stel laad- of ontlaadvermogen in via de bijbehorende limiet-entiteit.
        """
        if power_w > 0:
            charge_w = min(power_w, ZENDURE_MAX_CHARGE_W)
            _LOGGER.debug(
                "Zendure [%s]: charging at %sW", self.name, charge_w
            )
            await self._set_number(self._discharge_entity, 0)
            await self._set_number(self._charge_entity, int(charge_w))
        elif power_w < 0:
            discharge_w = min(abs(power_w), ZENDURE_MAX_DISCHARGE_W)
            _LOGGER.debug(
                "Zendure [%s]: discharging at %sW", self.name, discharge_w
            )
            await self._set_number(self._charge_entity, 0)
            await self._set_number(self._discharge_entity, int(discharge_w))
        else:
            await self.set_standby()
            return

        self._current_power_w = power_w

    async def set_standby(self) -> None:
        """
        Disable both charge and discharge by setting both limits to 0.
        / Schakel zowel laden als ontladen uit door beide limieten op 0 te zetten.
        """
        _LOGGER.debug("Zendure [%s]: standby", self.name)
        await self._set_number(self._charge_entity, 0)
        await self._set_number(self._discharge_entity, 0)
        self._current_power_w = 0.0

    # --- Telemetry ---

    async def get_state(self) -> BatteryState:
        """
        Derive current state from HA entity states.
        / Bepaal huidige toestand vanuit HA-entiteitstoestanden.
        """
        charge_state = self.hass.states.get(self._charge_entity)
        discharge_state = self.hass.states.get(self._discharge_entity)
        available = (
            charge_state is not None
            and discharge_state is not None
            and charge_state.state not in ("unavailable", "unknown")
            and discharge_state.state not in ("unavailable", "unknown")
        )
        return BatteryState(
            device_id=self.device_id,
            name=self.name,
            power_w=self._current_power_w,
            soc_pct=None,
            available=available,
        )

    # --- Internal helpers ---

    async def _set_number(self, entity_id: str, value: int) -> None:
        """Call the number.set_value service."""
        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": str(value)},
        )
