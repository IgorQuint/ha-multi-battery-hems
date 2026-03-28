"""
Strategy registry for Multi Battery HEMS.
/ Strategie-register voor Multi Battery HEMS.
"""
from .base import BaseStrategy, StrategyContext
from .standby import StandbyStrategy
from .nom import NomStrategy
from .dynamic_nom import DynamicNomStrategy
from .arbitrage import ArbitrageStrategy

# Maps strategy identifier → class
# Add new strategies here to make them available in the UI.
# / Voeg nieuwe strategieën hier toe om ze beschikbaar te maken in de UI.
STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "standby": StandbyStrategy,
    "nom": NomStrategy,
    "dynamic_nom": DynamicNomStrategy,
    "arbitrage": ArbitrageStrategy,
}

__all__ = [
    "BaseStrategy",
    "StrategyContext",
    "StandbyStrategy",
    "NomStrategy",
    "DynamicNomStrategy",
    "ArbitrageStrategy",
    "STRATEGY_MAP",
]
