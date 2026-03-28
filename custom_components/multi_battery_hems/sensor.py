"""
Sensor platform for Multi Battery HEMS.
/ Sensorplatform voor Multi Battery HEMS.

Creates the following sensors per device (and combined):
  • Total kWh charged / discharged (lifetime)
  • kWh charged / discharged per period (daily / weekly / monthly / yearly)
  • Profit per period in EUR (daily / weekly / monthly / yearly)

Also creates:
  • sensor.multi_battery_hems_grid_power  — live P1 reading
  • sensor.multi_battery_hems_current_price — live electricity price

/ Maakt de volgende sensoren per apparaat (en gecombineerd):
  • Totaal kWh geladen / ontladen (levensduur)
  • kWh geladen / ontladen per periode (dag / week / maand / jaar)
  • Winst per periode in EUR (dag / week / maand / jaar)

Maakt ook:
  • sensor.multi_battery_hems_grid_power  — live P1-meting
  • sensor.multi_battery_hems_current_price — live elektriciteitsprijs
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    COMBINED_DEVICE_ID,
    COMBINED_DEVICE_NAME,
    PERIOD_DAILY,
    PERIOD_WEEKLY,
    PERIOD_MONTHLY,
    PERIOD_YEARLY,
)
from .coordinator import HemsCoordinator
from .financial.tracker import DeviceFinancials

_LOGGER = logging.getLogger(__name__)

PERIODS = [PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY, PERIOD_YEARLY]
PERIOD_LABELS = {
    PERIOD_DAILY: "Dag",
    PERIOD_WEEKLY: "Week",
    PERIOD_MONTHLY: "Maand",
    PERIOD_YEARLY: "Jaar",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: HemsCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        HemsGridPowerSensor(coordinator, entry),
        HemsPriceSensor(coordinator, entry),
    ]

    # Sensors per physical device
    for device in coordinator.devices:
        entities.extend(_device_sensors(coordinator, entry, device.device_id, device.name))

    # Combined sensors
    entities.extend(
        _device_sensors(coordinator, entry, COMBINED_DEVICE_ID, COMBINED_DEVICE_NAME)
    )

    async_add_entities(entities)


def _device_sensors(
    coordinator: HemsCoordinator,
    entry: ConfigEntry,
    device_id: str,
    device_name: str,
) -> list[SensorEntity]:
    """Build all financial sensors for one device (or combined)."""
    sensors: list[SensorEntity] = [
        HemsEnergySensor(
            coordinator, entry, device_id, device_name,
            key="total_kwh_charged",
            label=f"{device_name} — Totaal geladen",
            getter=lambda fin: fin.total_kwh_charged,
        ),
        HemsEnergySensor(
            coordinator, entry, device_id, device_name,
            key="total_kwh_discharged",
            label=f"{device_name} — Totaal ontladen",
            getter=lambda fin: fin.total_kwh_discharged,
        ),
    ]

    for period in PERIODS:
        plabel = PERIOD_LABELS[period]
        sensors += [
            HemsEnergySensor(
                coordinator, entry, device_id, device_name,
                key=f"{period}_kwh_charged",
                label=f"{device_name} — {plabel} geladen",
                getter=lambda fin, p=period: getattr(fin, p).kwh_charged,
            ),
            HemsEnergySensor(
                coordinator, entry, device_id, device_name,
                key=f"{period}_kwh_discharged",
                label=f"{device_name} — {plabel} ontladen",
                getter=lambda fin, p=period: getattr(fin, p).kwh_discharged,
            ),
            HemsProfitSensor(
                coordinator, entry, device_id, device_name,
                key=f"{period}_profit",
                label=f"{device_name} — {plabel}winst",
                getter=lambda fin, p=period: getattr(fin, p).profit_eur,
            ),
        ]

    return sensors


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class HemsBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor tied to the HEMS coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HemsCoordinator,
        entry: ConfigEntry,
        unique_suffix: str,
        friendly_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = friendly_name
        self._entry = entry


# ---------------------------------------------------------------------------
# System sensors
# ---------------------------------------------------------------------------


class HemsGridPowerSensor(HemsBaseSensor):
    """Live grid power from P1 meter (positive = consuming, negative = returning)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: HemsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "grid_power", "Netvermogen")

    @property
    def native_value(self) -> float:
        return self.coordinator.grid_power_w


class HemsPriceSensor(HemsBaseSensor):
    """Current electricity price in EUR/kWh."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"

    def __init__(self, coordinator: HemsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current_price", "Actuele stroomprijs")

    @property
    def native_value(self) -> float:
        return round(self.coordinator.current_price_eur, 5)


# ---------------------------------------------------------------------------
# Financial sensors
# ---------------------------------------------------------------------------


class HemsEnergySensor(HemsBaseSensor):
    """kWh sensor backed by the financial tracker."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: HemsCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        key: str,
        label: str,
        getter: Callable[[DeviceFinancials], float],
    ) -> None:
        super().__init__(coordinator, entry, f"{device_id}_{key}", label)
        self._device_id = device_id
        self._getter = getter

    @property
    def native_value(self) -> float:
        fin = self.coordinator.tracker.get(self._device_id)
        return round(self._getter(fin), 4)


class HemsProfitSensor(HemsBaseSensor):
    """EUR profit sensor backed by the financial tracker."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash-plus"

    def __init__(
        self,
        coordinator: HemsCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        key: str,
        label: str,
        getter: Callable[[DeviceFinancials], float],
    ) -> None:
        super().__init__(coordinator, entry, f"{device_id}_{key}", label)
        self._device_id = device_id
        self._getter = getter

    @property
    def native_value(self) -> float:
        fin = self.coordinator.tracker.get(self._device_id)
        return round(self._getter(fin), 4)
