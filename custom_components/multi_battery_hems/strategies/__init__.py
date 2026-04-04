"""
Strategy registry for Multi Battery HEMS.
/ Strategie-register voor Multi Battery HEMS.

Add new strategies by:
1. Creating a file in this directory
2. Subclassing BaseStrategy
3. Adding one entry to STRATEGY_MAP below

/ Voeg nieuwe strategieën toe door:
1. Een bestand in deze map aan te maken
2. Een subklasse van BaseStrategy te maken
3. Één invoer toe te voegen aan STRATEGY_MAP hieronder
"""
from .base import BaseStrategy, StrategyContext, calculate_spread
from .standby import StandbyStrategy
from .nom import NomStrategy
from .dynamic_nom import DynamicNomStrategy
from .arbitrage import ArbitrageStrategy
from .manual import ManualStrategy
from .fast_charge import FastChargeStrategy
from .fast_discharge import FastDischargeStrategy
from .smart_charge_only import SmartChargeOnlyStrategy
from .smart_discharge_only import SmartDischargeOnlyStrategy

STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "standby":               StandbyStrategy,
    "nom":                   NomStrategy,
    "dynamic_nom":           DynamicNomStrategy,
    "arbitrage":             ArbitrageStrategy,
    "manual":                ManualStrategy,
    "fast_charge":           FastChargeStrategy,
    "fast_discharge":        FastDischargeStrategy,
    "smart_charge_only":     SmartChargeOnlyStrategy,
    "smart_discharge_only":  SmartDischargeOnlyStrategy,
}

__all__ = [
    "BaseStrategy", "StrategyContext", "calculate_spread",
    "StandbyStrategy", "NomStrategy", "DynamicNomStrategy", "ArbitrageStrategy",
    "ManualStrategy", "FastChargeStrategy", "FastDischargeStrategy",
    "SmartChargeOnlyStrategy", "SmartDischargeOnlyStrategy",
    "STRATEGY_MAP",
]
