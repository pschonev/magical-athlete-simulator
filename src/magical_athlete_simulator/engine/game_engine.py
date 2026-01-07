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
    MainMoveSkippedEvent,
    MoveCmdEvent,
    PassingEvent,
    PerformMainRollEvent,
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
from magical_athlete_simulator.core.types import Source
from magical_athlete_simulator.engine.logging import ContextFilter
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
    from magical_athlete_simulator.core.types import AbilityName


AbilityCallback = Callable[[GameEvent, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


@dataclass(frozen=True)
class HeuristicKey:
    """Unique key for tracking loop states without relying on queue recursion."""

    board_hash: int
    event_type: type[GameEvent]
    target_idx: int | None
    responsible_idx: int | None


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    log_context: LogContext
    current_processing_event: ScheduledEvent | None = None
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)

    # LOOP DETECTION
    # 1. Heuristic History: Tracks (Board+Event) -> Min Queue Size
    heuristic_history: dict[HeuristicKey, int] = field(default_factory=dict)
    # 2. Creation Hashes: Maps Event.Serial -> BoardHash at creation time.
    #    Used to detect "Lagging" events that shouldn't trigger loop detection.
    event_creation_hashes: dict[int, int] = field(default_factory=dict)

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
        # Clear loop detection history at the start of every turn
        self.state.history.clear()
        self.heuristic_history.clear()
        self.event_creation_hashes.clear()

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
            # --- LAYER 1: Exact State Detection ---
            # Catches standard cycles (Scenario 2: Unproductive loops)
            current_hash = self.state.get_state_hash()

            if current_hash in self.state.history:
                # This is a strict cycle (Board + Queue are identical)
                skipped_sched = heapq.heappop(self.state.queue)
                # Cleanup auxiliary map
                self.event_creation_hashes.pop(skipped_sched.serial, None)

                self.log_warning(
                    f"Infinite loop detected (Exact State Cycle). Dropping recursive event: {skipped_sched.event}",
                )
                continue

            self.state.history.add(current_hash)

            # Peek the next event
            sched = heapq.heappop(self.state.queue)

            # Retrieve creation context
            creation_hash = self.event_creation_hashes.pop(sched.serial, None)

            # --- LAYER 2: Heuristic Detection (High-Water Mark) ---
            # Catches Exploding Queues (Scenario 3)
            # Checks if we are repeating work on the SAME board state.
            if self._check_heuristic_loop(sched, creation_hash):
                self.log_warning(
                    f"Infinite loop detected (Heuristic/Exploding). Dropping: {sched.event}",
                )
                continue

            # 3. Proceed
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

        # STALE EVENT CHECK:
        # If this event was created during a different board state, it is "lagging".
        # It represents a reaction to a past state, not a loop in the current state.
        # We allow it to resolve (drain).
        if creation_hash is not None and creation_hash != current_board_hash:
            return False

        ev = sched.event
        key = HeuristicKey(
            board_hash=current_board_hash,
            event_type=type(ev),
            target_idx=getattr(ev, "target_racer_idx", None),
            responsible_idx=getattr(ev, "responsible_racer_idx", None),
        )

        current_q_len = len(self.state.queue)

        if key in self.heuristic_history:
            prev_q_len = self.heuristic_history[key]

            # If we are back at the exact same state, processing the exact same event,
            # and the queue has not shrunk, we are spinning our wheels.
            if current_q_len >= prev_q_len:
                return True

            # If queue shrank (e.g. bouncing off walls), update high-water mark and proceed.
            self.heuristic_history[key] = current_q_len
            return False

        else:
            self.heuristic_history[key] = current_q_len
            return False

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

        # RECORD CREATION CONTEXT
        # We assume the current board state is the 'parent' of this event.
        # This helps us differentiate "lagging" events from "current loop" events later.
        self.event_creation_hashes[sched.serial] = self._calculate_board_hash()

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
