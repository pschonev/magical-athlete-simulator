from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypeVar

from magical_athlete_simulator.core.events import AbilityTriggeredEvent

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine

EventT = TypeVar("EventT", bound=object)


class LogSource(Protocol):
    def export_text(self) -> str: ...
    def export_html(self) -> str: ...


@dataclass(frozen=True, slots=True)
class SnapshotPolicy:
    snapshot_event_types: tuple[type[object], ...] = ()
    ensure_snapshot_each_turn: bool = True
    fallback_event_name: str = "TurnSkipped/Recovery"
    snapshot_on_turn_end: bool = False
    turn_end_event_name: str = "TurnEnd"


@dataclass(frozen=True, slots=True)
class StepSnapshot:
    global_step_index: int
    turn_index: int
    event_name: str

    positions: list[int]
    tripped: list[bool]
    vp: list[int]

    last_roll: int
    current_racer: int
    names: list[str]

    modifiers: list[list[AbilityName | ModifierName]]
    abilities: list[list[AbilityName]]

    log_html: str
    log_line_index: int


@dataclass(slots=True)
class SnapshotRecorder:
    policy: SnapshotPolicy
    log_source: LogSource

    step_history: list[StepSnapshot] = field(default_factory=list)
    turn_map: dict[int, list[int]] = field(default_factory=dict)

    # Internal per-turn bookkeeping:
    _turn_step_counts: dict[int, int] = field(default_factory=dict)

    def on_event(
        self,
        engine: GameEngine,
        event: GameEvent,
        *,
        turn_index: int,
    ) -> None:
        if isinstance(event, self.policy.snapshot_event_types):
            self.capture(engine, event.__class__.__name__, turn_index=turn_index)

    def on_turn_end(self, engine: GameEngine, *, turn_index: int) -> None:
        if self.policy.snapshot_on_turn_end:
            self.capture(engine, self.policy.turn_end_event_name, turn_index=turn_index)

        if (
            self.policy.ensure_snapshot_each_turn
            and self._turn_step_counts.get(turn_index, 0) == 0
        ):
            self.capture(engine, self.policy.fallback_event_name, turn_index=turn_index)

    def capture(self, engine: GameEngine, event_name: str, *, turn_index: int) -> None:
        current_logs_text = self.log_source.export_text()
        log_line_index = max(0, current_logs_text.count("\n") - 1)
        current_logs_html = self.log_source.export_html()

        snapshot = StepSnapshot(
            global_step_index=len(self.step_history),
            turn_index=turn_index,
            event_name=event_name,
            positions=[r.position for r in engine.state.racers],
            tripped=[r.tripped for r in engine.state.racers],
            vp=[r.victory_points for r in engine.state.racers],
            last_roll=engine.state.roll_state.base_value,
            current_racer=engine.state.current_racer_idx,
            names=[r.name for r in engine.state.racers],
            modifiers=[[m.name for m in r.modifiers] for r in engine.state.racers],
            abilities=[sorted(r.active_abilities) for r in engine.state.racers],
            log_html=current_logs_html,
            log_line_index=log_line_index,
        )

        self.step_history.append(snapshot)
        self.turn_map.setdefault(turn_index, []).append(snapshot.global_step_index)
        self._turn_step_counts[turn_index] = (
            self._turn_step_counts.get(turn_index, 0) + 1
        )


@dataclass(slots=True)
class AbilityTriggerCounter:
    """
    Counts ability triggers per racer for events that carry:
      - event.responsible_racer_idx
    """

    counts: dict[int, int] = field(default_factory=dict)

    def on_event(self, event: GameEvent) -> None:
        if isinstance(event, AbilityTriggeredEvent):
            idx = event.responsible_racer_idx
            self.counts[idx] = self.counts.get(idx, 0) + 1
