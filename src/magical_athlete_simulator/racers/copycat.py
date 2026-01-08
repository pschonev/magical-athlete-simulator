from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import RacerState

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityCopyLead(Ability, SelectionDecisionMixin[RacerState]):
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
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return "skip_trigger"

        me = engine.get_racer(owner_idx)
        racers = engine.state.racers

        active_racers = [r for r in racers if not r.finished and r.idx != owner_idx]
        if not active_racers:
            potential_targets = []
        else:
            max_pos = max(r.position for r in active_racers)
            potential_targets = [r for r in active_racers if r.position == max_pos]
            engine.log_info(f"{potential_targets=}")

        if not potential_targets:
            # Only log at TurnStart to avoid spamming logs on every move
            if isinstance(event, TurnStartEvent):
                engine.log_info(f"{self.name}: No one ahead to copy.")
            engine.update_racer_abilities(owner_idx, new_abilities={self.name})
            return "skip_trigger"

        # 2. Find the highest position among those ahead
        max_pos = max(r.position for r in potential_targets)
        leaders = [r for r in potential_targets if r.position == max_pos]
        # Sort for deterministic behavior
        leaders.sort(key=lambda r: r.idx)

        # 3. Ask the Agent which leader to copy
        target = agent.make_selection_decision(
            engine,
            SelectionDecisionContext(
                source=self,
                game_state=engine.state,
                source_racer_idx=owner_idx,
                options=leaders,
            ),
        )
        if target is None:
            return "skip_trigger"

        # Optimization: Don't copy if abilities are identical
        if not me.abilities.isdisjoint(target.abilities):
            return "skip_trigger"

        engine.log_info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        # 4. Perform the Update
        # This registers the new ability with the engine, but it won't run in the current loop.
        new_abilities = set(target.abilities)
        new_abilities.add(self.name)
        engine.update_racer_abilities(owner_idx, new_abilities)

        # 5. IMMEDIATE TRIGGER CHECK
        # Because the engine loop over subscribers is already running, the new ability
        # (if it triggers on this same event type) will be missed. We run it manually.

        # We need to find the specific new ability instance.
        # Since 'target.abilities' is a set of names, we iterate over them.
        current_event_type = type(event)

        for ab_name in target.abilities:
            # We look up the instance in our own active abilities
            if ab_name in me.active_abilities:
                ab_instance = me.active_abilities[ab_name]

                # Check if this ability is triggered by the current event type
                if current_event_type in ab_instance.triggers:
                    engine.log_info(
                        f"{self.name}: Manually triggering new ability {ab_name} because it missed the event loop.",
                    )
                    # Manually invoke the wrapped handler (so it checks liveness etc.)
                    # We access the method bound to the instance.
                    # Note: We can call 'execute' directly, but _wrapped_handler handles logs/emit.
                    # Since we can't easily access _wrapped_handler from here without internal knowledge
                    # (it's usually the callback), we will call execute directly and emit the event manually if needed.

                    # Better: If we can trust 'execute' returns the event or skipped.
                    result = ab_instance.execute(
                        replace(event, target_racer_idx=owner_idx),
                        owner_idx,
                        engine,
                        agent,
                    )

                    if isinstance(result, AbilityTriggeredEvent):
                        engine.push_event(result)

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner_idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=target.idx,
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerState],
    ) -> RacerState:
        # Always return the first option (deterministic tie-break)
        # options are already sorted by idx in execute()
        return ctx.options[0]
