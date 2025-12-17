from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, ModifierName


class Phase(IntEnum):
    SYSTEM = 0
    PRE_MAIN = 10
    ROLL_DICE = 15
    ROLL_WINDOW = 18  # Hook for re-rolls
    MAIN_ACT = 20
    BOARD = 22
    REACTION = 25
    MOVE_EXEC = 30


class GameEvent:
    pass


@dataclass(frozen=True)
class RacerFinishedEvent(GameEvent):
    racer_idx: int
    finishing_position: int  # 1st, 2nd, etc.


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class PerformRollEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollModificationWindowEvent(GameEvent):
    """
    Fired after a roll is calculated but before it is finalized.
    Listeners can inspect `engine.state.roll_state` and call `engine.trigger_reroll()`.
    """

    racer_idx: int
    current_roll_val: int
    roll_serial: int


@dataclass(frozen=True)
class ResolveMainMoveEvent(GameEvent):
    racer_idx: int
    roll_serial: int


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    victim_idx: int
    tile_idx: int


@dataclass(frozen=True)
class MoveCmdEvent(GameEvent):
    racer_idx: int
    distance: int
    source: str
    phase: int


@dataclass(frozen=True)
class WarpCmdEvent(GameEvent):
    racer_idx: int
    target_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class TripCmdEvent(GameEvent):
    racer_idx: int
    source: str


@dataclass(frozen=True)
class PreMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    distance: int
    source: str
    phase: int


@dataclass(frozen=True)
class PreWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    target_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int | None
    ability_name: AbilityName | ModifierName | str
    # Human-readable context for logs
    log_context: str


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)
    modifier_sources: list[tuple[str, int]] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_amount + sum(self.modifiers))


@dataclass(order=True)
class ScheduledEvent:
    phase: int
    priority: int
    serial: int
    event: GameEvent = field(compare=False)
