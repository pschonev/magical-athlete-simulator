from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PassingEvent,
)
from magical_athlete_simulator.engine.movement import push_trip

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityBananaTrip(Ability):
    name: AbilityName = "BananaTrip"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, PassingEvent):
            return "skip_trigger"

        # check if passed racer has Banana ability
        if event.passed_racer_idx != owner_idx:
            return "skip_trigger"

        victim = engine.get_racer(event.passing_racer_idx)
        if victim.finished:
            return "skip_trigger"

        engine.log_info(f"{self.name}: Queuing TripCmd for {victim.repr}.")
        push_trip(
            engine,
            tripped_racer_idx=event.passing_racer_idx,
            source=self.name,
            responsible_racer_idx=owner_idx,
            phase=event.phase,
        )

        return "skip_trigger"  # delay this until we know whether the tripping happened
