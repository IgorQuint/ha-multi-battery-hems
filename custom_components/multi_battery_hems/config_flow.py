"""
Config flow for Multi Battery HEMS.
/ Configuratiestroom voor Multi Battery HEMS.

Allows installation via the Home Assistant UI (Settings → Integrations → Add).
Also provides an Options flow so users can change strategy after setup.

/ Maakt installatie via de Home Assistant UI mogelijk (Instellingen → Integraties → Toevoegen).
Biedt ook een Options-stroom zodat gebruikers de strategie na installatie kunnen wijzigen.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    STRATEGIES,
    STRATEGY_FRIENDLY_NAMES,
    CONF_STRATEGY,
    CONF_P1_SENSOR,
    CONF_PRICE_SENSOR,
    CONF_PRICE_ATTRIBUTE,
    CONF_MARSTEK_ENABLED,
    CONF_MARSTEK_DEVICE_ID,
    CONF_ZENDURE_ENABLED,
    CONF_ZENDURE_NAME,
    CONF_ZENDURE_CHARGE_LIMIT_ENTITY,
    CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY,
    DEFAULT_STRATEGY,
    DEFAULT_P1_SENSOR,
    DEFAULT_PRICE_SENSOR,
    DEFAULT_PRICE_ATTRIBUTE,
    DEFAULT_MARSTEK_DEVICE_ID,
    DEFAULT_ZENDURE_NAME,
    DEFAULT_ZENDURE_CHARGE_LIMIT,
    DEFAULT_ZENDURE_DISCHARGE_LIMIT,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step schemas
# ---------------------------------------------------------------------------

_SCHEMA_STEP_GENERAL = vol.Schema(
    {
        vol.Required(CONF_P1_SENSOR, default=DEFAULT_P1_SENSOR): str,
        vol.Required(CONF_PRICE_SENSOR, default=DEFAULT_PRICE_SENSOR): str,
        vol.Optional(CONF_PRICE_ATTRIBUTE, default=DEFAULT_PRICE_ATTRIBUTE): str,
        vol.Required(CONF_STRATEGY, default=DEFAULT_STRATEGY): vol.In(STRATEGIES),
    }
)

_SCHEMA_STEP_DEVICES = vol.Schema(
    {
        vol.Required(CONF_MARSTEK_ENABLED, default=True): bool,
        vol.Required(CONF_ZENDURE_ENABLED, default=True): bool,
    }
)

_SCHEMA_STEP_MARSTEK = vol.Schema(
    {
        vol.Required(CONF_MARSTEK_DEVICE_ID, default=DEFAULT_MARSTEK_DEVICE_ID): str,
    }
)

_SCHEMA_STEP_ZENDURE = vol.Schema(
    {
        vol.Optional(CONF_ZENDURE_NAME, default=DEFAULT_ZENDURE_NAME): str,
        vol.Required(
            CONF_ZENDURE_CHARGE_LIMIT_ENTITY, default=DEFAULT_ZENDURE_CHARGE_LIMIT
        ): str,
        vol.Required(
            CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY, default=DEFAULT_ZENDURE_DISCHARGE_LIMIT
        ): str,
    }
)

_SCHEMA_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_STRATEGY, default=DEFAULT_STRATEGY): vol.In(STRATEGIES),
    }
)


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class MultiHemsBatteryConfigFlow(ConfigFlow, domain=DOMAIN):
    """
    Handle the initial configuration flow (Settings → Integrations → Add).
    Multi-step: general → devices → marstek (optional) → zendure (optional).

    / Verwerkt de initiële configuratiestroom (Instellingen → Integraties → Toevoegen).
    Meerdere stappen: algemeen → apparaten → marstek (optioneel) → zendure (optioneel).
    """

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    # Step 1: general settings (sensors + default strategy)
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=_SCHEMA_STEP_GENERAL,
            errors=errors,
            description_placeholders={},
        )

    # Step 2: which devices are present?
    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)

            if user_input.get(CONF_MARSTEK_ENABLED):
                return await self.async_step_marstek()
            if user_input.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure()
            return self._create_entry()

        return self.async_show_form(
            step_id="devices",
            data_schema=_SCHEMA_STEP_DEVICES,
        )

    # Step 3a: Marstek configuration
    async def async_step_marstek(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)

            if self._data.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure()
            return self._create_entry()

        return self.async_show_form(
            step_id="marstek",
            data_schema=_SCHEMA_STEP_MARSTEK,
        )

    # Step 3b: Zendure configuration
    async def async_step_zendure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="zendure",
            data_schema=_SCHEMA_STEP_ZENDURE,
        )

    def _create_entry(self) -> FlowResult:
        return self.async_create_entry(
            title="Multi Battery HEMS",
            data=self._data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "HemsOptionsFlow":
        return HemsOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow (post-setup strategy change)
# ---------------------------------------------------------------------------


class HemsOptionsFlow(OptionsFlow):
    """
    Allow changing the active strategy via Settings → Integrations → Configure.
    / Sta het wijzigen van de actieve strategie toe via Instellingen → Integraties → Configureren.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_strategy = self._config_entry.options.get(
            CONF_STRATEGY,
            self._config_entry.data.get(CONF_STRATEGY, DEFAULT_STRATEGY),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_STRATEGY, default=current_strategy): vol.In(STRATEGIES),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
