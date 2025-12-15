import logging
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.agent_base import DecisionReason, SelectionDecision
from magical_athlete_simulator.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine

logger = logging.getLogger(LOGGER_NAME)


class AbilityCopyLead(Ability):
    name: ClassVar[AbilityName] = "CopyLead"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngineLike) -> bool:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return False

        me = engine.get_racer(owner_idx)
        racers = engine.state.racers

        # 1. Find all racers who are strictly ahead of Copycat
        potential_targets = [
            r for r in racers if r.position > me.position and not r.finished
        ]

        if not potential_targets:
            logger.info(f"{self.name}: No one ahead to copy.")
            return False

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
            return False

        logger.info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        engine.update_racer_abilities(owner_idx, target.abilities)
        return True
