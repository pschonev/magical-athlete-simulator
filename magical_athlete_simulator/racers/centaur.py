import logging
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.events import GameEvent, PassingEvent
from magical_athlete_simulator.core.protocols import Ability, GameEngineLike
from magical_athlete_simulator.core.types import AbilityName, Phase

logger = logging.getLogger(LOGGER_NAME)


class AbilityTrample(Ability):
    name: ClassVar[AbilityName] = "Trample"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngineLike) -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Logic: Only trigger if *I* am the mover
        if event.mover_idx != owner_idx:
            return False

        victim = engine.get_racer(event.victim_idx)
        if victim.finished:
            return False

        logger.info(f"{self.name}: Centaur passed {victim.repr}. Queuing -2 move.")
        engine.push_move(victim.idx, -2, self.name, phase=Phase.REACTION)
        return True
