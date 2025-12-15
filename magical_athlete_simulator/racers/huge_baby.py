import logging
from dataclasses import dataclass
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    PreMoveEvent,
    PreWarpEvent,
)
from magical_athlete_simulator.core.protocols import (
    Ability,
    ApproachHookMixin,
    LifecycleManagedMixin,
    SpaceModifier,
)
from magical_athlete_simulator.core.types import AbilityName
from magical_athlete_simulator.engine.game_engine import GameEngine

logger = logging.getLogger(LOGGER_NAME)


@dataclass(eq=False)
class HugeBabyModifier(SpaceModifier, ApproachHookMixin):
    """The physical manifestation of the Huge Baby on the board.
    Blocks others from entering the tile by redirecting them backward.
    """

    name: ClassVar[AbilityName | str] = "HugeBabyBlocker"
    priority: int = 10

    @override
    def on_approach(self, target: int, mover_idx: int, engine: GameEngine) -> int:
        # Prevent others from entering the tile
        if target == 0:
            return target

        logger.info(f"Huge Baby already occupies {target}!")
        # Redirect to the previous tile
        return max(0, target - 1)


class HugeBabyPush(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "HugeBabyPush"
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
            engine.state.board.register_modifier(racer.position, mod)

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int):
        racer = engine.get_racer(owner_idx)
        mod = HugeBabyModifier(owner_idx=owner_idx)
        engine.state.board.unregister_modifier(racer.position, mod)

    # --- REWRITTEN: The core logic is now split into clear phases ---
    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine) -> bool:
        # --- DEPARTURE LOGIC: Triggered BEFORE the move happens ---
        if isinstance(event, (PreMoveEvent, PreWarpEvent)):
            if event.racer_idx != owner_idx:
                return False

            start_tile = event.start_tile
            # No blocker to clean up at the start line
            if start_tile == 0:
                return False

            # Clean up the blocker from the tile we are leaving
            mod_to_remove = self._get_modifier(owner_idx)
            engine.state.board.unregister_modifier(start_tile, mod_to_remove)

            # This is a cleanup action, so it should not trigger other abilities
            return False

        # --- ARRIVAL LOGIC: Triggered AFTER the move is complete ---
        if isinstance(event, (PostMoveEvent, PostWarpEvent)):
            if event.racer_idx != owner_idx:
                return False

            end_tile = event.end_tile
            # Huge Baby does not place a blocker at the start line
            if end_tile == 0:
                return False

            # 1. Place a new blocker at the destination
            mod_to_add = self._get_modifier(owner_idx)
            engine.state.board.register_modifier(end_tile, mod_to_add)

            # 2. "Active Push": Eject any racers already on this tile
            victims = [
                r
                for r in engine.state.racers
                if r.position == end_tile and r.idx != owner_idx and not r.finished
            ]

            for v in victims:
                target = max(0, event.end_tile - 1)
                engine.push_warp(v.idx, target, source=self.name, phase=event.phase)
                logger.info(f"Huge Baby pushes {v.repr} to {target}")

                # Explicitly emit a trigger for THIS push.
                engine.emit_ability_trigger(owner_idx, self.name, f"Pushing {v.repr}")

            # Return False because we handled our own emissions.
            # This prevents the `_wrapped_handler` from firing a generic event.
            return False

        return False
