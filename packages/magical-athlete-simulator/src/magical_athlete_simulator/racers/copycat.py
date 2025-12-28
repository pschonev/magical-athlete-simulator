from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import Agent, SelectionDecisionContext
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import RacerState
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
        agent: Agent,
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
            # Only log at TurnStart to avoid spamming logs on every move
            if isinstance(event, TurnStartEvent):
                engine.log_info(f"{self.name}: No one ahead to copy.")
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

        # Optimization: Don't copy if abilities are identical
        if me.abilities == target.abilities:
            return "skip_trigger"

        engine.log_info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        # 4. Perform the Update
        # This registers the new ability with the engine, but it won't run in the current loop.
        engine.update_racer_abilities(owner_idx, target.abilities)

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
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext,
    ) -> RacerState:
        # Always return the first option (deterministic tie-break)
        # options are already sorted by idx in execute()
        return ctx.options[0]
