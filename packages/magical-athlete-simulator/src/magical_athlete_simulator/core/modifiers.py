from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, ModifierName


@dataclass
class Modifier(ABC):
    """Base class for all persistent effects."""

    owner_idx: int | None
    name: AbilityName | ModifierName

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


@dataclass(eq=False)
class SpaceModifier(Modifier, ABC):
    """Base for board features. Can mix in Approach or Landing hooks."""

    priority: int = 5


@dataclass(eq=False)
class RacerModifier(Modifier, ABC):
    """Attached to Racers (e.g. SlimeDebuff)."""
