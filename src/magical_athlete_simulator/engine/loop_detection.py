from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent, ScheduledEvent

# --- Configuration ---
MAX_IDENTICAL_BOARD_VISITS = 200  # Threshold for physical board state oscillations
HEURISTIC_LOOP_TOLERANCE = 5  # Threshold for repeated actions on the same state


@dataclass(frozen=True)
class HeuristicKey:
    """
    Composite key used to detect logical loops where the board state resets
    but the event queue grows or stagnates (e.g., oscillating moves).
    """

    board_hash: int
    event_type: type[GameEvent]
    target_idx: int | None
    responsible_idx: int | None
    phase: int | None


@dataclass
class LoopTrackingData:
    """Tracks queue metrics for a specific heuristic state."""

    min_queue_len: int
    visit_count: int


@dataclass
class LoopDetector:
    """
    Manages multi-layered loop detection strategies.

    Strategies:
    1. Exact Cycle: Detects identical system snapshots (Board + Queue) to prune strict recursion.
    2. Heuristic: Detects logical loops (e.g., ping-ponging) where state reverts but queue size creates a new snapshot.
    3. Global Sanity: Failsafe that aborts the turn if the board physically oscillates too many times.
    """

    # Global Sanity State
    board_visit_counts: Counter[int] = field(default_factory=Counter)
    last_board_hash: int | None = None

    # Exact Cycle State
    exact_state_history: set[int] = field(default_factory=set)

    # Heuristic State
    heuristic_history: dict[HeuristicKey, LoopTrackingData] = field(
        default_factory=dict
    )
    event_creation_hashes: dict[int, int] = field(default_factory=dict)

    def reset_for_turn(self) -> None:
        """Resets all tracking history for a new turn."""
        self.board_visit_counts.clear()
        self.last_board_hash = None
        self.exact_state_history.clear()
        self.heuristic_history.clear()
        self.event_creation_hashes.clear()

    def record_event_creation(self, serial: int, board_hash: int) -> None:
        """Associates an event serial with the board state at its creation time."""
        self.event_creation_hashes[serial] = board_hash

    def forget_event(self, serial: int) -> None:
        """Cleans up tracking data for an event that was discarded or skipped."""
        self.event_creation_hashes.pop(serial, None)

    def check_exact_cycle(self, state_hash: int) -> bool:
        """
        Layer 1 (Exact): Returns True if this precise Board+Queue configuration has occurred before.
        Used to catch strict recursion loops immediately.
        """
        if state_hash in self.exact_state_history:
            return True
        self.exact_state_history.add(state_hash)
        return False

    def check_heuristic_loop(
        self, current_board_hash: int, current_queue_len: int, sched: ScheduledEvent
    ) -> bool:
        """
        Layer 2 (Heuristic): Returns True if the same event is being processed on the same
        board state repeatedly without queue progress. Handles 'exploding' queues.
        """
        creation_hash = self.event_creation_hashes.pop(sched.serial, None)

        # Ignore events created during a different board state (lagging reactions)
        if creation_hash is not None and creation_hash != current_board_hash:
            return False

        ev = sched.event
        key = HeuristicKey(
            board_hash=current_board_hash,
            event_type=type(ev),
            target_idx=getattr(ev, "target_racer_idx", None),
            responsible_idx=getattr(ev, "responsible_racer_idx", None),
            phase=getattr(ev, "phase", None),
        )

        if key not in self.heuristic_history:
            self.heuristic_history[key] = LoopTrackingData(current_queue_len, 1)
            return False

        data = self.heuristic_history[key]

        # If queue has shrunk, we are making progress; reset strikes
        if current_queue_len < data.min_queue_len:
            data.min_queue_len = current_queue_len
            data.visit_count = 1
            return False

        # If queue is stable or growing, record a strike
        data.visit_count += 1
        return data.visit_count > HEURISTIC_LOOP_TOLERANCE

    def check_global_sanity(self, current_board_hash: int) -> bool:
        """
        Layer 3 (Global): Returns True if the board state has oscillated too many times
        in total during this turn. Acts as a final failsafe.
        """
        # Only increment count on state entry/re-entry
        if current_board_hash != self.last_board_hash:
            self.board_visit_counts[current_board_hash] += 1
            self.last_board_hash = current_board_hash

        return self.board_visit_counts[current_board_hash] > MAX_IDENTICAL_BOARD_VISITS
