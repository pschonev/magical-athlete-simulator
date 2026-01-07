from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import GameEvent, Phase, TurnStartEvent
from magical_athlete_simulator.core.state import RacerState
from magical_athlete_simulator.engine.movement import push_simultaneous_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class FlipFlopSwap(Ability, SelectionDecisionMixin[RacerState]):
    name: AbilityName = "FlipFlopSwap"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, TurnStartEvent):
            return "skip_trigger"

        # Only on Flip Flop's own turn
        if event.target_racer_idx != owner_idx:
            return "skip_trigger"

        ff = engine.get_racer(owner_idx)
        if not ff.active or ff.finished:
            return "skip_trigger"

        target = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[RacerState],
                RacerState,
            ](
                source=self,
                game_state=engine.state,
                source_racer_idx=owner_idx,
                options=engine.state.racers,
            ),
        )

        if target is None:
            return "skip_trigger"

        ff_pos = ff.position
        target_pos = target.position

        push_simultaneous_warp(
            engine,
            warps=[
                (owner_idx, target_pos),  # Flip Flop -> Target's old pos
                (target.idx, ff_pos),  # Target -> Flip Flop's old pos
            ],
            phase=Phase.PRE_MAIN,
            source=self.name,
            responsible_racer_idx=owner_idx,
            emit_ability_triggered="after_resolution",
        )

        # FlipFlop skips main move when using his ability
        engine.skip_main_move(owner_idx, self.name)

        return "skip_trigger"

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerState],
    ) -> RacerState | None:
        # pick someone at least 6 ahead (strictly greater position)
        candidates: list[RacerState] = [
            c
            for c in ctx.options
            if (c.position - engine.get_racer_pos(ctx.source_racer_idx)) >= 6
            and c.active
        ]
        if not candidates:
            return None

        # Choose the one furthest ahead
        return max(
            candidates,
            key=lambda r: r.position,
        )
