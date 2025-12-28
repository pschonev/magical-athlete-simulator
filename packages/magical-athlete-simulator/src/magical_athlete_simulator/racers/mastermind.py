from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    DefaultAutosolvableMixin,
    SelectionDecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RacerFinishedEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import RacerState
from magical_athlete_simulator.engine.flow import mark_finished

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityMastermindPredict(Ability, DefaultAutosolvableMixin):
    name: AbilityName = "MastermindPredict"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent, RacerFinishedEvent)

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
        # ---------------------------------------------------------------------
        # Trigger 1: Make Prediction (Start of Mastermind's first turn)
        # ---------------------------------------------------------------------
        if isinstance(event, TurnStartEvent):
            if event.target_racer_idx == owner_idx and self.prediction is None:
                target_racer = agent.make_selection_decision(
                    engine,
                    ctx=SelectionDecisionContext(
                        source=self,
                        game_state=engine.state,
                        source_racer_idx=owner_idx,
                        options=engine.state.racers,
                    ),
                )

                # Store State
                self.prediction = target_racer.idx

                owner = engine.get_racer(owner_idx)
                engine.log_info(
                    f"{owner.repr} predicts {target_racer.name} will win the race!",
                )

                return AbilityTriggeredEvent(
                    responsible_racer_idx=owner_idx,
                    source=self.name,
                    phase=event.phase,
                )

        # ---------------------------------------------------------------------
        # Trigger 2: Check Victory (Someone finished)
        # ---------------------------------------------------------------------
        elif isinstance(event, RacerFinishedEvent):
            owner: RacerState = engine.get_racer(owner_idx)
            if event.finishing_position != 1:
                return "skip_trigger"

            if self.prediction is None:
                engine.log_info(f"{owner.repr} did not predict anything!")
                return "skip_trigger"

            winner = engine.state.racers[self.prediction]

            if event.target_racer_idx != self.prediction:
                engine.log_info(f"{owner.repr} predicted wrong!")
                return "skip_trigger"
            else:
                engine.log_info(
                    f"{owner.repr}'s prediction was correct! {winner.repr} won!",
                )

                if not owner.finished:
                    if engine.state.rules.hr_mastermind_steal_1st:
                        # house rule lets Mastermind steal 1st place instead
                        engine.log_info("Mastermind steals 1st place!")
                        mark_finished(
                            engine,
                            racer=engine.get_racer(event.target_racer_idx),
                            rank=2,
                        )
                        mark_finished(engine, owner, 1)
                    else:
                        # If Mastermind hasn't finished yet, they take 2nd place immediately.
                        engine.log_info("Mastermind claims 2nd place immediately!")
                        mark_finished(engine, owner, 2)

        return "skip_trigger"

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext,
    ) -> RacerState:
        """
        AI Logic: Predict the racer with the best early-game stats or position.
        """
        options: list[RacerState] = cast("list[RacerState]", ctx.options)
        candidates = [r for r in options if r.idx != ctx.source_racer_idx]
        if not candidates:
            return engine.get_racer(ctx.source_racer_idx)
        # Sort by position (descending)
        candidates.sort(key=lambda r: r.position, reverse=True)
        return candidates[0]
