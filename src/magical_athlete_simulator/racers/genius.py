from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
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
class AbilityGenius(Ability, SelectionDecisionMixin[int]):
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
            if (
                event.target_racer_idx != owner_idx
                or engine.get_racer(owner_idx).main_move_consumed
            ):
                self.prediction = None
                return "skip_trigger"
            self.prediction = agent.make_selection_decision(
                engine,
                ctx=SelectionDecisionContext[
                    SelectionInteractive[int],
                    int,
                ](
                    source=self,
                    game_state=engine.state,
                    source_racer_idx=owner_idx,
                    options=list(range(1, 7)),
                ),
            )

            engine.log_info(f"{self.name}: Predicts a roll of {self.prediction}.")
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
            )

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

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int:
        return 6
