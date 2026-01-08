from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.agent import (
    Agent,
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class SmartAgent(Agent):
    """A concrete agent that delegates decisions to the source ability."""

    @override
    def make_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[BooleanInteractive],
    ) -> bool:
        return ctx.source.get_auto_boolean_decision(engine, ctx)

    @override
    def make_selection_decision[R](
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return ctx.source.get_auto_selection_decision(engine, ctx)
