from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import GameEvent, Phase, TurnStartEvent
from magical_athlete_simulator.engine.movement import push_simultaneous_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class FlipFlopSwap(Ability):
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

        # AI decision: pick someone at least 6 ahead (strictly greater position)
        candidates: list[RacerState] = [
            c
            for c in engine.state.racers
            if (c.position - ff.position) >= 6 and c.active
        ]
        if not candidates:
            return "skip_trigger"

        # Choose the one furthest ahead
        target = max(
            candidates,
            key=lambda r: r.position,
        )

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
        ff.main_move_consumed = True

        return "skip_trigger"
