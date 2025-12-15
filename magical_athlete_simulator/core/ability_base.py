from abc import ABC, abstractmethod
from typing import ClassVar

from magical_athlete_simulator.core.events import GameEvent
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine


class Ability(ABC):
    """Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    name: ClassVar[AbilityName]
    triggers: tuple[type[GameEvent], ...] = ()

    def register(self, engine: GameEngine, owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        """The internal handler that wraps the user logic.
        It checks liveness, executes logic, and automatically emits the trigger event.
        """
        # 1. Dead racers tell no tales (usually)
        if engine.state.racers[owner_idx].finished:
            return

        # 2. Execute
        did_trigger = self.execute(event, owner_idx, engine)

        # 3. Automatic Emission
        if did_trigger:
            ctx = f"Reacting to {event.__class__.__name__}"
            engine.emit_ability_trigger(owner_idx, self.name, ctx)

    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        """Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        _ = event, owner_idx, engine
        return False


class LifecycleManagedMixin(ABC):
    @staticmethod
    @abstractmethod
    def on_gain(engine: "GameEngine", owner_idx: int) -> None:
        pass

    @staticmethod
    @abstractmethod
    def on_loss(engine: "GameEngine", owner_idx: int) -> None:
        pass
