"""
Strategy selector entity for Multi Battery HEMS.
/ Strategie-selectie-entiteit voor Multi Battery HEMS.

Creates a `select` entity that lets users change the active HEMS strategy
directly from the Home Assistant dashboard (no restart required).

/ Maakt een `select`-entiteit die gebruikers de actieve HEMS-strategie
direct vanuit het Home Assistant-dashboard laat wijzigen (geen herstart vereist).
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STRATEGIES, STRATEGY_FRIENDLY_NAMES
from .coordinator import HemsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the strategy selector."""
    coordinator: HemsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HemsStrategySelect(coordinator, entry)])


class HemsStrategySelect(CoordinatorEntity, SelectEntity):
    """
    Select entity for choosing the active HEMS strategy.
    / Select-entiteit voor het kiezen van de actieve HEMS-strategie.

    Selecting a new option immediately updates the coordinator's active strategy
    without requiring a restart or reloading the integration.

    / Het selecteren van een nieuwe optie werkt onmiddellijk de actieve strategie
    van de coördinator bij zonder herstart of herladen van de integratie.
    """

    _attr_has_entity_name = True
    _attr_name = "Actieve strategie"
    _attr_icon = "mdi:strategy"

    def __init__(self, coordinator: HemsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_strategy_select"
        self._attr_options = [STRATEGY_FRIENDLY_NAMES[s] for s in STRATEGIES]

    @property
    def current_option(self) -> str | None:
        return STRATEGY_FRIENDLY_NAMES.get(self.coordinator.active_strategy)

    async def async_select_option(self, option: str) -> None:
        """
        Handle user selecting a new strategy from the dropdown.
        / Verwerk gebruikersselectie van een nieuwe strategie uit de keuzelijst.
        """
        # Reverse lookup: friendly name → strategy key
        key = next(
            (k for k, v in STRATEGY_FRIENDLY_NAMES.items() if v == option), None
        )
        if key is None:
            _LOGGER.warning("Unknown strategy option selected: %s", option)
            return

        _LOGGER.info("User changed strategy to: %s (%s)", key, option)
        self.coordinator.active_strategy = key
        # Trigger an immediate coordinator refresh so the new strategy takes effect
        await self.coordinator.async_request_refresh()
