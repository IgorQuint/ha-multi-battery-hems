# Multi Battery HEMS

**Home Energy Management System for Home Assistant — control multiple batteries from different brands simultaneously.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-ha--multi--battery--hems-181717?logo=github)](https://github.com/multi-battery-hems/ha-multi-battery-hems)

---

## What is Multi Battery HEMS?

Most battery systems only control a single device. Multi Battery HEMS is a Home Assistant custom integration that orchestrates **multiple batteries from different brands** as a single unified system — using smart, configurable energy strategies to minimise your electricity bill.

It reads your real-time grid import/export (P1 meter) and today's dynamic electricity prices, then commands all your batteries accordingly — every 60 seconds.

### Key features

- **Multi-device**: control Marstek, Zendure, and more — simultaneously
- **4 strategies**: Standby, Zero-Import (NOM), Dynamic NOM, Arbitrage
- **Live strategy switching**: change strategy from your dashboard without restart
- **Financial tracking**: profit per device and combined — daily, weekly, monthly, yearly
- **HACS compatible**: install in one click via the HACS custom repository
- **Modular architecture**: add new battery brands or strategies with minimal code

---

## Supported devices

| Brand | Model | Control method |
|---|---|---|
| Marstek | Venus E (5.12 kWh) | `marstek_local_api.set_passive_mode` service |
| Zendure | SolarFlow 800 Plus | `number` entities (charge/discharge limit) |

> **Roadmap**: second Zendure 800 Plus, Zendure 800 Pro with PV panels, and more brands via the extensible device driver model.

---

## Strategies

### 1. Standby
All batteries are disabled. No charging or discharging takes place. Useful when you want full manual control or during maintenance.

### 2. NOM — Zero Import/Export (Nul op de Meter)
The system continuously tries to keep your net grid power at exactly zero:
- **Grid consumption detected** → batteries discharge to cover the load
- **Grid export detected** (surplus solar) → batteries charge to absorb the surplus

Power is distributed evenly across all active devices, clamped to each device's individual limits.

### 3. Dynamic NOM
Identical to NOM but overlays time-of-use price intelligence:
- **Cheap hour** (< 85% of today's day-average price) → charges extra on top of NOM, even without solar surplus
- **Expensive hour** (> 115% of today's day-average price) → discharges extra on top of NOM, even without grid consumption
- **Normal hour** → pure NOM behaviour

Extra power in cheap/expensive hours is 50% of total combined device capacity. Thresholds and fractions are tunable in `strategies/dynamic_nom.py`.

### 4. Arbitrage
Pure price-based charging and discharging, ignoring real-time grid power:
- **3 cheapest hours** of today → charge all batteries at maximum power
- **4 most expensive hours** of today → discharge all batteries at maximum power
- **All other hours** → standby

The thresholds are derived from today's full price list on every cycle, so the strategy self-adapts as new price data arrives during the day.

---

## Financial tracking

For every configured battery (and a combined total) the integration tracks:

| Metric | Reset |
|---|---|
| Total kWh charged (lifetime) | Never |
| Total kWh discharged (lifetime) | Never |
| kWh charged / discharged — daily | Every day at midnight |
| kWh charged / discharged — weekly | Every Monday |
| kWh charged / discharged — monthly | 1st of each month |
| kWh charged / discharged — yearly | 1st of January |
| Profit — daily / weekly / monthly / yearly | Same as above |

**Profit** = revenue from discharging − cost of charging, calculated using the actual spot price at the time of each operation.

Energy is estimated from the commanded power setpoint × cycle duration (60 seconds). All data is persisted to Home Assistant's built-in storage so it survives restarts.

---

## Sensors created

After installation the following entities are available:

### System sensors
| Entity | Description |
|---|---|
| `sensor.multi_battery_hems_netvermogen` | Live grid power from P1 meter (W) |
| `sensor.multi_battery_hems_actuele_stroomprijs` | Current electricity price (€/kWh) |

### Per device + combined (example: Marstek Venus E)
| Entity | Description |
|---|---|
| `sensor.multi_battery_hems_marstek_venus_e_totaal_geladen` | Lifetime kWh charged |
| `sensor.multi_battery_hems_marstek_venus_e_totaal_ontladen` | Lifetime kWh discharged |
| `sensor.multi_battery_hems_marstek_venus_e_dag_geladen` | Today's kWh charged |
| `sensor.multi_battery_hems_marstek_venus_e_dagwinst` | Today's profit (€) |
| `sensor.multi_battery_hems_marstek_venus_e_weekwinst` | This week's profit (€) |
| `sensor.multi_battery_hems_marstek_venus_e_maandwinst` | This month's profit (€) |
| `sensor.multi_battery_hems_marstek_venus_e_jaarwinst` | This year's profit (€) |
| *(and identical sensors for each other device and for `gecombineerd`)* | |

### Strategy selector
| Entity | Description |
|---|---|
| `select.multi_battery_hems_actieve_strategie` | Change the active strategy live from the dashboard |

---

## Requirements

- Home Assistant 2024.1 or newer
- [HACS](https://hacs.xyz) (for easy installation)
- A working P1 meter sensor reporting grid power in watts — positive = consuming, negative = returning
- A dynamic electricity price sensor with a `prices_today` attribute containing `[{time, price}, ...]` (compatible with e.g. Enever, Tibber, ENTSO-E integrations)

### Per device
| Device | Prerequisite integration |
|---|---|
| Marstek Venus E | [marstek_local_api](https://github.com/) installed and working |
| Zendure SolarFlow | Zendure HA integration with `number` entities for charge/discharge limits |

---

## Installation

### Via HACS (recommended)

1. Open **HACS** in Home Assistant
2. Click the three dots (top right) → **Custom repositories**
3. Enter `multi-battery-hems/ha-multi-battery-hems`, category: **Integration**
4. Click **Add**, then find "Multi Battery HEMS" and click **Download**
5. Restart Home Assistant
6. Go to **Settings → Integrations → Add Integration** → search for **Multi Battery HEMS**

### Manual installation

1. Download or clone this repository
2. Copy `custom_components/multi_battery_hems/` to your HA config directory:
   ```
   /config/custom_components/multi_battery_hems/
   ```
3. Restart Home Assistant
4. Go to **Settings → Integrations → Add Integration** → search for **Multi Battery HEMS**

---

## Configuration

The integration is configured entirely through the Home Assistant UI in four steps:

**Step 1 — General**
- P1 meter sensor entity ID (e.g. `sensor.p1_meter_power`)
- Electricity price sensor entity ID (e.g. `sensor.electricity_price_today`)
- Price attribute name (default: `prices_today`)
- Default strategy

**Step 2 — Devices**
- Toggle which battery brands are present in your setup

**Step 3 — Marstek** *(if enabled)*
- Device ID from the marstek_local_api integration

**Step 4 — Zendure** *(if enabled)*
- Device name
- Charge limit entity ID (e.g. `number.solarflow_charge_limit`)
- Discharge limit entity ID (e.g. `number.solarflow_discharge_limit`)

### Changing strategy after setup
Go to **Settings → Integrations → Multi Battery HEMS → Configure**, or simply use the `select.multi_battery_hems_actieve_strategie` entity on your dashboard.

---

## Architecture

```
custom_components/multi_battery_hems/
├── __init__.py          Integration setup and teardown
├── manifest.json        HACS/HA manifest
├── const.py             All constants in one place
├── config_flow.py       UI configuration wizard + options flow
├── coordinator.py       60-second control loop (reads sensors, runs strategy, tracks finances)
├── sensor.py            All sensor entities
├── select.py            Strategy selector entity
│
├── devices/             Battery device drivers
│   ├── base.py          Abstract BatteryDevice interface
│   ├── marstek.py       Marstek Venus E driver
│   └── zendure.py       Zendure SolarFlow driver
│
├── strategies/          Energy management strategies
│   ├── base.py          Abstract BaseStrategy + StrategyContext
│   ├── standby.py       Standby
│   ├── nom.py           Zero import/export (NOM)
│   ├── dynamic_nom.py   NOM + time-of-use pricing
│   └── arbitrage.py     Charge cheap / discharge expensive
│
├── financial/
│   └── tracker.py       kWh + EUR tracking with auto period resets
│
└── translations/
    ├── nl.json           Dutch UI strings
    └── en.json           English UI strings
```

### Control loop

Every 60 seconds the coordinator:
1. Reads the P1 meter (grid power in watts)
2. Reads the current electricity price and today's full price list
3. Instantiates the active strategy and calls `execute(context)`
4. Each strategy commands every device via the `BatteryDevice.set_charge(power_w)` interface
5. Updates the financial tracker for each device
6. Persists financial data to HA storage

### Adding a new battery brand

1. Create `devices/mybrand.py` — subclass `BatteryDevice` and implement `set_charge()`, `set_standby()`, `get_state()`, `max_charge_power_w`, `max_discharge_power_w`
2. Add a configuration step in `config_flow.py`
3. Register the device in `coordinator.py` → `_build_devices()`

### Adding a new strategy

1. Create `strategies/mystrategy.py` — subclass `BaseStrategy` and implement `execute(context)`
2. Add it to `STRATEGY_MAP` in `strategies/__init__.py`

That's it — the UI selector, coordinator, and financial tracker pick it up automatically.

---

## Roadmap

- [ ] Second Zendure 800 Plus support
- [ ] Zendure 800 Pro with PV panel integration
- [ ] SoC-aware strategies (stop charging at X%, stop discharging at Y%)
- [ ] Real energy sensor integration (instead of setpoint estimation)
- [ ] Forecast-based strategies using solar/consumption predictions
- [ ] Multi-instance support (multiple HEMS setups)
- [ ] Platform abstraction layer for Homey and other smart home systems

---

## Contributing

Pull requests are welcome. For major changes please open an issue first to discuss the approach.

When adding a new device driver or strategy, follow the existing patterns in `devices/` and `strategies/` respectively — the abstract base classes define the required interface.

---

## License

MIT — see [LICENSE](LICENSE) for details.
