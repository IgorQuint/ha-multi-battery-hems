"""
NOM — Nul op de Meter strategy.
/ NOM — Nul-op-de-Meter strategie.

Goal: keep net grid import/export at (or near) zero at all times.
  grid_power > 0  →  consuming from grid  →  discharge batteries
  grid_power < 0  →  returning to grid    →  charge batteries

Power is distributed evenly across all available devices, clamped
to each device's individual limits.

/ Doel: netto netverbruik/-teruglevering altijd op (of nabij) nul houden.
  grid_power > 0  →  verbruik uit net     →  ontlaad batterijen
  grid_power < 0  →  teruglevering aan net →  laad batterijen

Vermogen wordt gelijk verdeeld over alle beschikbare apparaten,
begrensd tot de individuele limieten van elk apparaat.
"""
from __future__ import annotations

import logging

from .base import BaseStrategy, StrategyContext

_LOGGER = logging.getLogger(__name__)


class NomStrategy(BaseStrategy):
    """Nul op de Meter (NOM) strategy."""

    @property
    def name(self) -> str:
        return "nom"

    @property
    def friendly_name(self) -> str:
        return "Nul op de Meter (NOM)"

    async def execute(self, context: StrategyContext) -> None:
        devices = context.devices
        if not devices:
            return

        grid_w = context.grid_power_w
        # Target per device: negate grid power and split evenly
        # / Doel per apparaat: negeer netvermogen en verdeel gelijkmatig
        target_per_device = -grid_w / len(devices)

        for device in devices:
            if target_per_device >= 0:
                power_w = min(target_per_device, device.max_charge_power_w)
            else:
                power_w = max(target_per_device, -device.max_discharge_power_w)

            _LOGGER.debug(
                "NOM: grid=%.0fW → %s target=%.0fW clamped=%.0fW",
                grid_w, device.name, target_per_device, power_w,
            )
            await device.set_charge(power_w)
