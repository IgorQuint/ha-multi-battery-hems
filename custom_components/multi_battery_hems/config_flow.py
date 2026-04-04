"""
Config flow for Multi Battery HEMS.
/ Configuratiestroom voor Multi Battery HEMS.

Setup steps:
  1. user       — P1 sensor, price sensor, default strategy
  2. devices    — which batteries are present
  3. marstek    — Marstek device ID + optional SoC entity
  4. zendure    — Zendure entity IDs + optional SoC entity
  5. advanced   — SoC limits, margins, dynamic period settings, manual power

All sensor/entity fields use HA EntitySelector (dropdown).
Options flow and reconfigure cover all the same steps so users never need
to remove/re-add the integration.
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
    CONF_MARSTEK_SOC_ENTITY,
    CONF_ZENDURE_ENABLED,
    CONF_ZENDURE_NAME,
    CONF_ZENDURE_CHARGE_LIMIT_ENTITY,
    CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY,
    CONF_ZENDURE_SOC_ENTITY,
    CONF_MIN_SOC_PCT,
    CONF_MAX_SOC_PCT,
    CONF_CHARGE_MARGIN_W,
    CONF_DISCHARGE_MARGIN_W,
    CONF_CHEAP_HOURS,
    CONF_EXPENSIVE_HOURS,
    CONF_MIN_SPREAD_PCT,
    CONF_MANUAL_POWER_W,
    CONF_INVERT_P1_SIGN,
    DEFAULT_STRATEGY,
    DEFAULT_PRICE_ATTRIBUTE,
    DEFAULT_ZENDURE_NAME,
    DEFAULT_MIN_SOC_PCT,
    DEFAULT_MAX_SOC_PCT,
    DEFAULT_CHARGE_MARGIN_W,
    DEFAULT_DISCHARGE_MARGIN_W,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_EXPENSIVE_HOURS,
    DEFAULT_MIN_SPREAD_PCT,
    DEFAULT_MANUAL_POWER_W,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reusable selectors
# ---------------------------------------------------------------------------

_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)
_SENSOR_OPTIONAL_SELECTOR = selector.EntitySelector(
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


def _num_selector(min_val: float, max_val: float, step: float = 1, unit: str = "") -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_val,
            max=max_val,
            step=step,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


# ---------------------------------------------------------------------------
# Schema builders — all pre-filled with current values
# ---------------------------------------------------------------------------

def _schema_general(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_P1_SENSOR,
            description={"suggested_value": d.get(CONF_P1_SENSOR, "")}): _SENSOR_SELECTOR,
        vol.Required(CONF_PRICE_SENSOR,
            description={"suggested_value": d.get(CONF_PRICE_SENSOR, "")}): _SENSOR_SELECTOR,
        vol.Optional(CONF_PRICE_ATTRIBUTE,
            description={"suggested_value": d.get(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)}): _TEXT_SELECTOR,
        vol.Required(CONF_STRATEGY,
            description={"suggested_value": d.get(CONF_STRATEGY, DEFAULT_STRATEGY)}): _STRATEGY_SELECTOR,
    })


def _schema_devices(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_MARSTEK_ENABLED,
            description={"suggested_value": d.get(CONF_MARSTEK_ENABLED, False)}): _BOOL_SELECTOR,
        vol.Required(CONF_ZENDURE_ENABLED,
            description={"suggested_value": d.get(CONF_ZENDURE_ENABLED, False)}): _BOOL_SELECTOR,
    })


def _schema_marstek(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_MARSTEK_DEVICE_ID,
            description={"suggested_value": d.get(CONF_MARSTEK_DEVICE_ID, "")}): _TEXT_SELECTOR,
        vol.Optional(CONF_MARSTEK_SOC_ENTITY,
            description={"suggested_value": d.get(CONF_MARSTEK_SOC_ENTITY, "")}): _SENSOR_SELECTOR,
    })


def _schema_zendure(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_ZENDURE_NAME,
            description={"suggested_value": d.get(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)}): _TEXT_SELECTOR,
        vol.Required(CONF_ZENDURE_CHARGE_LIMIT_ENTITY,
            description={"suggested_value": d.get(CONF_ZENDURE_CHARGE_LIMIT_ENTITY, "")}): _NUMBER_SELECTOR,
        vol.Required(CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY,
            description={"suggested_value": d.get(CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY, "")}): _NUMBER_SELECTOR,
        vol.Optional(CONF_ZENDURE_SOC_ENTITY,
            description={"suggested_value": d.get(CONF_ZENDURE_SOC_ENTITY, "")}): _SENSOR_SELECTOR,
    })


def _schema_advanced(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_INVERT_P1_SIGN,
            description={"suggested_value": d.get(CONF_INVERT_P1_SIGN, False)}): _BOOL_SELECTOR,
        vol.Optional(CONF_MIN_SOC_PCT,
            description={"suggested_value": d.get(CONF_MIN_SOC_PCT, DEFAULT_MIN_SOC_PCT)}):
            _num_selector(0, 50, 1, "%"),
        vol.Optional(CONF_MAX_SOC_PCT,
            description={"suggested_value": d.get(CONF_MAX_SOC_PCT, DEFAULT_MAX_SOC_PCT)}):
            _num_selector(50, 100, 1, "%"),
        vol.Optional(CONF_CHARGE_MARGIN_W,
            description={"suggested_value": d.get(CONF_CHARGE_MARGIN_W, DEFAULT_CHARGE_MARGIN_W)}):
            _num_selector(0, 250, 5, "W"),
        vol.Optional(CONF_DISCHARGE_MARGIN_W,
            description={"suggested_value": d.get(CONF_DISCHARGE_MARGIN_W, DEFAULT_DISCHARGE_MARGIN_W)}):
            _num_selector(0, 250, 5, "W"),
        vol.Optional(CONF_CHEAP_HOURS,
            description={"suggested_value": d.get(CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS)}):
            _num_selector(1, 12, 1, "uur"),
        vol.Optional(CONF_EXPENSIVE_HOURS,
            description={"suggested_value": d.get(CONF_EXPENSIVE_HOURS, DEFAULT_EXPENSIVE_HOURS)}):
            _num_selector(1, 12, 1, "uur"),
        vol.Optional(CONF_MIN_SPREAD_PCT,
            description={"suggested_value": d.get(CONF_MIN_SPREAD_PCT, DEFAULT_MIN_SPREAD_PCT)}):
            _num_selector(0, 100, 1, "%"),
        vol.Optional(CONF_MANUAL_POWER_W,
            description={"suggested_value": d.get(CONF_MANUAL_POWER_W, DEFAULT_MANUAL_POWER_W)}):
            _num_selector(-4800, 4800, 50, "W"),
    })


# ---------------------------------------------------------------------------
# Mixin: shared multi-step flow logic
# Used by both ConfigFlow and OptionsFlow to avoid duplication.
# ---------------------------------------------------------------------------

class _HemsFlowMixin:
    """Shared step implementations for config and options flows."""

    _data: dict

    def _next_after_devices(self, user_input: dict):
        """Determine next step after device selection."""
        if user_input.get(CONF_MARSTEK_ENABLED):
            return "marstek"
        if user_input.get(CONF_ZENDURE_ENABLED):
            return "zendure"
        return "advanced"

    def _next_after_marstek(self, data: dict):
        if data.get(CONF_ZENDURE_ENABLED):
            return "zendure"
        return "advanced"


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------

class MultiHemsBatteryConfigFlow(_HemsFlowMixin, ConfigFlow, domain=DOMAIN):
    """
    Multi-step setup flow: general → devices → marstek → zendure → advanced.

    / Meerdere stappen: algemeen → apparaten → marstek → zendure → geavanceerd.
    """

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices()
        return self.async_show_form(step_id="user", data_schema=_schema_general(self._data))

    async def async_step_devices(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_devices(user_input)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(step_id="devices", data_schema=_schema_devices(self._data))

    async def async_step_marstek(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_marstek(self._data)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(step_id="marstek", data_schema=_schema_marstek(self._data))

    async def async_step_zendure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return await self.async_step_advanced()
        return self.async_show_form(step_id="zendure", data_schema=_schema_zendure(self._data))

    async def async_step_advanced(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="Multi Battery HEMS", data=self._data)
        return self.async_show_form(step_id="advanced", data_schema=_schema_advanced(self._data))

    # --- Reconfigure ---

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        self._data = dict(self._config_entry.data)
        if user_input is not None:
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices_reconfigure()
        return self.async_show_form(step_id="reconfigure", data_schema=_schema_general(self._data))

    async def async_step_devices_reconfigure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_devices(user_input)
            return await getattr(self, f"async_step_{next_step}_reconfigure")()
        return self.async_show_form(step_id="devices_reconfigure", data_schema=_schema_devices(self._data))

    async def async_step_marstek_reconfigure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_marstek(self._data)
            return await getattr(self, f"async_step_{next_step}_reconfigure")()
        return self.async_show_form(step_id="marstek_reconfigure", data_schema=_schema_marstek(self._data))

    async def async_step_zendure_reconfigure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return await self.async_step_advanced_reconfigure()
        return self.async_show_form(step_id="zendure_reconfigure", data_schema=_schema_zendure(self._data))

    async def async_step_advanced_reconfigure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_update_reload_and_abort(
                self._config_entry, data=self._data, reason="reconfigure_successful"
            )
        return self.async_show_form(step_id="advanced_reconfigure", data_schema=_schema_advanced(self._data))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "HemsOptionsFlow":
        return HemsOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow — full settings, pre-filled with current values
# ---------------------------------------------------------------------------

class HemsOptionsFlow(_HemsFlowMixin, OptionsFlow):
    """Full options flow: same steps as config flow, pre-filled."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data: dict[str, Any] = {**config_entry.data, **config_entry.options}

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
            self._data.update(user_input)
            return await self.async_step_devices()
        return self.async_show_form(step_id="init", data_schema=_schema_general(self._data))

    async def async_step_devices(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_devices(user_input)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(step_id="devices", data_schema=_schema_devices(self._data))

    async def async_step_marstek(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            next_step = self._next_after_marstek(self._data)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(step_id="marstek", data_schema=_schema_marstek(self._data))

    async def async_step_zendure(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input.setdefault(CONF_ZENDURE_NAME, DEFAULT_ZENDURE_NAME)
            self._data.update(user_input)
            return await self.async_step_advanced()
        return self.async_show_form(step_id="zendure", data_schema=_schema_zendure(self._data))

    async def async_step_advanced(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        return self.async_show_form(step_id="advanced", data_schema=_schema_advanced(self._data))
