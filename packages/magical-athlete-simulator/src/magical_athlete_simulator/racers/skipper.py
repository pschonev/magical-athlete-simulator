from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    ResolveMainMoveEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilitySkipper(Ability):
    name: AbilityName = "SkipperTurn"
    triggers: tuple[type[GameEvent], ...] = (ResolveMainMoveEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, ResolveMainMoveEvent):
            return "skip_trigger"

        if event.roll_serial != engine.state.roll_state.serial_id:
            engine.log_debug(
                f"{engine.get_racer(owner_idx).repr} ignores stale roll resolution for {self.name}.",
            )
            return "skip_trigger"

        # "Whenever any racer rolls a 1..."
        if engine.state.roll_state.base_value == 1:
            me = engine.get_racer(owner_idx)
            engine.log_info(
                f"{self.name}: A 1 was rolled! {me.repr} steals the next turn!",
            )

            # Simple override. If Genius already set this, we overwrite it.
            engine.state.next_turn_override = owner_idx

            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
            )

        return "skip_trigger"
