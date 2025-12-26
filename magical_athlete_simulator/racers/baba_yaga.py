from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.engine.movement import push_trip

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class BabaYagaTrip(Ability):
    name: AbilityName = "BabaYagaTrip"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, self.triggers):
            return "skip_trigger"

        # whether Baba Yaga moves somewhere or racers move onto her space
        # everyone there except Baba Yaga will trip
        baba = engine.get_racer(owner_idx)
        if not baba.active:
            return "skip_trigger"

        for victim in engine.get_racers_at_position(
            tile_idx=baba.position,
            except_racer_idx=owner_idx,
        ):
            push_trip(
                engine,
                phase=event.phase,
                tripped_racer_idx=victim.idx,
                source=self.name,
                responsible_racer_idx=owner_idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
