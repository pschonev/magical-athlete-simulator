from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import DecisionReason, SelectionDecision
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityCopyLead(Ability):
    name: AbilityName = "CopyLead"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return "skip_trigger"

        me = engine.get_racer(owner_idx)
        racers = engine.state.racers

        # 1. Find all racers who are strictly ahead of Copycat
        potential_targets = [
            r for r in racers if r.position > me.position and not r.finished
        ]

        if not potential_targets:
            engine.log_info(f"{self.name}: No one ahead to copy.")
            return "skip_trigger"

        # 2. Find the highest position among those ahead
        max_pos = max(r.position for r in potential_targets)
        leaders = [r for r in potential_targets if r.position == max_pos]
        leaders.sort(key=lambda r: r.idx)

        # 3. Ask the Agent which leader to copy
        agent = engine.get_agent(owner_idx)
        decision_ctx = SelectionDecision(
            game_state=engine.state,
            source_racer_idx=owner_idx,
            reason=DecisionReason.COPY_LEAD_TARGET,
            options=leaders,
        )

        selected_index = agent.make_selection_decision(decision_ctx)
        target = leaders[selected_index]

        # Avoid redundant updates
        if me.abilities == target.abilities:
            return "skip_trigger"

        engine.log_info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        engine.update_racer_abilities(owner_idx, target.abilities)
        return AbilityTriggeredEvent(owner_idx, self.name, phase=event.phase)
