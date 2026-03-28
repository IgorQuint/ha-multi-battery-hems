"""
HEMS Coordinator — the heart of Multi Battery HEMS.
/ HEMS Coördinator — het hart van Multi Battery HEMS.

Runs every UPDATE_INTERVAL_SECONDS seconds and:
  1. Reads the P1 meter (grid power)
  2. Reads the current electricity price and today's price list
  3. Executes the active strategy across all devices
  4. Updates the financial tracker
  5. Persists financial data

/ Draait elke UPDATE_INTERVAL_SECONDS seconden en:
  1. Leest de P1-meter (netvermogen)
  2. Leest de actuele elektriciteitsprijs en de prijslijst voor vandaag
  3. Voert de actieve strategie uit op alle apparaten
  4. Werkt de financiële tracker bij
  5. Slaat financiële gegevens op
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
    CONF_P1_SENSOR,
    CONF_PRICE_SENSOR,
    CONF_PRICE_ATTRIBUTE,
    CONF_STRATEGY,
    CONF_MARSTEK_ENABLED,
    CONF_MARSTEK_DEVICE_ID,
    CONF_ZENDURE_ENABLED,
    CONF_ZENDURE_NAME,
    CONF_ZENDURE_CHARGE_LIMIT_ENTITY,
    CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY,
    DEFAULT_STRATEGY,
    DEFAULT_PRICE_ATTRIBUTE,
)
from .devices import BatteryDevice, MarstekDevice, ZendureDevice
from .financial import FinancialTracker
from .strategies import STRATEGY_MAP, StrategyContext

_LOGGER = logging.getLogger(__name__)


class HemsCoordinator(DataUpdateCoordinator):
    """
    Central coordinator for Multi Battery HEMS.
    Inherits from DataUpdateCoordinator for built-in scheduling and error handling.

    / Centrale coördinator voor Multi Battery HEMS.
    Erft van DataUpdateCoordinator voor ingebouwde planning en foutafhandeling.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._entry = entry
        self._config = entry.data
        self._options = entry.options

        # Active strategy identifier (can be changed at runtime via select entity)
        self._active_strategy: str = self._options.get(
            CONF_STRATEGY, self._config.get(CONF_STRATEGY, DEFAULT_STRATEGY)
        )

        # Instantiate device drivers from config
        self._devices: List[BatteryDevice] = self._build_devices()

        # Financial tracker
        self._tracker = FinancialTracker(hass)

        # Runtime state (exposed to sensor platform)
        self.grid_power_w: float = 0.0
        self.current_price_eur: float = 0.0
        self.prices_today: list = []

    # --- Public API ---

    @property
    def active_strategy(self) -> str:
        return self._active_strategy

    @active_strategy.setter
    def active_strategy(self, value: str) -> None:
        if value not in STRATEGY_MAP:
            _LOGGER.warning("Unknown strategy '%s', ignoring", value)
            return
        _LOGGER.info("HEMS strategy changed: %s → %s", self._active_strategy, value)
        self._active_strategy = value

    @property
    def devices(self) -> List[BatteryDevice]:
        return self._devices

    @property
    def tracker(self) -> FinancialTracker:
        return self._tracker

    # --- Lifecycle ---

    async def async_setup(self) -> None:
        """
        Load persisted financial data before first update.
        / Laad persistente financiële gegevens vóór de eerste update.
        """
        await self._tracker.async_load()

    # --- Core update loop ---

    async def _async_update_data(self) -> dict:
        """
        Called every UPDATE_INTERVAL_SECONDS by the coordinator framework.
        Returns a dict that sensors can use directly.

        / Wordt elke UPDATE_INTERVAL_SECONDS aangeroepen door het coördinator-framework.
        Geeft een dict terug die sensoren direct kunnen gebruiken.
        """
        try:
            self.grid_power_w = self._read_p1()
            self.current_price_eur, self.prices_today = self._read_prices()

            strategy = STRATEGY_MAP.get(self._active_strategy)
            if strategy is None:
                raise UpdateFailed(f"Unknown strategy: {self._active_strategy}")

            context = StrategyContext(
                grid_power_w=self.grid_power_w,
                current_price_eur=self.current_price_eur,
                prices_today=self.prices_today,
                devices=self._devices,
            )
            await strategy().execute(context)

            # Update financial tracker for each device
            for device in self._devices:
                state = await device.get_state()
                if state.available:
                    self._tracker.update(
                        device.device_id, state.power_w, self.current_price_eur
                    )

            # Persist after each cycle (cheap operation, uses HA's debounced writer)
            await self._tracker.async_save()

        except UpdateFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"HEMS update failed: {exc}") from exc

        return {
            "strategy": self._active_strategy,
            "grid_power_w": self.grid_power_w,
            "current_price_eur": self.current_price_eur,
        }

    # --- Sensor reading helpers ---

    def _read_p1(self) -> float:
        """
        Read the current grid power from the P1 meter sensor.
        Returns 0.0 if the sensor is unavailable.

        / Lees het huidige netvermogen van de P1-metersensor.
        Geeft 0,0 terug als de sensor niet beschikbaar is.
        """
        entity_id: str = self._config.get(CONF_P1_SENSOR, "")
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            _LOGGER.warning("P1 sensor '%s' unavailable, using 0W", entity_id)
            return 0.0
        try:
            return float(state.state)
        except ValueError:
            _LOGGER.warning(
                "P1 sensor '%s' has non-numeric state '%s'", entity_id, state.state
            )
            return 0.0

    def _read_prices(self) -> tuple[float, list]:
        """
        Read current price and today's price list from the price sensor.
        Returns (current_price, prices_today).

        / Lees de actuele prijs en de prijslijst voor vandaag van de prijssensor.
        Geeft (actuele_prijs, prijslijst_vandaag) terug.
        """
        entity_id: str = self._config.get(CONF_PRICE_SENSOR, "")
        attribute: str = self._config.get(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)

        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            _LOGGER.warning("Price sensor '%s' unavailable", entity_id)
            return 0.0, []

        try:
            current_price = float(state.state)
        except ValueError:
            current_price = 0.0

        prices_today = state.attributes.get(attribute, [])
        if not isinstance(prices_today, list):
            prices_today = []

        return current_price, prices_today

    # --- Device factory ---

    def _build_devices(self) -> List[BatteryDevice]:
        """
        Instantiate device drivers from config entry data.
        / Maak apparaat-drivers aan vanuit de config-entry gegevens.
        """
        devices: List[BatteryDevice] = []

        if self._config.get(CONF_MARSTEK_ENABLED):
            device_id = self._config.get(CONF_MARSTEK_DEVICE_ID, "")
            devices.append(MarstekDevice(self.hass, device_id))
            _LOGGER.info("HEMS: Marstek Venus E added (device_id=%s)", device_id)

        if self._config.get(CONF_ZENDURE_ENABLED):
            devices.append(
                ZendureDevice(
                    hass=self.hass,
                    name=self._config.get(CONF_ZENDURE_NAME, "Zendure"),
                    charge_limit_entity=self._config.get(CONF_ZENDURE_CHARGE_LIMIT_ENTITY, ""),
                    discharge_limit_entity=self._config.get(CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY, ""),
                )
            )
            _LOGGER.info(
                "HEMS: Zendure '%s' added", self._config.get(CONF_ZENDURE_NAME)
            )

        if not devices:
            _LOGGER.warning(
                "HEMS: no devices configured — "
                "strategies will run but have no devices to control"
            )
        return devices
