"""Modelos de dominio puros: sin pandas, sin I/O, sin Streamlit.

Representan el concepto de "objetivo" y "progreso hacia un objetivo",
independientemente de qué métrica de Polar lo alimente.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GoalDirection(str, Enum):
    """Sentido en que el valor actual debe moverse para cumplir el objetivo."""

    AT_LEAST = "at_least"  # el valor actual debe ser >= target (pasos, km, sueño)
    AT_MOST = "at_most"  # el valor actual debe ser <= target (peso)


@dataclass(frozen=True)
class Goal:
    """Objetivo configurado por el usuario para una métrica concreta."""

    name: str
    target: float
    direction: GoalDirection
    unit: str
    baseline: float | None = None  # valor de partida, necesario para progress_ratio en AT_MOST


@dataclass(frozen=True)
class ProgressSnapshot:
    """Comparación entre el valor actual de una métrica y su objetivo."""

    goal: Goal
    current: float | None

    @property
    def delta(self) -> float | None:
        """Diferencia actual - objetivo (negativo en AT_MOST significa ya superado)."""
        if self.current is None:
            return None
        return self.current - self.goal.target

    @property
    def on_track(self) -> bool | None:
        if self.current is None:
            return None
        if self.goal.direction is GoalDirection.AT_LEAST:
            return self.current >= self.goal.target
        return self.current <= self.goal.target

    @property
    def progress_ratio(self) -> float | None:
        """Fracción (0..1+) del objetivo alcanzada.

        Para AT_LEAST es directo (actual/objetivo). Para AT_MOST (p.ej. peso)
        requiere un baseline de partida: sin saber de dónde se partió, "peso
        actual <= objetivo" no dice cuánto del camino se ha recorrido.
        """
        if self.current is None:
            return None
        if self.goal.direction is GoalDirection.AT_LEAST:
            return self.current / self.goal.target if self.goal.target else None
        if self.goal.baseline is None or self.goal.baseline == self.goal.target:
            return None
        return (self.goal.baseline - self.current) / (self.goal.baseline - self.goal.target)
