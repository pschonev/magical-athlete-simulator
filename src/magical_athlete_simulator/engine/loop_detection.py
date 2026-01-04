from collections import defaultdict
from dataclasses import dataclass, field

from magical_athlete_simulator.core.events import (
    GameEvent,
    HasTargetRacer,
    ScheduledEvent,
)
from magical_athlete_simulator.core.state import GameState
from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class LoopDetectionState:
    """Tracks multiple levels of loop detection simultaneously."""

    # Level 1: Full state hash (includes queue) - catches simple unproductive loops
    full_state_history: set[int] = field(default_factory=set)

    # Level 2: Positional state tracking - catches loops where queue grows
    # Maps (racer_positions, active_racers, current_phase) -> repetition count
    positional_state_count: dict[tuple, int] = field(
        default_factory=lambda: defaultdict(int)
    )

    # Level 3: Event frequency tracking - catches rapid repetition of same event types
    # Maps (event_type, target_racer, source) -> list of serial numbers when seen
    event_frequency: dict[tuple, list[int]] = field(
        default_factory=lambda: defaultdict(list)
    )

    # Configuration
    max_positional_repeats: int = 3  # Allow same board position X times before flagging
    event_window_size: int = 50  # Look at last N serials
    max_event_frequency: int = 10  # Max times same event in window

    def clear_for_new_turn(self):
        """Reset between turns."""
        self.full_state_history.clear()
        self.positional_state_count.clear()
        self.event_frequency.clear()


def get_positional_hash(state: GameState) -> tuple[tuple[int, int, bool, bool, bool]]:
    """
    Create a hash of just the positional/status data, ignoring the event queue.
    This catches loops where the queue keeps growing but positions cycle.
    """
    racer_data = tuple(
        (r.idx, r.position, r.active, r.tripped, r.main_move_consumed)
        for r in state.racers
    )
    return (
        racer_data,
        state.current_racer_idx,
        # Include the phase of the top event if queue exists
        state.queue[0].event.phase if state.queue else None,
    )


def get_event_signature(event: GameEvent) -> tuple:
    """Create a signature for tracking event frequency."""
    return (
        type(event).__name__,
        event.target_racer_idx if isinstance(event, HasTargetRacer) else None,
        event.source,
    )


def check_for_loops(
    engine: GameEngine,
    scheduled_event: ScheduledEvent,
) -> tuple[bool, str | None]:
    """
    Multi-level loop detection. Returns (should_skip, reason).

    Returns (True, reason) if a loop is detected and event should be skipped.
    Returns (False, None) if no loop detected.
    """
    state = engine.state
    loop_state = state.loop_detection

    # ============================================================================
    # LEVEL 1: Full State Hash (Most Precise)
    # ============================================================================
    # Catches unproductive loops where exact same state recurs
    # This is your original detection - keep it!
    current_full_hash = state.get_state_hash()

    if current_full_hash in loop_state.full_state_history:
        return True, "Exact state repetition (full hash match)"

    loop_state.full_state_history.add(current_full_hash)

    # ============================================================================
    # LEVEL 2: Positional State Repetition (Growing Queue Detection)
    # ============================================================================
    # Catches loops where queue grows but positions cycle
    # Example: Romantic + Scoocher + MoveDeltaTile creating expanding event chains
    positional_hash = get_positional_hash(state)
    loop_state.positional_state_count[positional_hash] += 1

    repeat_count = loop_state.positional_state_count[positional_hash]
    if repeat_count > loop_state.max_positional_repeats:
        # We've seen this exact board position too many times in this turn
        return True, f"Positional loop detected (seen {repeat_count} times)"

    # ============================================================================
    # LEVEL 3: Event Frequency Analysis (Rapid Repetition)
    # ============================================================================
    # Catches when the same type of event fires too frequently
    # Helps catch cascading ability triggers
    event_sig = get_event_signature(scheduled_event.event)
    serial = state.serial

    loop_state.event_frequency[event_sig].append(serial)

    # Only look at recent events (sliding window)
    recent_serials = [
        s
        for s in loop_state.event_frequency[event_sig]
        if s >= serial - loop_state.event_window_size
    ]
    loop_state.event_frequency[event_sig] = recent_serials

    if len(recent_serials) > loop_state.max_event_frequency:
        return (
            True,
            f"Event frequency loop (same event {len(recent_serials)} times in window)",
        )

    # ============================================================================
    # LEVEL 4: Depth Limit (Circuit Breaker)
    # ============================================================================
    # Ultimate safety net - if event chain goes too deep, something is wrong
    max_depth = 150  # Adjust based on your game's needs
    if scheduled_event.depth > max_depth:
        return (
            True,
            f"Maximum event depth exceeded ({scheduled_event.depth} > {max_depth})",
        )

    # No loop detected
    return False, None


# ============================================================================
# Integration into GameEngine
# ============================================================================
