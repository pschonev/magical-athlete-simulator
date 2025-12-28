from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class RomanticMove(Ability):
    name: AbilityName = "RomanticMove"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, (PostMoveEvent, PostWarpEvent)):
            return "skip_trigger"

        if not engine.get_racer(owner_idx):
            return "skip_trigger"

        racers_on_tile = engine.get_racers_at_position(event.end_tile)

        if len(racers_on_tile) == 2:
            push_move(
                engine,
                distance=2,
                phase=event.phase,
                moved_racer_idx=owner_idx,
                source=self.name,
                responsible_racer_idx=owner_idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
