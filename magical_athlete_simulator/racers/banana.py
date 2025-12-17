from typing import TYPE_CHECKING, ClassVar, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    GameEvent,
    PassingEvent,
    Phase,
    TripCmdEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityBananaTrip(Ability):
    name: ClassVar[AbilityName] = "BananaTrip"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine) -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Only trigger if *I* (Banana) am the victim
        if event.victim_idx != owner_idx:
            return False

        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return False

        engine.log_info(f"{self.name}: Queuing TripCmd for {mover.repr}.")

        # Push a command to the queue instead of mutating state directly
        engine.push_event(
            TripCmdEvent(racer_idx=mover.idx, source=self.name),
            phase=Phase.REACTION,  # Reactions happen in their own phase
        )

        return True  # The ability successfully fired an event
