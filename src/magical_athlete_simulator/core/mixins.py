from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import (
        GameEvent,
        MoveDistanceQuery,
        Phase,
    )
    from magical_athlete_simulator.engine.game_engine import GameEngine


class RollModificationMixin(ABC):
    """Mixin for modifiers that alter dice rolls."""

    @abstractmethod
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> None:
        pass

    @abstractmethod
    def send_ability_trigger(
        self,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> None:
        pass


class ApproachHookMixin(ABC):
    """Allows a modifier to redirect incoming racers (e.g., Huge Baby blocking)."""

    @abstractmethod
    def on_approach(
        self,
        target: int,
        moving_racer_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        pass


class LandingHookMixin(ABC):
    """Allows a modifier to react when a racer stops on the tile (e.g., Trip, VP)."""

    @abstractmethod
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        pass


class LifecycleManagedMixin(ABC):
    @staticmethod
    @abstractmethod
    def on_gain(engine: GameEngine, owner_idx: int) -> None:
        pass

    @staticmethod
    @abstractmethod
    def on_loss(engine: GameEngine, owner_idx: int) -> None:
        pass


class DestinationCalculatorMixin(ABC):
    """Allows a modifier to override the standard 'start + distance' math."""

    @abstractmethod
    def calculate_destination(
        self, engine: GameEngine, racer_idx: int, start_tile: int, distance: int
    ) -> int:
        pass


class MovementValidatorMixin(ABC):
    """Allows a modifier to veto a move based on its projected destination."""

    @abstractmethod
    def validate_move(
        self, engine: GameEngine, racer_idx: int, start_tile: int, end_tile: int
    ) -> bool:
        pass
