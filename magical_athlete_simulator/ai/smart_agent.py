from dataclasses import dataclass
from typing import override

from magical_athlete_simulator.core.agent import (
    Agent,
    DecisionContext,
    SelectionDecisionContext,
)


@dataclass
class SmartAgent(Agent):
    """A concrete agent that delegates decisions to the source ability."""

    @override
    def make_boolean_decision(self, ctx: DecisionContext) -> bool:
        return ctx.source.get_auto_boolean_decision(ctx)

    @override
    def make_selection_decision[T](self, ctx: SelectionDecisionContext[T]) -> T:
        return ctx.source.get_auto_selection_decision(ctx)
