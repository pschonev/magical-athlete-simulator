from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from magical_athlete_simulator.core.abilities import Ability
    from magical_athlete_simulator.core.state import GameState


@dataclass
class DecisionContext:
    source: Ability
    game_state: GameState
    source_racer_idx: int


@dataclass
class SelectionDecisionContext[T](DecisionContext):
    options: list[T]


@runtime_checkable
class Autosolvable(Protocol):
    """Protocol for any object that can answer its own decision requests."""

    def get_auto_boolean_decision(self, ctx: DecisionContext) -> bool: ...
    def get_auto_selection_decision(self, ctx: DecisionContext) -> int: ...


class DefaultAutosolvableMixin:
    """
    Mixin that provides safe, 'dumb' default behavior.
    Inherit from this in your Ability class to make it Autosolvable.
    """

    def get_auto_boolean_decision(self, ctx: DecisionContext) -> bool:
        # Default: Always say No to optional things
        _ = ctx
        return False

    def get_auto_selection_decision[T](self, ctx: SelectionDecisionContext[T]) -> T:
        # Default: Always pick the first option
        _ = ctx
        return ctx.options[0]


class Agent:
    """Base Agent that knows how to handle context but not specific rules."""

    def make_boolean_decision(self, ctx: DecisionContext) -> bool:
        _ = ctx
        return NotImplemented

    def make_selection_decision[T](self, ctx: SelectionDecisionContext[T]) -> T:
        _ = ctx
        return NotImplemented
