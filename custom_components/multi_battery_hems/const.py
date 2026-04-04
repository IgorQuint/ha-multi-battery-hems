"""
Constants for Multi Battery HEMS.
/ Constanten voor Multi Battery HEMS.
"""

DOMAIN = "multi_battery_hems"
MANUFACTURER = "Multi Battery HEMS"
VERSION = "0.3"

# --- Strategies / Strategieën ---
STRATEGY_STANDBY = "standby"
STRATEGY_NOM = "nom"
STRATEGY_DYNAMIC_NOM = "dynamic_nom"
STRATEGY_ARBITRAGE = "arbitrage"
STRATEGY_MANUAL = "manual"
STRATEGY_FAST_CHARGE = "fast_charge"
STRATEGY_FAST_DISCHARGE = "fast_discharge"
STRATEGY_SMART_CHARGE_ONLY = "smart_charge_only"
STRATEGY_SMART_DISCHARGE_ONLY = "smart_discharge_only"

STRATEGIES = [
    STRATEGY_STANDBY,
    STRATEGY_NOM,
    STRATEGY_DYNAMIC_NOM,
    STRATEGY_ARBITRAGE,
    STRATEGY_MANUAL,
    STRATEGY_FAST_CHARGE,
    STRATEGY_FAST_DISCHARGE,
    STRATEGY_SMART_CHARGE_ONLY,
    STRATEGY_SMART_DISCHARGE_ONLY,
]

STRATEGY_FRIENDLY_NAMES = {
    STRATEGY_STANDBY:            "Standby",
    STRATEGY_NOM:                "Nul op de Meter (NOM)",
    STRATEGY_DYNAMIC_NOM:        "Dynamisch NOM",
    STRATEGY_ARBITRAGE:          "Arbitrage",
    STRATEGY_MANUAL:             "Handmatig",
    STRATEGY_FAST_CHARGE:        "Snel laden",
    STRATEGY_FAST_DISCHARGE:     "Snel ontladen",
    STRATEGY_SMART_CHARGE_ONLY:  "Alleen laden",
    STRATEGY_SMART_DISCHARGE_ONLY: "Alleen ontladen",
}

# Sign inversion options (for debugging inverted behavior)
CONF_INVERT_P1_SIGN = "invert_p1_sign"
CONF_INVERT_MARSTEK_SIGN = "invert_marstek_sign"

# --- Config entry keys ---
CONF_STRATEGY = "strategy"
CONF_P1_SENSOR = "p1_sensor"
CONF_PRICE_SENSOR = "price_sensor"
CONF_PRICE_ATTRIBUTE = "price_attribute"

CONF_MARSTEK_ENABLED = "marstek_enabled"
CONF_MARSTEK_DEVICE_ID = "marstek_device_id"
CONF_MARSTEK_SOC_ENTITY = "marstek_soc_entity"

CONF_ZENDURE_ENABLED = "zendure_enabled"
CONF_ZENDURE_NAME = "zendure_name"
CONF_ZENDURE_CHARGE_LIMIT_ENTITY = "zendure_charge_limit_entity"
CONF_ZENDURE_DISCHARGE_LIMIT_ENTITY = "zendure_discharge_limit_entity"
CONF_ZENDURE_SOC_ENTITY = "zendure_soc_entity"

# SoC protection (inspired by Gielz/zenSDK)
# / SoC-bescherming (geïnspireerd door Gielz/zenSDK)
CONF_MIN_SOC_PCT = "min_soc_pct"
CONF_MAX_SOC_PCT = "max_soc_pct"

# NOM hysteresis margins (prevent relay chatter)
# / NOM-hysteresismarges (voorkomt relay-gezwabber)
CONF_CHARGE_MARGIN_W = "charge_margin_w"
CONF_DISCHARGE_MARGIN_W = "discharge_margin_w"

# Dynamic period selection
# / Dynamische periodeselect
CONF_CHEAP_HOURS = "cheap_hours"
CONF_EXPENSIVE_HOURS = "expensive_hours"

# Minimum price spread for arbitrage to activate
# / Minimale prijsspread voor activering van arbitrage
CONF_MIN_SPREAD_PCT = "min_spread_pct"

# Manual strategy: user-defined power setpoint
# / Handmatige strategie: door gebruiker ingesteld vermogensssetpoint
CONF_MANUAL_POWER_W = "manual_power_w"

# --- Default values ---
DEFAULT_STRATEGY = STRATEGY_NOM
DEFAULT_P1_SENSOR = ""
DEFAULT_PRICE_SENSOR = ""
DEFAULT_PRICE_ATTRIBUTE = "prices_today"
DEFAULT_MARSTEK_DEVICE_ID = ""
DEFAULT_ZENDURE_NAME = "SolarFlow"
DEFAULT_ZENDURE_CHARGE_LIMIT = ""
DEFAULT_ZENDURE_DISCHARGE_LIMIT = ""

DEFAULT_MIN_SOC_PCT = 10.0    # %  — force-charge below this SoC
DEFAULT_MAX_SOC_PCT = 95.0    # %  — stop charging above this SoC
DEFAULT_CHARGE_MARGIN_W = 50  # W  — hysteresis to prevent charging flip-flop
DEFAULT_DISCHARGE_MARGIN_W = 5  # W — hysteresis for discharging
DEFAULT_CHEAP_HOURS = 3        # Number of cheapest hours to use
DEFAULT_EXPENSIVE_HOURS = 4    # Number of most expensive hours to use
DEFAULT_MIN_SPREAD_PCT = 10.0  # %  — minimum spread to justify arbitrage
DEFAULT_MANUAL_POWER_W = 0     # W  — manual power setpoint (+ charge, - discharge)

# --- Update interval ---
UPDATE_INTERVAL_SECONDS = 60

# --- NOM control thresholds (from Gielz analysis) ---
# Only start discharging when grid consumption exceeds this value
# / Pas ontladen wanneer netverbruik boven deze waarde komt
NOM_DISCHARGE_THRESHOLD_W = 100
# Only start charging when grid export exceeds this value (as positive number)
# / Pas laden wanneer netto teruglevering boven deze waarde komt
NOM_CHARGE_THRESHOLD_W = 300
# Initial ramp factor when first activating charge/discharge (prevents overshoot)
# / Initiële ramp-factor bij eerste activering (voorkomt overschieten)
NOM_RAMP_FACTOR = 0.75

# Force-charge power when SoC drops below minimum
# / Verplicht laadvermogen wanneer SoC onder minimum zakt
SOC_PROTECTION_CHARGE_W = 1200

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
SENSOR_KWH_CHARGED_TOTAL = "kwh_charged_total"
SENSOR_KWH_DISCHARGED_TOTAL = "kwh_discharged_total"
SENSOR_KWH_CHARGED = "kwh_charged_{period}"
SENSOR_KWH_DISCHARGED = "kwh_discharged_{period}"
SENSOR_PROFIT = "profit_{period}"

# Combined device name (pseudo-device for aggregate sensors)
COMBINED_DEVICE_ID = "combined"
COMBINED_DEVICE_NAME = "Gecombineerd"
