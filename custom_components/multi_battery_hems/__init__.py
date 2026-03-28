"""
Multi Battery HEMS — Home Energy Management System for multiple batteries.
/ Multi Battery HEMS — Energiebeheersysteem voor meerdere batterijen.

Supports simultaneous control of multiple battery brands (Marstek, Zendure, ...)
using configurable strategies:
  • Standby         — all batteries off
  • NOM             — zero-import/export (Nul op de Meter)
  • Dynamic NOM     — NOM + time-of-use price optimisation
  • Arbitrage       — charge during cheapest hours, discharge during most expensive

Financial tracking per device and combined:
  - Cumulative kWh charged/discharged
  - Cost/revenue per day, week, month, year

/ Ondersteunt gelijktijdige aansturing van meerdere batterijmerken (Marstek, Zendure, ...)
met configureerbare strategieën:
  • Standby         — alle batterijen uit
  • NOM             — nul-op-de-meter
  • Dynamisch NOM   — NOM + tijdgebaseerde prijsoptimalisatie
  • Arbitrage       — laden in goedkoopste uren, ontladen in duurste uren

Financiële bijhouding per apparaat en gecombineerd:
  - Cumulatieve kWh geladen/ontladen
  - Kosten/opbrengst per dag, week, maand, jaar
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HemsCoordinator

_LOGGER = logging.getLogger(__name__)

# Platforms provided by this integration
PLATFORMS = [Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up Multi Battery HEMS from a config entry.
    Called by HA after the user completes the config flow.

    / Stel Multi Battery HEMS in vanuit een config-entry.
    Wordt door HA aangeroepen nadat de gebruiker de configuratiestroom heeft voltooid.
    """
    hass.data.setdefault(DOMAIN, {})

    coordinator = HemsCoordinator(hass, entry)
    await coordinator.async_setup()

    # First refresh — blocks until data is available
    # / Eerste verversing — blokkeert totdat gegevens beschikbaar zijn
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register a listener so option changes (e.g. strategy) propagate immediately
    # / Registreer een luisteraar zodat optiewijzigingen (bijv. strategie) onmiddellijk worden doorgegeven
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Multi Battery HEMS set up successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry (e.g. when integration is removed).
    / Verwijder een config-entry (bijv. wanneer de integratie wordt verwijderd).
    """
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Handle updates to options (e.g. strategy changed via OptionsFlow).
    Reloads the config entry to apply changes cleanly.

    / Verwerk updates van opties (bijv. strategie gewijzigd via OptionsFlow).
    Herlaadt de config-entry om wijzigingen schoon toe te passen.
    """
    _LOGGER.debug("Options updated, reloading HEMS entry")
    await hass.config_entries.async_reload(entry.entry_id)
