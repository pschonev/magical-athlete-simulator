from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from magical_athlete_simulator.core.agent import (
    Agent,
    DecisionContext,
    SelectionDecisionContext,
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
        ctx: DecisionContext,
    ) -> bool:
        return ctx.source.get_auto_boolean_decision(engine, ctx)

    @override
    def make_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext,
    ) -> Any:
        return ctx.source.get_auto_selection_decision(engine, ctx)
