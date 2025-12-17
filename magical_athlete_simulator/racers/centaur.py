from typing import TYPE_CHECKING, ClassVar, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    GameEvent,
    PassingEvent,
    Phase,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityTrample(Ability):
    name: ClassVar[AbilityName] = "Trample"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine) -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Logic: Only trigger if *I* am the mover
        if event.mover_idx != owner_idx:
            return False

        victim = engine.get_racer(event.victim_idx)
        if victim.finished:
            return False

        engine.log_info(f"{self.name}: Centaur passed {victim.repr}. Queuing -2 move.")
        push_move(
            engine,
            victim.idx,
            -2,
            self.name,
            phase=Phase.REACTION,
            owner_idx=owner_idx,
        )
        return True
