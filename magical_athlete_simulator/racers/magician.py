import logging
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.agent_base import BooleanDecision, DecisionReason
from magical_athlete_simulator.core.events import GameEvent, RollModificationWindowEvent
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine

logger = logging.getLogger(LOGGER_NAME)


class AbilityMagicalReroll(Ability):
    name: ClassVar[AbilityName] = "MagicalReroll"
    triggers: tuple[type[GameEvent], ...] = (RollModificationWindowEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine):
        if not isinstance(event, RollModificationWindowEvent):
            return False

        me = engine.get_racer(owner_idx)

        # 1. Eligibility Check
        if event.racer_idx != owner_idx:
            return False
        if me.reroll_count >= 2:
            return False

        # 2. Ask the Agent
        agent = engine.get_agent(owner_idx)
        decision_ctx = BooleanDecision(
            game_state=engine.state,
            source_racer_idx=owner_idx,
            reason=DecisionReason.MAGICAL_REROLL,
        )

        should_reroll = agent.make_boolean_decision(decision_ctx)

        if should_reroll:
            me.reroll_count += 1
            engine.emit_ability_trigger(
                owner_idx,
                self.name,
                f"Disliked roll of {event.current_roll_val}",
            )
            engine.trigger_reroll(owner_idx, "MagicalReroll")
            # Return False to prevent generic emission, as we handled it via emit_ability_trigger
            return False

        return False
