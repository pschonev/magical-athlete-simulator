from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypeVar

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    TripRecoveryEvent,
)
from magical_athlete_simulator.simulation.db.models import RacerResult

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import (
        AbilityName,
        ModifierName,
    )
    from magical_athlete_simulator.engine.game_engine import GameEngine


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
class TurnRecord:
    """Lightweight record of a single turn's key outcome."""

    turn_index: int
    racer_idx: int
    dice_roll: int


@dataclass(slots=True)
class MetricsAggregator:
    """
    Accumulates stats directly into RacerResult objects.
    """

    config_hash: str

    # We store the RacerResult objects here, keyed by racer_idx
    results: dict[int, RacerResult] = field(default_factory=dict)
    turn_history: list[TurnRecord] = field(default_factory=list)

    def initialize_racers(self, engine: GameEngine) -> None:
        """
        Pre-populate results for all racers in the engine.
        MUST be called before processing events.
        """
        for racer in engine.state.racers:
            self.results[racer.idx] = RacerResult(
                config_hash=self.config_hash,
                racer_id=racer.idx,
                racer_name=racer.name,
            )

    def _get_result(self, racer_idx: int) -> RacerResult:
        """
        Retrieve existing result object.
        Raises KeyError if racer was not initialized.
        """
        return self.results[racer_idx]

    def on_event(self, event: GameEvent) -> None:
        """Count specific events."""
        if isinstance(event, AbilityTriggeredEvent):
            stats = self._get_result(event.responsible_racer_idx)
            stats.ability_trigger_count += 1

            if event.responsible_racer_idx == event.target_racer_idx:
                stats.ability_self_target_count += 1

            if (
                event.target_racer_idx is not None
                and event.target_racer_idx != event.responsible_racer_idx
            ):
                target_stats = self._get_result(event.target_racer_idx)
                target_stats.ability_target_count += 1

        if isinstance(event, TripRecoveryEvent):
            stats = self._get_result(event.target_racer_idx)
            stats.recovery_turns += 1

    def on_turn_end(
        self,
        engine: GameEngine,
        *,
        turn_index: int,
        active_racer_idx: int | None = None,
    ) -> None:
        """Update stats at the end of a turn."""
        racer_idx = (
            active_racer_idx
            if active_racer_idx is not None
            else engine.state.current_racer_idx
        )
        if racer_idx < 0 or racer_idx >= len(engine.state.racers):
            return

        roll_val = engine.state.roll_state.base_value

        stats = self._get_result(racer_idx)
        stats.turns_taken += 1
        stats.sum_dice_rolled += roll_val

        self.turn_history.append(
            TurnRecord(turn_index=turn_index, racer_idx=racer_idx, dice_roll=roll_val),
        )

    def finalize_metrics(self, engine: GameEngine) -> list[RacerResult]:
        """
        Finalize values that are simply snapshots of the end state (VP, position).
        Returns the list of RacerResult objects ready for DB insertion.
        """
        output: list[RacerResult] = []
        for racer in engine.state.racers:
            # We trust initialize_racers was called; if this fails, we want to crash loudly
            stats = self._get_result(racer.idx)

            # Update final snapshot values
            stats.final_vp = racer.victory_points
            stats.finished = racer.finished
            stats.finish_position = racer.finish_position
            stats.eliminated = racer.eliminated

            output.append(stats)

        return output
