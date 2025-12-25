from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import BooleanDecision, DecisionReason
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollModificationWindowEvent,
)
from magical_athlete_simulator.engine.roll import trigger_reroll

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityMagicalReroll(Ability):
    name: AbilityName = "MagicalReroll"
    triggers: tuple[type[GameEvent], ...] = (RollModificationWindowEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, RollModificationWindowEvent):
            return "skip_trigger"

        me = engine.get_racer(owner_idx)

        # 1. Eligibility Check
        if event.target_racer_idx != owner_idx:
            return "skip_trigger"
        if me.reroll_count >= 2:
            return "skip_trigger"

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
            engine.push_event(
                AbilityTriggeredEvent(
                    owner_idx,
                    source=self.name,
                    phase=event.phase,
                ),
            )
            trigger_reroll(engine, owner_idx, "MagicalReroll")
            # Return False to prevent generic emission, as we handled it via emit_ability_trigger
            return "skip_trigger"

        return "skip_trigger"
