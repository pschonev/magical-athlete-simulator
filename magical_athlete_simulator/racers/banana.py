import logging
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.events import GameEvent, PassingEvent
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine

logger = logging.getLogger(LOGGER_NAME)


class AbilityBananaTrip(Ability):
    name: ClassVar[AbilityName] = "BananaTrip"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngineLike) -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Logic: Only trigger if *I* am the victim
        if event.victim_idx != owner_idx:
            return False

        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return False

        logger.info(f"{self.name}: {mover.repr} passed Banana! Tripping mover.")
        mover.tripped = True
        return True
