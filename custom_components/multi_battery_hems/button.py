"""
Button entities for Multi Battery HEMS.
/ Knop-entiteiten voor Multi Battery HEMS.

Quick action buttons visible in the dashboard:
  - Force refresh (trigger immediate coordinator update)
  - Reset P1 test override to 0 (exit test mode)
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HemsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HemsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HemsRefreshButton(coordinator, entry),
        HemsResetTestButton(coordinator, entry),
    ])


class _HemsBaseButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HemsCoordinator, entry: ConfigEntry, suffix: str, name: str) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = name


class HemsRefreshButton(_HemsBaseButton):
    """Force an immediate coordinator refresh."""
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "refresh", "Nu bijwerken")

    async def async_press(self) -> None:
        _LOGGER.debug("Manual refresh triggered")
        await self._coordinator.async_request_refresh()


class HemsResetTestButton(_HemsBaseButton):
    """Reset P1 test override to 0 (exit test mode)."""
    _attr_icon = "mdi:test-tube-off"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "reset_test", "Stop testmodus")

    async def async_press(self) -> None:
        entity_id = f"number.{DOMAIN}_p1_testwaarde"
        state = self._coordinator.hass.states.get(entity_id)
        if state:
            await self._coordinator.hass.services.async_call(
                "number", "set_value",
                {"entity_id": entity_id, "value": "0"},
            )
