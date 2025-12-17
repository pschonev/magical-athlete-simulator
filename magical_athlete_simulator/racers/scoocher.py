from typing import TYPE_CHECKING, ClassVar, assert_never, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    Phase,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityScoochStep(Ability):
    name: ClassVar[AbilityName] = "ScoochStep"
    triggers: tuple[type[GameEvent], ...] = (AbilityTriggeredEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine) -> bool:
        if not isinstance(event, AbilityTriggeredEvent):
            return False

        # Logic: Trigger on ANY ability, except my own
        if event.source_racer_idx == owner_idx:
            return False

        # Correct code
        me = engine.get_racer(owner_idx)  # <--- Get MY state
        if me.finished:
            return False

        source_racer = engine.get_racer(owner_idx)
        if event.source_racer_idx is None:
            _ = assert_never
            raise ValueError("AbilityTriggeredEvent should always have a source racer.")

        # Logging context
        source_racer: RacerState = engine.get_racer(event.source_racer_idx)
        cause_msg = f"Saw {source_racer.repr} use {event.ability_name}"

        engine.log_info(f"{self.name}: {cause_msg} -> Queue Moving 1")
        push_move(
            engine, owner_idx, 1, self.name, phase=Phase.REACTION, owner_idx=owner_idx
        )

        # Returns True, so ScoochStep will emit an AbilityTriggeredEvent.
        # This is fine, because the NEXT ScoochStep check will see source_idx == owner_idx
        # (assuming only one Scoocher exists).
        # If two Scoochers exist, they WILL infinite loop off each other.
        # That is actually consistent with the board game rules (infinite loop -> execute once -> stop).
        # Our Engine loop detector handles the "Stop" part.
        return True
