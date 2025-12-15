from dataclasses import dataclass, field

from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.modifier_base import RacerModifier
from magical_athlete_simulator.core.types import AbilityName, RacerName
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS, Board


@dataclass(slots=True)
class RollState:
    serial_id: int = 0
    base_value: int = 0
    final_value: int = 0


@dataclass(slots=True)
class RacerState:
    idx: int
    name: RacerName
    position: int = 0
    victory_points: int = 0
    tripped: bool = False
    reroll_count: int = 0
    finish_position: int | None = None
    eliminated: bool = False

    modifiers: list[RacerModifier] = field(default_factory=list)
    active_abilities: dict[AbilityName, Ability] = field(default_factory=dict)

    @property
    def repr(self) -> str:
        return f"{self.idx}:{self.name}"

    @property
    def abilities(self) -> set[AbilityName]:
        """Derive from active instances."""
        return set(self.active_abilities.keys())

    @property
    def finished(self) -> bool:
        return self.finish_position is not None

    @property
    def active(self) -> bool:
        return not self.finished and not self.eliminated


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    roll_state: RollState = field(default_factory=RollState)
    board: Board = field(default_factory=BOARD_DEFINITIONS["standard"])

    def get_state_hash(self) -> int:
        """Hash entire game state including all racer data."""
        racer_data = tuple(
            (
                r.idx,
                r.position,
                r.tripped,
                r.finish_position,
                r.eliminated,
                r.victory_points,
                frozenset(r.abilities),
                frozenset(m.name for m in r.modifiers),
            )
            for r in self.racers
        )

        board_data = frozenset(
            (tile, frozenset(m.name for m in mods))
            for tile, mods in self.board.dynamic_modifiers.items()
        )

        return hash((racer_data, board_data))
