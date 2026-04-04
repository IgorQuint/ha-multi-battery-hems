"""
HEMS Coordinator — the heart of Multi Battery HEMS.
/ HEMS Coördinator — het hart van Multi Battery HEMS.

Runs every UPDATE_INTERVAL_SECONDS and:
  1. Reads the P1 meter (grid power)
  2. Reads the current electricity price and today's price list
  3. Reads SoC for each device (if an SoC entity is configured)
  4. Enforces SoC protection (min/max limits) — overrides strategy if needed
  5. Executes the active strategy across all devices
  6. Updates the financial tracker
  7. Persists financial data

SoC protection logic (from Gielz/zenSDK):
  - If any device SoC < min_soc AND the device can charge → force SOC_PROTECTION_CHARGE_W
    regardless of active strategy. This is a hard safety constraint.
  - If any device SoC > max_soc AND the device would charge → block charging (standby).

/ Draait elke UPDATE_INTERVAL_SECONDS en:
  1. Leest de P1-meter (netvermogen)
  2. Leest de actuele elektriciteitsprijs en de prijslijst voor vandaag
  3. Leest SoC per apparaat (als een SoC-entiteit is geconfigureerd)
  4. Dwingt SoC-bescherming af (min/max limieten) — overschrijft strategie indien nodig
  5. Voert de actieve strategie uit op alle apparaten
  6. Werkt de financiële tracker bij
  7. Slaat financiële gegevens op

SoC-beschermingslogica (van Gielz/zenSDK):
  - Als SoC van een apparaat < min_soc EN het apparaat kan laden → forceer SOC_PROTECTION_CHARGE_W
    ongeacht de actieve strategie. Dit is een harde veiligheidsbeperking.
  - Als SoC van een apparaat > max_soc EN het apparaat zou laden → blokkeer laden (stand-by).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
    SOC_PROTECTION_CHARGE_W,
    CONF_P1_SENSOR,
    CONF_PRICE_SENSOR,
    CONF_PRICE_ATTRIBUTE,
    CONF_STRATEGY,
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
    DEFAULT_MIN_SOC_PCT,
    DEFAULT_MAX_SOC_PCT,
    DEFAULT_CHARGE_MARGIN_W,
    DEFAULT_DISCHARGE_MARGIN_W,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_EXPENSIVE_HOURS,
    DEFAULT_MIN_SPREAD_PCT,
    DEFAULT_MANUAL_POWER_W,
    STRATEGY_FRIENDLY_NAMES,
)
from .devices import BatteryDevice, BatteryState, MarstekDevice, ZendureDevice
from .financial import FinancialTracker
from .strategies import STRATEGY_MAP, StrategyContext

_LOGGER = logging.getLogger(__name__)


class HemsCoordinator(DataUpdateCoordinator):
    """
    Central coordinator for Multi Battery HEMS.

    / Centrale coördinator voor Multi Battery HEMS.
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

        self._active_strategy: str = self._get_cfg(CONF_STRATEGY, DEFAULT_STRATEGY)

        # SoC entity IDs per device (optional — empty string means no SoC reading)
        self._soc_entities: Dict[str, str] = self._build_soc_entity_map()

        # Device instances
        self._devices: List[BatteryDevice] = self._build_devices()

        # Financial tracker
        self._tracker = FinancialTracker(hass)

        # Runtime state
        self.grid_power_w: float = 0.0
        self.current_price_eur: float = 0.0
        self.prices_today: list = []
        self.device_states: Dict[str, BatteryState] = {}

        # Status tracking (exposed to status sensor)
        self.last_action: str = "Onbekend"
        self.last_reason: str = ""
        self.p1_direction: str = ""
        self.price_category: str = ""
        self.p1_override_entity: str = ""  # entity_id of the override number entity

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
        """Load persisted financial data before first update."""
        await self._tracker.async_load()

    # --- Core update loop ---

    async def _async_update_data(self) -> dict:
        try:
            self.grid_power_w = self._read_p1()
            self.current_price_eur, self.prices_today = self._read_prices()

            # Read latest device states
            for device in self._devices:
                self.device_states[device.device_id] = await device.get_state()

            # Read SoC values for all devices
            soc_map = self._read_soc_values()

            # --- SoC protection (hard override, inspired by Gielz/zenSDK) ---
            protected = await self._apply_soc_protection(soc_map)

            if not protected:
                # No SoC override — execute normal strategy
                strategy_cls = STRATEGY_MAP.get(self._active_strategy)
                if strategy_cls is None:
                    raise UpdateFailed(f"Unknown strategy: {self._active_strategy}")

                context = self._build_context()
                await strategy_cls().execute(context)

            # Build last_action and last_reason for status sensor
            actions = []
            for device in self._devices:
                state = await device.get_state()
                if state.power_w > 50:
                    actions.append(f"{device.name}: laden {state.power_w:.0f}W")
                elif state.power_w < -50:
                    actions.append(f"{device.name}: ontladen {abs(state.power_w):.0f}W")
                else:
                    actions.append(f"{device.name}: standby")
            self.last_action = ", ".join(actions) if actions else "Standby"

            # Build reason
            direction = "verbruikt" if self.grid_power_w > 0 else "teruglevert"
            self.last_reason = (
                f"Net {direction} {abs(self.grid_power_w):.0f}W | "
                f"Prijs \u20ac{self.current_price_eur:.4f}/kWh | "
                f"Strategie: {STRATEGY_FRIENDLY_NAMES.get(self._active_strategy, self._active_strategy)}"
            )

            # Update financial tracker
            for device in self._devices:
                state = await device.get_state()
                self.device_states[device.device_id] = state
                if state.available:
                    self._tracker.update(
                        device.device_id, state.power_w, self.current_price_eur
                    )

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

    # --- SoC protection ---

    async def _apply_soc_protection(self, soc_map: Dict[str, float]) -> bool:
        """
        Enforce min/max SoC limits across all devices.
        Returns True if a protection override was applied (strategy should be skipped).

        / Dwingt min/max SoC-limieten af op alle apparaten.
        Geeft True terug als een beschermingsoverride is toegepast (strategie overslaan).
        """
        min_soc = float(self._get_cfg(CONF_MIN_SOC_PCT, DEFAULT_MIN_SOC_PCT))
        max_soc = float(self._get_cfg(CONF_MAX_SOC_PCT, DEFAULT_MAX_SOC_PCT))
        overridden = False

        for device in self._devices:
            soc = soc_map.get(device.device_id)
            if soc is None:
                continue  # No SoC data for this device — skip protection

            if soc < min_soc:
                _LOGGER.warning(
                    "SoC protection: %s SoC=%.1f%% < min=%.1f%% → force charge %sW",
                    device.name, soc, min_soc, SOC_PROTECTION_CHARGE_W,
                )
                await device.set_charge(SOC_PROTECTION_CHARGE_W)
                overridden = True

            elif soc >= max_soc:
                _LOGGER.debug(
                    "SoC protection: %s SoC=%.1f%% ≥ max=%.1f%% → standby",
                    device.name, soc, max_soc,
                )
                await device.set_standby()
                overridden = True

        return overridden

    # --- Context builder ---

    def _build_context(self) -> StrategyContext:
        """Assemble StrategyContext from current coordinator state and config."""
        return StrategyContext(
            grid_power_w=self.grid_power_w,
            current_price_eur=self.current_price_eur,
            prices_today=self.prices_today,
            devices=self._devices,
            device_states=self.device_states,
            min_soc_pct=float(self._get_cfg(CONF_MIN_SOC_PCT, DEFAULT_MIN_SOC_PCT)),
            max_soc_pct=float(self._get_cfg(CONF_MAX_SOC_PCT, DEFAULT_MAX_SOC_PCT)),
            charge_margin_w=float(self._get_cfg(CONF_CHARGE_MARGIN_W, DEFAULT_CHARGE_MARGIN_W)),
            discharge_margin_w=float(self._get_cfg(CONF_DISCHARGE_MARGIN_W, DEFAULT_DISCHARGE_MARGIN_W)),
            cheap_hours=int(self._get_cfg(CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS)),
            expensive_hours=int(self._get_cfg(CONF_EXPENSIVE_HOURS, DEFAULT_EXPENSIVE_HOURS)),
            min_spread_pct=float(self._get_cfg(CONF_MIN_SPREAD_PCT, DEFAULT_MIN_SPREAD_PCT)),
            manual_power_w=float(self._get_cfg(CONF_MANUAL_POWER_W, DEFAULT_MANUAL_POWER_W)),
        )

    # --- Sensor reading helpers ---

    def get_p1_override(self) -> float | None:
        """Return override P1 value if set (non-zero number entity), else None."""
        entity_id = f"number.{DOMAIN}_p1_testwaarde"
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unavailable", "unknown"):
            try:
                val = float(state.state)
                if val != 0.0:
                    return val
            except ValueError:
                pass
        return None

    def _read_p1(self) -> float:
        # Check for test override first
        override = self.get_p1_override()
        if override is not None:
            self.p1_direction = "TEST"
            return override

        entity_id: str = self._get_cfg(CONF_P1_SENSOR, "")
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            _LOGGER.warning("P1 sensor '%s' unavailable", entity_id)
            return 0.0
        try:
            value = float(state.state)
        except ValueError:
            return 0.0

        if self._get_cfg(CONF_INVERT_P1_SIGN, False):
            value = -value

        # Store human-readable direction (accessed by status sensor)
        if value > 50:
            self.p1_direction = "verbruik"
        elif value < -50:
            self.p1_direction = "teruglevering"
        else:
            self.p1_direction = "balans"

        return value

    def _read_prices(self) -> tuple[float, list]:
        entity_id: str = self._get_cfg(CONF_PRICE_SENSOR, "")
        attribute: str = self._get_cfg(CONF_PRICE_ATTRIBUTE, DEFAULT_PRICE_ATTRIBUTE)
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            _LOGGER.warning("Price sensor '%s' unavailable", entity_id)
            return 0.0, []
        try:
            current_price = float(state.state)
        except ValueError:
            current_price = 0.0
        prices_today = state.attributes.get(attribute, [])
        return current_price, (prices_today if isinstance(prices_today, list) else [])

    def _read_soc_values(self) -> Dict[str, float]:
        """Read SoC from configured entities for each device."""
        result: Dict[str, float] = {}
        for device_id, entity_id in self._soc_entities.items():
            if not entity_id:
                continue
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unavailable", "unknown", ""):
                try:
                    result[device_id] = float(state.state)
                except ValueError:
                    pass
        return result

    # --- Device / entity factory ---

    def _build_soc_entity_map(self) -> Dict[str, str]:
        """Map device_id → SoC entity_id (empty string if not configured)."""
        result: Dict[str, str] = {}
        if self._get_cfg(CONF_MARSTEK_ENABLED):
            device_id = self._get_cfg(CONF_MARSTEK_DEVICE_ID, "")
            result[device_id] = self._get_cfg(CONF_MARSTEK_SOC_ENTITY, "")
        if self._get_cfg(CONF_ZENDURE_ENABLED):
            charge_entity = self._get_cfg(CONF_ZENDURE_CHARGE_LIMIT_ENTITY, "")
            result[charge_entity] = self._get_cfg(CONF_ZENDURE_SOC_ENTITY, "")
        return result

    def _build_devices(self) -> List[BatteryDevice]:
        devices: List[BatteryDevice] = []
        if self._get_cfg(CONF_MARSTEK_ENABLED):
            device_id = self._get_cfg(CONF_MARSTEK_DEVICE_ID, "")
            devices.append(MarstekDevice(self.hass, device_id))
            _LOGGER.info("HEMS: Marstek Venus E added (device_id=%s)", device_id)
        if self._get_cfg(CONF_ZENDURE_ENABLED):
            devices.append(ZendureDevice(
                hass=self.hass,
                name=self._get_cfg(CONF_ZENDURE_NAME, "Zendure"),
                charge_limit_entity=self._get_cfg(CONF_ZENDURE_CHARGE_LIMIT_ENTITY, ""),
                discharge_limit_entity=self._get_cfg(CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY, ""),
            ))
            _LOGGER.info("HEMS: Zendure '%s' added", self._get_cfg(CONF_ZENDURE_NAME))
        if not devices:
            _LOGGER.warning("HEMS: no devices configured")
        return devices

    # --- Config helper ---

    def _get_cfg(self, key: str, default=None):
        """Read from options first, then data, then default."""
        return self._options.get(key, self._config.get(key, default))
