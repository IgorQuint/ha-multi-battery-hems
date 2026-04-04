"""
Number entities for Multi Battery HEMS.
/ Number-entiteiten voor Multi Battery HEMS.

Provides a P1 test override entity:
  number.multi_battery_hems_p1_testwaarde

When set to a non-zero value, the coordinator uses this as the P1 reading
instead of the real sensor. Set to 0 to return to normal operation.

Useful for testing strategies without physical grid manipulation.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([HemsP1TestOverride(entry)])


class HemsP1TestOverride(NumberEntity):
    """
    Test override for P1 meter reading.
    Set to non-zero to inject a fake grid power value for testing.

    Positive = simulate grid consumption (should trigger discharge in NOM).
    Negative = simulate grid export/solar surplus (should trigger charging in NOM).
    Zero = disabled, use real P1 sensor.
    """

    _attr_has_entity_name = True
    _attr_name = "P1 testwaarde"
    _attr_icon = "mdi:test-tube"
    _attr_native_min_value = -5000
    _attr_native_max_value = 5000
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"
    _attr_mode = NumberMode.BOX
    _attr_native_value = 0.0

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_p1_testwaarde"
        self._entry = entry

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        if value != 0:
            _LOGGER.info("HEMS test mode: P1 override = %.0fW", value)
        else:
            _LOGGER.info("HEMS test mode: disabled, using real P1 sensor")
