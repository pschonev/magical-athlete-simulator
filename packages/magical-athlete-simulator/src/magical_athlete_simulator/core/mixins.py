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
    ) -> None:
        pass


class ApproachHookMixin(ABC):
    """Allows a modifier to redirect incoming racers (e.g., Huge Baby blocking)."""

    @abstractmethod
    def on_approach(
        self,
        target: int,
        modifier_owner_idx: int,
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
