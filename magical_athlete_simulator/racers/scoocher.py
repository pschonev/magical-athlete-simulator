from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    HasTargetRacer,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityScoochStep(Ability):
    name: AbilityName = "ScoochStep"
    triggers: tuple[type[GameEvent], ...] = (AbilityTriggeredEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, AbilityTriggeredEvent):
            return "skip_trigger"

        # Logic: Trigger on ANY ability, except my own
        if event.responsible_racer_idx == owner_idx:
            return "skip_trigger"

        # Correct code
        me = engine.get_racer(owner_idx)  # <--- Get MY state
        if me.finished:
            return "skip_trigger"

        source_racer = engine.get_racer(owner_idx)

        # Logging context
        source_racer: RacerState = engine.get_racer(event.responsible_racer_idx)

        target_msg = ""
        if isinstance(event, HasTargetRacer):
            target_msg = f" on {event.target_racer_idx}"

        cause_msg = f"Saw {source_racer.repr} use {event.source}{target_msg}"

        engine.log_info(f"{owner_idx}:{self.name}: {cause_msg} -> Queue Moving 1")
        push_move(
            engine,
            1,
            phase=event.phase,
            moved_racer_idx=owner_idx,
            source=self.name,
            responsible_racer_idx=owner_idx,
            emit_ability_triggered="after_resolution",
        )

        # Returns True, so ScoochStep will emit an AbilityTriggeredEvent.
        # This is fine, because the NEXT ScoochStep check will see source_idx == owner_idx
        # (assuming only one Scoocher exists).
        # If two Scoochers exist, they WILL infinite loop off each other.
        # That is actually consistent with the board game rules (infinite loop -> execute once -> stop).
        # Our Engine loop detector handles the "Stop" part.
        return "skip_trigger"
