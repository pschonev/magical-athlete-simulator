from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.mixins import ApproachHookMixin, LandingHookMixin
from magical_athlete_simulator.core.modifiers import SpaceModifier
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent, Phase
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import (
        AbilityName,
        BoardName,
        ModifierName,
    )
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(slots=True)
class Board:
    """Manages track topology and spatial modifiers (static and dynamic)."""

    length: int
    static_features: dict[int, list[SpaceModifier]]
    dynamic_modifiers: defaultdict[int, set[SpaceModifier]] = field(
        init=False,
        default_factory=lambda: defaultdict(set),
    )

    @property
    def finish_space(self) -> int:
        return self.length

    def register_modifier(
        self,
        tile: int,
        modifier: SpaceModifier,
        engine: GameEngine,
    ) -> None:
        modifiers = self.dynamic_modifiers[tile]
        if modifier not in modifiers:
            modifiers.add(modifier)
            engine.log_info(
                f"BOARD: Registered {modifier.name} (owner={modifier.owner_idx}) at tile {tile}",
            )

    def unregister_modifier(
        self,
        tile: int,
        modifier: SpaceModifier,
        engine: GameEngine,
    ) -> None:
        modifiers = self.dynamic_modifiers.get(tile)
        if not modifiers or modifier not in modifiers:
            engine.log_warning(
                f"BOARD: Failed to unregister {modifier.name} from {tile} - not found.",
            )
            return

        modifiers.remove(modifier)
        engine.log_info(
            f"BOARD: Unregistered {modifier.name} (owner={modifier.owner_idx}) from tile {tile}",
        )

        if not modifiers:
            _ = self.dynamic_modifiers.pop(tile, None)

    def get_modifiers_at(self, tile: int) -> list[SpaceModifier]:
        static = self.static_features.get(tile, ())
        dynamic = self.dynamic_modifiers.get(tile, ())
        return sorted((*static, *dynamic), key=lambda m: m.priority)

    def resolve_position(
        self,
        target: int,
        moving_racer_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        visited: set[int] = set()
        current = target

        while current not in visited:
            visited.add(current)
            new_target = current

            for mod in (
                mod
                for mod in self.get_modifiers_at(current)
                if isinstance(mod, ApproachHookMixin)
            ):
                redirected = mod.on_approach(current, moving_racer_idx, engine, event)
                if redirected != current:
                    engine.log_info(
                        "%s redirected %s from %s -> %s",
                        mod.name,
                        engine.get_racer(moving_racer_idx).repr,
                        current,
                        redirected,
                    )
                    new_target = redirected
                    break

            if new_target == current:
                return current

            current = new_target

        engine.log_warning("resolve_position loop detected, settling on %s", current)
        return current

    def trigger_on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        for mod in (
            mod
            for mod in self.get_modifiers_at(tile)
            if isinstance(mod, LandingHookMixin)
        ):
            current_pos = engine.get_racer_pos(racer_idx)
            if current_pos != tile:
                break
            mod.on_land(tile, racer_idx, phase, engine)

    def dump_state(self, engine: GameEngine):
        """Log the location of all dynamic modifiers currently on the board.

        Useful for debugging test failures.
        """
        engine.log_info("=== BOARD STATE DUMP ===")
        if not self.dynamic_modifiers:
            engine.log_info("  (Board is empty of dynamic modifiers)")
            return

        # Sort by tile index for readability
        active_tiles = sorted(self.dynamic_modifiers.keys())
        for tile in active_tiles:
            mods = self.dynamic_modifiers[tile]
            if mods:
                # Format each modifier as "Name(owner=ID)"
                mod_strs = [f"{m.name}(owner={m.owner_idx})" for m in mods]
                engine.log_info(f"  Tile {tile:02d}: {', '.join(mod_strs)}")
        engine.log_info("========================")


@dataclass
class MoveDeltaTile(SpaceModifier, LandingHookMixin):
    """On landing, queue a move of +delta (forward) or -delta (backward)."""

    delta: int = 0
    priority: int = 5
    owner_idx: int | None = None
    name: AbilityName | ModifierName = "MoveDeltaTile"

    @property
    @override
    def display_name(self) -> str:
        return f"MoveDeltaTile({self.delta})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        if self.delta == 0:
            return
        racer: RacerState = engine.get_racer(
            racer_idx,
        )  # uses existing GameEngine API.[file:1]
        engine.log_info(
            f"{self.display_name}: Queuing {self.delta} move for {racer.repr}",
        )
        # New move is a separate event, not part of the original main move.[file:1]
        push_move(
            engine,
            self.delta,
            phase=phase,
            moved_racer_idx=racer_idx,
            source=self.name,
            responsible_racer_idx=None,
        )


@dataclass
class TripTile(SpaceModifier, LandingHookMixin):
    """On landing, trip the racer (they skip their next main move)."""

    name: AbilityName | ModifierName = "TripTile"
    priority: int = 5
    owner_idx: int | None = None

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        racer = engine.get_racer(racer_idx)
        if racer.tripped:
            return
        racer.tripped = True
        engine.log_info(f"{self.name}: {racer.repr} is now Tripped.")


@dataclass
class VictoryPointTile(SpaceModifier, LandingHookMixin):
    """On landing, grant +1 VP (or a configured amount)."""

    amount: int = 1
    priority: int = 5
    owner_idx: int | None = None
    name: AbilityName | ModifierName = "VictoryPointTile"

    @property
    @override
    def display_name(self) -> str:
        return f"VP(+{self.amount})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        racer = engine.get_racer(racer_idx)
        racer.victory_points += self.amount
        engine.log_info(
            f"{self.display_name}: {racer.repr} gains +{self.amount} VP (now {racer.victory_points}).",
        )


def build_action_lane_board() -> Board:
    """Build example board using all three static tile types.

    - Tile 3: Move forward 2.
    - Tile 6: Move back 2.
    - Tile 9: Trip.
    - Tile 12: +1 VP.
    """
    return Board(
        length=30,
        static_features={
            3: [MoveDeltaTile(None, delta=2)],
            6: [MoveDeltaTile(None, delta=-2)],
            9: [TripTile(None)],
            12: [VictoryPointTile(None, amount=1)],
        },
    )


BoardFactory = Callable[[], Board]

BOARD_DEFINITIONS: dict[BoardName, BoardFactory] = {
    "standard": lambda: Board(
        length=30,
        static_features={},
    ),
    "wild_wilds": build_action_lane_board,
}
