from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from magical_athlete_simulator.engine.state import GameState, RacerState


class DecisionReason(Enum):
    """Specific reasons an Agent is being asked to make a decision."""

    MAGICAL_REROLL = auto()
    COPY_LEAD_TARGET = auto()


@dataclass
class DecisionContext:
    """Base context containing the minimal state needed for a decision."""

    game_state: GameState
    source_racer_idx: int
    reason: DecisionReason


@dataclass
class BooleanDecision(DecisionContext):
    """A Yes/No decision (e.g., should I reroll?)."""


@dataclass
class SelectionDecision(DecisionContext):
    """A generic selection from a list of options."""

    options: list[RacerState]


class Agent(ABC):
    """Base interface for decision making entities."""

    @abstractmethod
    def make_boolean_decision(self, ctx: BooleanDecision) -> bool:
        pass

    @abstractmethod
    def make_selection_decision(self, ctx: SelectionDecision) -> int:
        """Return the index of the selected option."""
