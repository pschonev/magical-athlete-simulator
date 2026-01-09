from __future__ import annotations

import heapq
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from magical_athlete_simulator.ai.smart_agent import SmartAgent
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    EmitsAbilityTriggeredEvent,
    GameEvent,
    HasTargetRacer,
    MainMoveSkippedEvent,
    MoveCmdEvent,
    PassingEvent,
    PerformMainRollEvent,
    Phase,
    RacerFinishedEvent,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
    ScheduledEvent,
    SimultaneousMoveCmdEvent,
    SimultaneousWarpCmdEvent,
    TripCmdEvent,
    TripRecoveryEvent,
    TurnStartEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.engine.logging import ContextFilter
from magical_athlete_simulator.engine.loop_detection import LoopDetector
from magical_athlete_simulator.engine.movement import (
    handle_move_cmd,
    handle_simultaneous_move_cmd,
    handle_simultaneous_warp_cmd,
    handle_trip_cmd,
    handle_warp_cmd,
)
from magical_athlete_simulator.engine.roll import (
    handle_perform_main_roll,
    resolve_main_move,
)
from magical_athlete_simulator.racers import get_ability_classes

if TYPE_CHECKING:
    import random

    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import (
        GameState,
        LogContext,
        RacerState,
    )
    from magical_athlete_simulator.core.types import AbilityName, ErrorCode, Source

HEURISTIC_LOOP_MAXIMUM = 5
HARD_LIMIT_BOARD_STATE = 200

AbilityCallback = Callable[[GameEvent, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    log_context: LogContext
    current_processing_event: ScheduledEvent | None = None
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)

    # errors and loop detection
    bug_reason: ErrorCode | None = None
    loop_detector: LoopDetector = field(default_factory=LoopDetector)

    # Callback for external observers
    on_event_processed: Callable[[GameEngine, GameEvent], None] | None = None
    verbose: bool = True
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Assigns starting abilities to all racers and fires on_gain hooks."""
        base = logging.getLogger("magical_athlete")  # or LOGGER_NAME
        self._logger = base.getChild(f"engine.{id(self)}")

        if self.verbose:
            self._logger.addFilter(ContextFilter(self))

        # Assign starting abilities
        for racer in self.state.racers:
            initial = RACER_ABILITIES.get(racer.name, set())
            self.update_racer_abilities(racer.idx, initial)

        for racer in self.state.racers:
            _ = self.agents.setdefault(racer.idx, SmartAgent())

    # --- Main Loop ---
    def run_race(self):
        while not self.state.race_over:
            self.run_turn()
            self._advance_turn()

    def run_turn(self):
        self.loop_detector.reset_for_turn()
        self.state.history.clear()

        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        racer.reroll_count = 0

        self.log_context.start_turn_log(racer.repr)
        self.log_info(f"=== START TURN: {racer.repr} ===")
        racer.main_move_consumed = False

        if racer.tripped:
            self.log_info(f"{racer.repr} recovers from Trip.")
            racer.tripped = False
            racer.main_move_consumed = True
            self.push_event(
                TripRecoveryEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
            self.push_event(
                TurnStartEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
        else:
            self.push_event(
                TurnStartEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
            self.push_event(
                PerformMainRollEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )

        while self.state.queue and not self.state.race_over:
            current_board_hash = self._calculate_board_hash()
            current_system_hash = self.state.get_state_hash()

            # --- Layer 1: Exact State Cycle (Least Harmful) ---
            # Checks if the entire system (Board + Queue) is in a recursive loop.
            if self.loop_detector.check_exact_cycle(current_system_hash):
                skipped = heapq.heappop(self.state.queue)
                self.loop_detector.forget_event(skipped.serial)
                self.log_warning(
                    f"Infinite loop detected (Exact State Cycle). Dropping recursive event: {skipped.event}",
                )
                continue

            # Pop the next event to analyze it against Heuristics
            sched = heapq.heappop(self.state.queue)

            # --- Layer 2: Heuristic Detection (Surgical Fix) ---
            # Checks for logical loops (e.g. oscillating moves) where queue grows/stagnates.
            if self.loop_detector.check_heuristic_loop(
                current_board_hash,
                len(self.state.queue),
                sched,
            ):
                self.log_warning(
                    f"MINOR_LOOP_DETECTED (Heuristic/Exploding). Dropping: {sched.event}",
                )
                # Ensure we don't downgrade a critical error
                self.bug_reason = (
                    "MINOR_LOOP_DETECTED"
                    if self.bug_reason != "CRITICAL_LOOP_DETECTED"
                    else self.bug_reason
                )
                continue

            # --- Layer 3: Global Sanity Check (Nuclear Option) ---
            # Failsafe: If the board keeps resetting despite the checks above, abort the turn.
            if self.loop_detector.check_global_sanity(current_board_hash):
                self.log_error(
                    "CRITICAL_LOOP_DETECTED: Board state oscillation limit exceeded. Aborting turn.",
                )
                self.state.queue.clear()
                self.bug_reason = "CRITICAL_LOOP_DETECTED"
                break

            self.current_processing_event = sched
            self._handle_event(sched.event)

    def _check_heuristic_loop(
        self,
        sched: ScheduledEvent,
        creation_hash: int | None,
    ) -> bool:
        """
        Returns True if a heuristic loop is detected.
        """
        current_board_hash = self._calculate_board_hash()

        # 1. LAG CHECK: If the event is old (created in a previous state), let it drain.
        if creation_hash is not None and creation_hash != current_board_hash:
            return False

        ev = sched.event

        # 2. KEY GENERATION: Now includes PHASE
        key = HeuristicKey(
            board_hash=current_board_hash,
            event_type=type(ev),
            target_idx=ev.target_racer_idx if isinstance(ev, HasTargetRacer) else None,
            responsible_idx=ev.responsible_racer_idx,
            phase=ev.phase,
        )

        current_q_len = len(self.state.queue)

        # 3. HISTORY TRACKING
        if key not in self.heuristic_history:
            self.heuristic_history[key] = LoopTrackingData(current_q_len, 1)
            return False

        data = self.heuristic_history[key]

        # 4. PROGRESS CHECK: Has the queue shrunk?
        # If queue got smaller, we are processing items successfully. Reset strikes.
        if current_q_len < data.min_queue_len:
            data.min_queue_len = current_q_len
            data.visit_count = 1
            return False

        # 5. STRIKE SYSTEM
        # Queue is same size or bigger -> Possible Loop.
        data.visit_count += 1

        # ONLY trigger if we have failed to make progress X times in a row.
        return data.visit_count > HEURISTIC_LOOP_MAXIMUM

    def _calculate_board_hash(self) -> int:
        """
        Generates a hash of the physical board state.
        Excludes the Event Queue and History.
        """
        racer_states = tuple(
            (
                r.position,
                r.active,
                r.tripped,
                r.main_move_consumed,
                r.reroll_count,
                frozenset(r.active_abilities.keys()),
            )
            for r in self.state.racers
        )
        return hash((self.state.current_racer_idx, racer_states))

    def _advance_turn(self):
        if self.state.race_over:
            return

        # 1. Handle Turn Override
        if self.state.next_turn_override is not None:
            next_idx = self.state.next_turn_override
            self.state.next_turn_override = None
            self.state.current_racer_idx = next_idx
            self.log_info(
                f"Turn Order Override: {self.get_racer(next_idx).repr} takes the next turn!",
            )
            return

        # 2. Standard Clockwise Logic
        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n

        start_search = next_idx
        while not self.state.racers[next_idx].active:
            next_idx = (next_idx + 1) % n
            if next_idx == start_search:
                self.state.race_over = True
                return

        # 3. Detect New Round
        if next_idx < curr:
            self.log_context.new_round()

        self.state.current_racer_idx = next_idx

    # --- Event Management ---
    def push_event(self, event: GameEvent, priority: int | None = None):
        if priority is not None:
            _priority = priority
        elif event.responsible_racer_idx is None:
            if (
                isinstance(event, EmitsAbilityTriggeredEvent)
                and event.emit_ability_triggered != "never"
            ):
                msg = f"Received a {event.__class__.__name__} with no responsible racer ID..."
                raise ValueError(msg)
            _priority = 0
        else:
            curr = self.state.current_racer_idx
            count = len(self.state.racers)
            _priority = 1 + ((event.responsible_racer_idx - curr) % count)

        if (
            self.current_processing_event
            and self.current_processing_event.event.phase == event.phase
        ):
            if self.current_processing_event.priority == 0:
                new_depth = self.current_processing_event.depth
            else:
                new_depth = self.current_processing_event.depth + 1
        else:
            new_depth = 0

        self.state.serial += 1
        sched = ScheduledEvent(
            new_depth,
            _priority,
            self.state.serial,
            event,
            mode=self.state.rules.timing_mode,
        )

        # Notify loop detector of the board state at creation time
        self.loop_detector.record_event_creation(
            sched.serial,
            self._calculate_board_hash(),
        )

        msg = f"{sched}"
        self.log_debug(msg)
        heapq.heappush(self.state.queue, sched)

        if (
            isinstance(event, EmitsAbilityTriggeredEvent)
            and event.emit_ability_triggered == "immediately"
        ):
            self.push_event(AbilityTriggeredEvent.from_event(event))

    def _rebuild_subscribers(self):
        self.subscribers.clear()
        for racer in self.state.racers:
            for ability in racer.active_abilities.values():
                ability.register(self, racer.idx)

    def subscribe(
        self,
        event_type: type[GameEvent],
        callback: AbilityCallback,
        owner_idx: int,
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        racer = self.get_racer(racer_idx)
        current_instances = racer.active_abilities
        old_names = set(current_instances.keys())

        removed = old_names - new_abilities
        added = new_abilities - old_names

        for name in removed:
            instance = current_instances.pop(name)
            if isinstance(instance, LifecycleManagedMixin):
                instance.__class__.on_loss(self, racer_idx)

            for event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub
                    for sub in self.subscribers[event_type]
                    if not (
                        sub.owner_idx == racer_idx
                        and getattr(sub.callback, "__self__", None) == instance
                    )
                ]

        for name in added:
            ability_cls = get_ability_classes().get(name)
            if ability_cls:
                instance = ability_cls(name=name)
                instance.register(self, racer_idx)
                current_instances[name] = instance
                if isinstance(instance, LifecycleManagedMixin):
                    instance.__class__.on_gain(self, racer_idx)

    def publish_to_subscribers(self, event: GameEvent):
        if type(event) not in self.subscribers:
            return
        subs = self.subscribers[type(event)]
        curr = self.state.current_racer_idx
        count = len(self.state.racers)
        ordered_subs = sorted(subs, key=lambda s: (s.owner_idx - curr) % count)

        for sub in ordered_subs:
            sub.callback(event, sub.owner_idx, self)

    def _handle_event(self, event: GameEvent):
        match event:
            case (
                TurnStartEvent()
                | PassingEvent()
                | AbilityTriggeredEvent()
                | RollModificationWindowEvent()
                | RacerFinishedEvent()
            ):
                self.publish_to_subscribers(event)
            case TripCmdEvent():
                handle_trip_cmd(self, event)
            case MoveCmdEvent():
                handle_move_cmd(self, event)
            case SimultaneousMoveCmdEvent():
                handle_simultaneous_move_cmd(self, event)
            case WarpCmdEvent():
                handle_warp_cmd(self, event)
            case SimultaneousWarpCmdEvent():
                handle_simultaneous_warp_cmd(self, event)

            case PerformMainRollEvent():
                handle_perform_main_roll(self, event)

            case ResolveMainMoveEvent():
                self.publish_to_subscribers(event)
                resolve_main_move(self, event)

            case _:
                pass

        if self.on_event_processed:
            self.on_event_processed(self, event)

    # -- Getters --
    def get_agent(self, racer_idx: int) -> Agent:
        return self.agents[racer_idx]

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def get_racer_pos(self, idx: int) -> int:
        return self.state.racers[idx].position

    def get_racers_at_position(
        self,
        tile_idx: int,
        except_racer_idx: int | None = None,
    ) -> list[RacerState]:
        if except_racer_idx is None:
            return [r for r in self.state.racers if r.position == tile_idx and r.active]
        else:
            return [
                r
                for r in self.state.racers
                if r.position == tile_idx and r.idx != except_racer_idx and r.active
            ]

    def skip_main_move(self, racer_idx: int, source: Source) -> None:
        """
        Marks the racer's main move as consumed and emits a notification event.
        Does nothing if the move was already consumed.
        """
        racer = self.get_racer(racer_idx)
        if not racer.main_move_consumed:
            racer.main_move_consumed = True
            self.log_info(
                f"{racer.repr} has their main move skipped (Source: {source}).",
            )
            self.push_event(
                MainMoveSkippedEvent(
                    responsible_racer_idx=racer_idx,
                    source=source,
                ),
            )

    # -- Logging --
    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        if not self.verbose:
            return
        self._logger.log(level, msg, *args, **kwargs)

    def log_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def log_info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def log_warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def log_error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)
