from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    Phase,
    PostMoveEvent,
    PostWarpEvent,
    PreMoveEvent,
    PreWarpEvent,
)
from magical_athlete_simulator.core.mixins import (
    ApproachHookMixin,
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.modifiers import SpaceModifier
from magical_athlete_simulator.engine.movement import push_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class HugeBabyModifier(SpaceModifier, ApproachHookMixin):
    """The physical manifestation of the Huge Baby on the board.
    Blocks others from entering the tile by redirecting them backward.
    """

    name: AbilityName | ModifierName = "HugeBabyBlocker"
    priority: int = 10

    @override
    def on_approach(
        self,
        target: int,
        modifier_owner_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        # Prevent others from entering the tile
        if target == 0:
            return target

        if self.owner_idx is None:
            msg = f"Expected ID of {self.display_name} owner but got None"
            raise ValueError(msg)
        engine.push_event(
            AbilityTriggeredEvent(
                self.owner_idx,
                source=self.name,
                phase=Phase.SYSTEM,
            ),
        )
        # Redirect to the previous tile
        return max(0, target - 1)


@dataclass
class HugeBabyPush(Ability, LifecycleManagedMixin):
    name: AbilityName = "HugeBabyPush"
    triggers: tuple[type[GameEvent], ...] = (
        PreMoveEvent,
        PreWarpEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    def _get_modifier(self, owner_idx: int) -> HugeBabyModifier:
        """Helper to create the modifier instance for this specific owner."""
        return HugeBabyModifier(owner_idx=owner_idx)

    # --- on_gain and on_loss remain unchanged ---
    @override
    @staticmethod
    def on_gain(engine: GameEngine, owner_idx: int):
        racer = engine.get_racer(owner_idx)
        if racer.position > 0:
            mod = HugeBabyModifier(owner_idx=owner_idx)
            engine.state.board.register_modifier(racer.position, mod, engine)

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int):
        racer = engine.get_racer(owner_idx)
        mod = HugeBabyModifier(owner_idx=owner_idx)
        engine.state.board.unregister_modifier(racer.position, mod, engine)

    # --- REWRITTEN: The core logic is now split into clear phases ---
    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # --- DEPARTURE LOGIC: Triggered BEFORE the move happens ---
        if isinstance(event, (PreMoveEvent, PreWarpEvent)):
            if event.target_racer_idx != owner_idx:
                return "skip_trigger"

            start_tile = event.start_tile
            # No blocker to clean up at the start line
            if start_tile == 0:
                return "skip_trigger"

            # Clean up the blocker from the tile we are leaving
            mod_to_remove = self._get_modifier(owner_idx)
            engine.state.board.unregister_modifier(start_tile, mod_to_remove, engine)

            # This is a cleanup action, so it should not trigger other abilities
            return "skip_trigger"

        # --- ARRIVAL LOGIC: Triggered AFTER the move is complete ---
        if isinstance(event, (PostMoveEvent, PostWarpEvent)):
            if event.target_racer_idx != owner_idx:
                return "skip_trigger"

            end_tile = event.end_tile
            # Huge Baby does not place a blocker at the start line
            if end_tile == 0:
                return "skip_trigger"

            # 1. Place a new blocker at the destination
            mod_to_add = self._get_modifier(owner_idx)
            engine.state.board.register_modifier(end_tile, mod_to_add, engine)

            # 2. "Active Push": Eject any racers already on this tile
            victims = [
                r
                for r in engine.state.racers
                if r.position == end_tile and r.idx != owner_idx and not r.finished
            ]

            for v in victims:
                target = max(0, event.end_tile - 1)
                push_warp(
                    engine,
                    target,
                    phase=event.phase,
                    warped_racer_idx=v.idx,
                    source=self.name,
                    responsible_racer_idx=None,
                )
                engine.log_info(f"HugeBaby pushes {v.repr} to {target}")

                # Explicitly emit a trigger for THIS push.
                engine.push_event(
                    AbilityTriggeredEvent(owner_idx, self.name, event.phase),
                )

            # Return False because we handled our own emissions.
            # This prevents the `_wrapped_handler` from firing a generic event.
            return "skip_trigger"

        return "skip_trigger"
