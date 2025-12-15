from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, override

from magical_athlete_simulator.core.events import MoveDistanceQuery
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class Modifier(ABC):
    """Base class for all persistent effects."""

    owner_idx: int | None
    name: ClassVar[AbilityName | str]

    @property
    def display_name(self) -> str:  # instance-level, can be dynamic
        return self.name

    # Equality check for safe add/remove
    @override
    def __eq__(self, other: object):
        if not isinstance(other, Modifier):
            return NotImplemented
        return self.name == other.name and self.owner_idx == other.owner_idx

    @override
    def __hash__(self):
        return hash((self.name, self.owner_idx))


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
    def on_approach(self, target: int, mover_idx: int, engine: "GameEngine") -> int:
        pass


class LandingHookMixin(ABC):
    """Allows a modifier to react when a racer stops on the tile (e.g., Trip, VP)."""

    @abstractmethod
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: GameEngine,
    ) -> None:
        pass


@dataclass(eq=False)
class SpaceModifier(Modifier, ABC):
    """Base for board features. Can mix in Approach or Landing hooks."""

    priority: int = 5


@dataclass(eq=False)
class RacerModifier(Modifier, ABC):
    """Attached to Racers (e.g. SlimeDebuff)."""
