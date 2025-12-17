import heapq
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from magical_athlete_simulator.ai.smart_agent import SmartAgent
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveCmdEvent,
    PassingEvent,
    PerformRollEvent,
    Phase,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
    ScheduledEvent,
    TripCmdEvent,
    TurnStartEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.engine.logging import ContextFilter
from magical_athlete_simulator.engine.movement import (
    handle_move_cmd,
    handle_trip_cmd,
    handle_warp_cmd,
)
from magical_athlete_simulator.engine.roll import handle_perform_roll, resolve_main_move
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


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    log_context: LogContext
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)

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

        # Rebuild subscribers
        self._rebuild_subscribers()

        for racer in self.state.racers:
            _ = self.agents.setdefault(racer.idx, SmartAgent(self.state.board))

    # --- Main Loop ---
    def run_race(self):
        while not self.state.race_over:
            self.run_turn()
            self._advance_turn()

    def run_turn(self):
        self.state.history.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        racer.reroll_count = 0

        self.log_context.start_turn_log(racer.repr)
        self.log_info(f"=== START TURN: {racer.repr} ===")

        if racer.tripped:
            self.log_info(f"{racer.repr} recovers from Trip.")
            racer.tripped = False
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
        else:
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
            self.push_event(PerformRollEvent(cr), phase=Phase.ROLL_DICE)

        while self.state.queue and not self.state.race_over:
            sched = heapq.heappop(self.state.queue)

            # Loop Detection
            state_hash = self.state.get_state_hash()
            event_sig = hash(repr(sched.event))
            if (state_hash, event_sig) in self.state.history:
                self.log_warning(f"Loop detected for {sched.event}. Discarding.")
                continue
            self.state.history.add((state_hash, event_sig))

            self._handle_event(sched.event)

    def _advance_turn(self):
        if self.state.race_over:
            return
        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n
        while not self.state.racers[next_idx].active:  # Skip finished/eliminated
            next_idx = (next_idx + 1) % n
            if next_idx == curr:
                break
        if next_idx < curr:
            self.log_context.new_round()
        self.state.current_racer_idx = next_idx

    # --- Event Management ---
    def push_event(self, event: GameEvent, *, phase: int):
        self.state.serial += 1
        sched = ScheduledEvent(phase, 0, self.state.serial, event)
        heapq.heappush(self.state.queue, sched)

    def _rebuild_subscribers(self):
        """Rebuild event subscriptions from each racer's active_abilities."""
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

        # 1. Handle Removed
        for name in removed:
            instance = current_instances.pop(name)

            if isinstance(instance, LifecycleManagedMixin):
                instance.__class__.on_loss(self, racer_idx)

            # Selective Unsubscribe
            for event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub
                    for sub in self.subscribers[event_type]
                    if not (
                        sub.owner_idx == racer_idx
                        and getattr(sub.callback, "__self__", None) == instance
                    )
                ]

        # 2. Handle Added
        for name in added:
            ability_cls = get_ability_classes().get(name)
            if ability_cls:
                instance = ability_cls()

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
        # Ordered iteration: Start from current player, go clockwise
        ordered_subs = sorted(subs, key=lambda s: (s.owner_idx - curr) % count)

        for sub in ordered_subs:
            # If a re-roll happened mid-loop during a Window event, we might want to abort
            # further listeners for this specific serial, but simplified here:
            sub.callback(event, sub.owner_idx, self)

    def _handle_event(self, event: GameEvent):
        match event:
            case (
                TurnStartEvent()
                | PassingEvent()
                | AbilityTriggeredEvent()
                | RollModificationWindowEvent()
            ):
                self.publish_to_subscribers(event)
            case TripCmdEvent():
                handle_trip_cmd(self, event)
            case MoveCmdEvent():
                handle_move_cmd(self, event)

            case WarpCmdEvent():
                handle_warp_cmd(self, event)

            case PerformRollEvent():
                handle_perform_roll(self, event)

            case ResolveMainMoveEvent():
                resolve_main_move(self, event)

            case _:
                pass

    # -- Getters for convencience --
    def get_agent(self, racer_idx: int) -> Agent:
        return self.agents[racer_idx]

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def get_racer_pos(self, idx: int) -> int:
        return self.state.racers[idx].position

    # -- Logging --
    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Core logging helper; respects engine verbosity."""
        if not self.verbose:
            return
        # Delegate to underlying logger; *args/kwargs support normal %-formatting or extra=
        self._logger.log(level, msg, *args, **kwargs)

    def log_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def log_info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def log_warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def log_error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)
