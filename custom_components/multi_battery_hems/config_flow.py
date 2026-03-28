"""
Config flow for Multi Battery HEMS.
/ Configuratiestroom voor Multi Battery HEMS.

Features:
  - Entity selectors (dropdowns) for all sensor / number entity fields
  - SelectSelector with friendly names for strategy choice
  - Full OptionsFlow covering ALL settings (not just strategy)
  - async_step_reconfigure so users can re-run setup from the integration card
    without removing and re-adding the integration

/ Functies:
  - Entity-selectors (keuzelijsten) voor alle sensor-/number-entiteitvelden
  - SelectSelector met leesbare namen voor strategiekeuze
  - Volledige OptionsFlow voor ALLE instellingen (niet alleen strategie)
  - async_step_reconfigure zodat gebruikers de setup opnieuw kunnen uitvoeren
    vanuit de integratiekaart, zonder de integratie te verwijderen en opnieuw toe te voegen
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
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
    DEFAULT_PRICE_ATTRIBUTE,
    DEFAULT_ZENDURE_NAME,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reusable selectors
# ---------------------------------------------------------------------------

_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

_NUMBER_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="number")
)

_BOOL_SELECTOR = selector.BooleanSelector()

_TEXT_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
)

_STRATEGY_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value=k, label=v)
            for k, v in STRATEGY_FRIENDLY_NAMES.items()
        ],
        mode=selector.SelectSelectorMode.LIST,
    )
)


# ---------------------------------------------------------------------------
# Schema builders (functions so defaults can be injected at runtime)
# ---------------------------------------------------------------------------

def _schema_general(defaults: dict) -> vol.Schema:
    """Step 1: P1 sensor, price sensor, strategy."""
    return vol.Schema(
        {
            vol.Required(
                CONF_P1_SENSOR,
                description={"suggested_value": defaults.get(CONF_P1_SENSOR, "")},
            ): _SENSOR_SELECTOR,
            vol.Required(
                CONF_PRICE_SENSOR,
                description={"suggested_value": defaults.get(CONF_PRICE_SENSOR, "")},
            ): _SENSOR_SELECTOR,
            vol.Optional(
                CONF_PRICE_ATTRIBUTE,
                description={"suggested_value": defaults.get(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)},
            ): _TEXT_SELECTOR,
            vol.Required(
                CONF_STRATEGY,
                description={"suggested_value": defaults.get(CONF_STRATEGY, DEFAULT_STRATEGY)},
            ): _STRATEGY_SELECTOR,
        }
    )


def _schema_devices(defaults: dict) -> vol.Schema:
    """Step 2: which devices are present."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MARSTEK_ENABLED,
                description={"suggested_value": defaults.get(CONF_MARSTEK_ENABLED, False)},
            ): _BOOL_SELECTOR,
            vol.Required(
                CONF_ZENDURE_ENABLED,
                description={"suggested_value": defaults.get(CONF_ZENDURE_ENABLED, False)},
            ): _BOOL_SELECTOR,
        }
    )


def _schema_marstek(defaults: dict) -> vol.Schema:
    """Step 3a: Marstek device ID."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MARSTEK_DEVICE_ID,
                description={"suggested_value": defaults.get(CONF_MARSTEK_DEVICE_ID, "")},
            ): _TEXT_SELECTOR,
        }
    )


def _schema_zendure(defaults: dict) -> vol.Schema:
    """Step 3b: Zendure entity IDs."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_ZENDURE_NAME,
                description={"suggested_value": defaults.get(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)},
            ): _TEXT_SELECTOR,
            vol.Required(
                CONF_ZENDURE_CHARGE_LIMIT_ENTITY,
                description={"suggested_value": defaults.get(CONF_ZENDURE_CHARGE_LIMIT_ENTITY, "")},
            ): _NUMBER_SELECTOR,
            vol.Required(
                CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY,
                description={"suggested_value": defaults.get(CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY, "")},
            ): _NUMBER_SELECTOR,
        }
    )


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class MultiHemsBatteryConfigFlow(ConfigFlow, domain=DOMAIN):
    """
    Multi-step config flow: general → devices → marstek (optional) → zendure (optional).

    All entity fields use HA's EntitySelector so the user picks from a dropdown
    instead of typing entity IDs by hand.

    / Meerdere stappen: algemeen → apparaten → marstek (optioneel) → zendure (optioneel).

    Alle entiteitvelden gebruiken HA's EntitySelector zodat de gebruiker
    kiest uit een keuzelijst in plaats van entiteit-ID's handmatig in te typen.
    """

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Step 1 — General (sensors + strategy)
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Store price_attribute default if omitted
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=_schema_general(self._data),
        )

    # ------------------------------------------------------------------
    # Step 2 — Device selection
    # ------------------------------------------------------------------

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
            data_schema=_schema_devices(self._data),
        )

    # ------------------------------------------------------------------
    # Step 3a — Marstek
    # ------------------------------------------------------------------

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
            data_schema=_schema_marstek(self._data),
        )

    # ------------------------------------------------------------------
    # Step 3b — Zendure
    # ------------------------------------------------------------------

    async def async_step_zendure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="zendure",
            data_schema=_schema_zendure(self._data),
        )

    # ------------------------------------------------------------------
    # Reconfigure — re-run full setup from the integration card
    # ("Herconfigueren" button in HA 2024.x)
    # ------------------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Allow users to change any setting after initial setup,
        pre-filled with current values.

        / Sta gebruikers toe om instellingen te wijzigen na de initiële setup,
        vooraf ingevuld met huidige waarden.
        """
        # Pre-fill with current config entry data
        self._data = dict(self._config_entry.data)

        if user_input is not None:
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices_reconfigure()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema_general(self._data),
        )

    async def async_step_devices_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_MARSTEK_ENABLED):
                return await self.async_step_marstek_reconfigure()
            if user_input.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure_reconfigure()
            return self._update_entry()

        return self.async_show_form(
            step_id="devices_reconfigure",
            data_schema=_schema_devices(self._data),
        )

    async def async_step_marstek_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if self._data.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure_reconfigure()
            return self._update_entry()

        return self.async_show_form(
            step_id="marstek_reconfigure",
            data_schema=_schema_marstek(self._data),
        )

    async def async_step_zendure_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return self._update_entry()

        return self.async_show_form(
            step_id="zendure_reconfigure",
            data_schema=_schema_zendure(self._data),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_entry(self) -> FlowResult:
        return self.async_create_entry(title="Multi Battery HEMS", data=self._data)

    def _update_entry(self) -> FlowResult:
        """Update the existing config entry during reconfigure."""
        return self.async_update_reload_and_abort(
            self._config_entry,
            data=self._data,
            reason="reconfigure_successful",
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "HemsOptionsFlow":
        return HemsOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow — change ANY setting after setup (Settings → Integrations → Configure)
# ---------------------------------------------------------------------------


class HemsOptionsFlow(OptionsFlow):
    """
    Full options flow covering all settings.
    Pre-filled with the current values so the user only changes what they want.

    Covers the same steps as the config flow (general → devices → marstek → zendure).

    / Volledige opties-stroom die alle instellingen dekt.
    Vooraf ingevuld met de huidige waarden zodat de gebruiker alleen wijzigt wat nodig is.

    Dezelfde stappen als de configuratiestroom (algemeen → apparaten → marstek → zendure).
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        # Start with a merged view of current data + options
        self._data: dict[str, Any] = {
            **config_entry.data,
            **config_entry.options,
        }

    # ------------------------------------------------------------------
    # Step 1 — General
    # ------------------------------------------------------------------

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices()

        return self.async_show_form(
            step_id="init",
            data_schema=_schema_general(self._data),
        )

    # ------------------------------------------------------------------
    # Step 2 — Devices
    # ------------------------------------------------------------------

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_MARSTEK_ENABLED):
                return await self.async_step_marstek()
            if user_input.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure()
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="devices",
            data_schema=_schema_devices(self._data),
        )

    # ------------------------------------------------------------------
    # Step 3a — Marstek
    # ------------------------------------------------------------------

    async def async_step_marstek(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if self._data.get(CONF_ZENDURE_ENABLED):
                return await self.async_step_zendure()
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="marstek",
            data_schema=_schema_marstek(self._data),
        )

    # ------------------------------------------------------------------
    # Step 3b — Zendure
    # ------------------------------------------------------------------

    async def async_step_zendure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="zendure",
            data_schema=_schema_zendure(self._data),
        )
