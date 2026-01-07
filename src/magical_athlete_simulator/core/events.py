from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Literal, Self, get_args

from magical_athlete_simulator.core.types import AbilityName, ModifierName, SystemSource

if TYPE_CHECKING:
    from collections.abc import Sequence

    from magical_athlete_simulator.core.state import TimingMode
    from magical_athlete_simulator.core.types import Source


class Phase(IntEnum):
    SYSTEM = 0
    PRE_MAIN = 10
    ROLL_DICE = 15
    ROLL_WINDOW = 18  # Hook for re-rolls
    MAIN_ACT = 20
    MOVE_EXEC = 21
    REACTION = 25


EventTriggerMode = Literal[
    "never",
    "immediately",
    "after_resolution",
]


@dataclass(frozen=True)
class GameEvent(ABC):
    responsible_racer_idx: int | None
    source: Source
    phase: Phase


@dataclass(frozen=True)
class EmitsAbilityTriggeredEvent:
    """Mixin for events that emit an AbilityTriggeredEvent"""

    emit_ability_triggered: EventTriggerMode


@dataclass(frozen=True)
class HasTargetRacer:
    """Mixin for events that have a racer as a target"""

    target_racer_idx: int


@dataclass(frozen=True)
class RacerFinishedEvent(GameEvent, HasTargetRacer):
    finishing_position: int  # 1st, 2nd, etc.


@dataclass(frozen=True, kw_only=True)
class TurnStartEvent(GameEvent, HasTargetRacer):
    phase: Phase = Phase.SYSTEM


@dataclass(frozen=True, kw_only=True)
class PerformMainRollEvent(GameEvent, HasTargetRacer):
    phase: Phase = Phase.ROLL_DICE


@dataclass(frozen=True, kw_only=True)
class RollModificationWindowEvent(GameEvent, HasTargetRacer):
    """
    Fired after a roll is calculated but before it is finalized.
    Listeners can inspect `engine.state.roll_state` and call `engine.trigger_reroll()`.
    """

    current_roll_val: int
    roll_serial: int
    phase: Phase = Phase.ROLL_WINDOW


@dataclass(frozen=True, kw_only=True)
class RollResultEvent(GameEvent, HasTargetRacer):
    """
    Fired exactly once per valid main roll, containing the final locked-in values.
    """

    base_value: int
    final_value: int
    phase: Phase = Phase.MAIN_ACT


@dataclass(frozen=True, kw_only=True)
class ResolveMainMoveEvent(GameEvent, HasTargetRacer):
    roll_serial: int
    phase: Phase = Phase.MAIN_ACT


@dataclass(frozen=True, kw_only=True)
class MainMoveSkippedEvent(GameEvent):
    responsible_racer_idx: int
    phase: Phase = Phase.ROLL_DICE


@dataclass(frozen=True, kw_only=True)
class PassingEvent(GameEvent):
    responsible_racer_idx: Annotated[int, "The ID of the racer that is passing"]
    target_racer_idx: Annotated[int, "The ID of the racer that is being passed."]
    tile_idx: int
    phase: Phase

    @property
    def passing_racer_idx(self) -> int:
        return self.responsible_racer_idx

    @property
    def passed_racer_idx(self) -> int:
        return self.target_racer_idx


@dataclass(frozen=True, kw_only=True)
class MoveCmdEvent(GameEvent, EmitsAbilityTriggeredEvent, HasTargetRacer):
    distance: int
    emit_ability_triggered: EventTriggerMode = "never"


@dataclass(frozen=True, kw_only=True)
class SimultaneousMoveCmdEvent(GameEvent, EmitsAbilityTriggeredEvent):
    """
    Atomically moves multiple racers.
    """

    moves: Sequence[tuple[int, int]]
    emit_ability_triggered: EventTriggerMode = "never"


@dataclass(frozen=True, kw_only=True)
class WarpCmdEvent(GameEvent, EmitsAbilityTriggeredEvent, HasTargetRacer):
    target_tile: int
    emit_ability_triggered: EventTriggerMode = "never"


@dataclass(frozen=True, kw_only=True)
class SimultaneousWarpCmdEvent(GameEvent, EmitsAbilityTriggeredEvent):
    warps: Sequence[tuple[int, int]]  # (racer_idx, target_tile)
    emit_ability_triggered: EventTriggerMode = "never"


@dataclass(frozen=True)
class TripCmdEvent(GameEvent, EmitsAbilityTriggeredEvent, HasTargetRacer): ...


@dataclass(frozen=True)
class TripRecoveryEvent(GameEvent, HasTargetRacer):
    phase: Phase = Phase.PRE_MAIN


@dataclass(frozen=True)
class PreMoveEvent(GameEvent, HasTargetRacer):
    start_tile: int
    distance: int


@dataclass(frozen=True)
class PreWarpEvent(GameEvent, HasTargetRacer):
    start_tile: int
    target_tile: int


@dataclass(frozen=True)
class PostMoveEvent(GameEvent, HasTargetRacer):
    start_tile: int
    end_tile: int


@dataclass(frozen=True)
class PostWarpEvent(GameEvent, HasTargetRacer):
    start_tile: int
    end_tile: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    responsible_racer_idx: int
    source: AbilityName | ModifierName
    target_racer_idx: int | None = None

    @classmethod
    def from_event(cls, event: GameEvent) -> Self:
        if event.responsible_racer_idx is None:
            raise ValueError(
                "Expected source racer ID in AbilityTriggeredEvent but got None.",
            )
        if event.source in get_args(SystemSource):
            msg = f"Expected source ability/modifier in AbilityTriggeredEvent but got {event.source}"
            raise ValueError(
                msg,
            )
        return cls(
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,  # pyright: ignore[reportArgumentType]
            phase=event.phase,
            target_racer_idx=event.target_racer_idx
            if isinstance(event, HasTargetRacer)
            else None,
        )


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)
    modifier_sources: list[tuple[str, int]] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_amount + sum(self.modifiers))


@dataclass(order=False)
class ScheduledEvent:
    depth: int
    priority: int
    serial: int
    event: GameEvent
    mode: TimingMode = "FLAT"

    @cached_property
    def sort_key(self):
        """Calculates the comparison tuple once per instance."""
        if self.mode == "FLAT":
            # Ignore depth
            return (self.event.phase, 0, self.priority, self.serial)

        if self.mode == "BFS":
            # Phase -> Depth (Ascending/Ripple) -> Priority
            return (self.event.phase, self.depth, self.priority, self.serial)

        if self.mode == "DFS":
            # Phase -> Depth (Descending/Rabbit Hole) -> Priority
            # We use -depth because small numbers come first in heaps.
            return (self.event.phase, -self.depth, self.priority, self.serial)

        return (self.event.phase, 0, self.priority, self.serial)

    def __lt__(self, other: Self) -> bool:
        # Extremely fast comparison of pre-calculated tuples
        return self.sort_key < other.sort_key


AbilityTriggeredEventOrSkipped = Literal["skip_trigger"] | AbilityTriggeredEvent
