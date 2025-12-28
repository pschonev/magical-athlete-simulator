from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from magical_athlete_simulator.core.abilities import Ability
    from magical_athlete_simulator.core.state import GameState
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class DecisionContext:
    source: Ability
    game_state: GameState
    source_racer_idx: int


@dataclass
class SelectionDecisionContext(DecisionContext):
    options: list[Any]


@runtime_checkable
class Autosolvable(Protocol):
    """Protocol for any object that can answer its own decision requests."""

    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext,
    ) -> bool: ...
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext,
    ) -> int: ...


class DefaultAutosolvableMixin:
    """
    Mixin that provides safe, 'dumb' default behavior.
    Inherit from this in your Ability class to make it Autosolvable.
    """

    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext,
    ) -> bool:
        # Default: Always say No to optional things
        _ = ctx, engine
        return False

    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext,
    ) -> Any:
        # Default: Always pick the first option
        _ = ctx, engine
        return ctx.options[0]


class Agent:
    """Base Agent that knows how to handle context but not specific rules."""

    def make_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext,
    ) -> bool:
        _ = ctx, engine
        return NotImplemented

    def make_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext,
    ) -> Any:
        _ = ctx, engine
        return NotImplemented
