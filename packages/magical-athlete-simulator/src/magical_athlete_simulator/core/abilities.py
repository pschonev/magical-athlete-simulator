from dataclasses import dataclass
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.agent import Agent, DefaultAutosolvableMixin
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class Ability(DefaultAutosolvableMixin):
    """Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    name: AbilityName
    triggers: tuple[type[GameEvent], ...] = ()

    def register(self, engine: GameEngine, owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
    ):
        """The internal handler that wraps the user logic.
        It checks liveness, executes logic, and automatically emits the trigger event.
        """
        # 1. Dead racers tell no tales (usually)
        if not engine.state.racers[owner_idx].active:
            return

        # 2. Execute
        ability_triggered_event = self.execute(
            event,
            owner_idx,
            engine,
            engine.get_agent(owner_idx),
        )

        # 3. Automatic Emission
        if isinstance(ability_triggered_event, AbilityTriggeredEvent):
            engine.push_event(event=ability_triggered_event)

    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        """Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        _ = event, owner_idx, engine, agent
        return "skip_trigger"
