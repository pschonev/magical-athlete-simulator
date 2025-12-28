from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from magical_athlete_simulator.core.abilities import Ability
    from magical_athlete_simulator.core.events import ScheduledEvent
    from magical_athlete_simulator.core.modifiers import RacerModifier
    from magical_athlete_simulator.core.types import AbilityName, RacerName
    from magical_athlete_simulator.engine.board import Board

TimingMode = Literal["FLAT", "DFS", "BFS"]


@dataclass(slots=True)
class GameRules:
    winner_vp: tuple[int, int] = (4, 2)
    timing_mode: TimingMode = "DFS"
    count_0_moves_for_ability_triggered: bool = False
    hr_mastermind_steal_1st: bool = False


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
    main_move_consumed: bool = False
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
    board: Board
    rules: GameRules = field(default_factory=GameRules)
    current_racer_idx: int = 0
    next_turn_override: int | None = None
    roll_state: RollState = field(default_factory=RollState)

    queue: list[ScheduledEvent] = field(default_factory=list)
    serial: int = 0
    race_over: bool = False
    history: set[int] = field(default_factory=set)

    def get_state_hash(self) -> int:
        """Hash entire game state including racers, board, and semantic queue content."""
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

        roll_data = (self.roll_state.serial_id, self.roll_state.base_value)

        queue_data = tuple(
            sorted((se.event.phase, se.priority, repr(se.event)) for se in self.queue),
        )

        return hash((racer_data, board_data, roll_data, queue_data))


@dataclass(frozen=True)
class TurnOutcome:
    """Result of simulating exactly one turn for a specific racer."""

    vp_delta: list[int]  # per racer: final_vp - start_vp
    position: list[int]  # per racer final positions
    tripped: list[bool]  # per racer tripped flags at end of turn
    eliminated: list[bool]  # per racer eliminated flags at end of turn
    start_position: list[int]  # per racer start positions


@dataclass(slots=True)
class LogContext:
    """Per-game logging state."""

    engine_id: int
    engine_level: int

    total_turn: int = 0
    turn_log_count: int = 0
    current_racer_repr: str = "_"

    parent_engine_id: int | None = None

    def new_round(self):
        self.total_turn += 1

    def start_turn_log(self, racer_repr: str):
        self.turn_log_count = 0
        self.current_racer_repr = racer_repr

    def inc_log_count(self):
        self.turn_log_count += 1
