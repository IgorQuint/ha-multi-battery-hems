"""
Constants for Multi Battery HEMS.
/ Constanten voor Multi Battery HEMS.
"""

DOMAIN = "multi_battery_hems"
MANUFACTURER = "Multi Battery HEMS"
VERSION = "0.1.0"

# --- Strategies / Strategieën ---
STRATEGY_STANDBY = "standby"
STRATEGY_NOM = "nom"
STRATEGY_DYNAMIC_NOM = "dynamic_nom"
STRATEGY_ARBITRAGE = "arbitrage"

STRATEGIES = [STRATEGY_STANDBY, STRATEGY_NOM, STRATEGY_DYNAMIC_NOM, STRATEGY_ARBITRAGE]

STRATEGY_FRIENDLY_NAMES = {
    STRATEGY_STANDBY: "Standby",
    STRATEGY_NOM: "Nul op de Meter (NOM)",
    STRATEGY_DYNAMIC_NOM: "Dynamisch NOM",
    STRATEGY_ARBITRAGE: "Arbitrage",
}

# --- Config entry keys ---
CONF_STRATEGY = "strategy"
CONF_P1_SENSOR = "p1_sensor"
CONF_PRICE_SENSOR = "price_sensor"
CONF_PRICE_ATTRIBUTE = "price_attribute"

CONF_MARSTEK_ENABLED = "marstek_enabled"
CONF_MARSTEK_DEVICE_ID = "marstek_device_id"

CONF_ZENDURE_ENABLED = "zendure_enabled"
CONF_ZENDURE_NAME = "zendure_name"
CONF_ZENDURE_CHARGE_LIMIT_ENTITY = "zendure_charge_limit_entity"
CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY = "zendure_discharge_limit_entity"

# --- Default values ---
DEFAULT_STRATEGY = STRATEGY_NOM
DEFAULT_P1_SENSOR = ""
DEFAULT_PRICE_SENSOR = ""
DEFAULT_PRICE_ATTRIBUTE = "prices_today"
DEFAULT_MARSTEK_DEVICE_ID = ""
DEFAULT_ZENDURE_NAME = "SolarFlow"
DEFAULT_ZENDURE_CHARGE_LIMIT = ""
DEFAULT_ZENDURE_DISCHARGE_LIMIT = ""

# --- Update interval ---
UPDATE_INTERVAL_SECONDS = 60

# --- Marstek device limits ---
MARSTEK_MIN_POWER_W = -2500   # Discharge to grid (negative = feed-in)
MARSTEK_MAX_POWER_W = 800     # Charge from grid/solar
MARSTEK_DURATION_SECONDS = 120  # Command validity window; refreshed each cycle

# --- Zendure device limits ---
ZENDURE_MAX_CHARGE_W = 1000
ZENDURE_MAX_DISCHARGE_W = 800

# --- Financial tracking periods ---
PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"
PERIOD_YEARLY = "yearly"

PERIODS = [PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY, PERIOD_YEARLY]

# --- Persistent storage ---
STORAGE_KEY = f"{DOMAIN}_financial"
STORAGE_VERSION = 1

# --- Sensor keys ---
# Used to build entity_id and friendly_name
SENSOR_KWH_CHARGED_TOTAL = "kwh_charged_total"
SENSOR_KWH_DISCHARGED_TOTAL = "kwh_discharged_total"
SENSOR_KWH_CHARGED = "kwh_charged_{period}"
SENSOR_KWH_DISCHARGED = "kwh_discharged_{period}"
SENSOR_PROFIT = "profit_{period}"

# Combined device name (pseudo-device for aggregate sensors)
COMBINED_DEVICE_ID = "combined"
COMBINED_DEVICE_NAME = "Gecombineerd"
