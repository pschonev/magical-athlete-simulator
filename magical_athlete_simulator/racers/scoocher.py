import logging
from typing import ClassVar, assert_never, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.events import AbilityTriggeredEvent, GameEvent
from magical_athlete_simulator.core.types import AbilityName, Phase
from magical_athlete_simulator.engine.game_engine import GameEngine
from magical_athlete_simulator.engine.state import RacerState

logger = logging.getLogger(LOGGER_NAME)


class AbilityScoochStep(Ability):
    name: ClassVar[AbilityName] = "ScoochStep"
    triggers: tuple[type[GameEvent], ...] = (AbilityTriggeredEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngineLike) -> bool:
        if not isinstance(event, AbilityTriggeredEvent):
            return False

        # Logic: Trigger on ANY ability, except my own
        if event.source_racer_idx == owner_idx:
            return False

        if event.source_racer_idx is None:
            _ = assert_never
            raise ValueError("AbilityTriggeredEvent should always have a source racer.")

        # Logging context
        source_racer: RacerState = engine.get_racer(event.source_racer_idx)
        cause_msg = f"Saw {source_racer.name} use {event.ability_name}"

        logger.info(f"{self.name}: {cause_msg} -> Moving 1")
        engine.push_move(owner_idx, 1, self.name, phase=Phase.REACTION)

        # Returns True, so ScoochStep will emit an AbilityTriggeredEvent.
        # This is fine, because the NEXT ScoochStep check will see source_idx == owner_idx
        # (assuming only one Scoocher exists).
        # If two Scoochers exist, they WILL infinite loop off each other.
        # That is actually consistent with the board game rules (infinite loop -> execute once -> stop).
        # Our Engine loop detector handles the "Stop" part.
        return True
