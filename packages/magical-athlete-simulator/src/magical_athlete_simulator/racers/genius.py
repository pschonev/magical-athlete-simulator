from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollModificationWindowEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityGenius(Ability):
    name: AbilityName = "GeniusPrediction"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        RollModificationWindowEvent,
    )

    # Persistent State
    prediction: int | None = None

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # 1. Prediction Phase (Turn Start)
        if isinstance(event, TurnStartEvent):
            if event.target_racer_idx == owner_idx:
                # Deterministic fallback: Always predict 6.
                # (In a real Agent system, this would call agent.make_selection_decision)
                self.prediction = 6

                engine.log_info(f"{self.name}: Predicts a roll of {self.prediction}.")
                return AbilityTriggeredEvent(
                    responsible_racer_idx=owner_idx,
                    source=self.name,
                    phase=event.phase,
                )
            else:
                self.prediction = None

        # 2. Check Phase (Roll Window)
        elif (
            isinstance(event, RollModificationWindowEvent)
            and event.target_racer_idx == owner_idx
            and self.prediction is not None
            and event.current_roll_val == self.prediction
        ):
            me = engine.get_racer(owner_idx)
            engine.log_info(
                f"{self.name}: Prediction Correct! {me.repr} gets an extra turn.",
            )

            # Set the override.
            engine.state.next_turn_override = owner_idx

            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
            )

        return "skip_trigger"
