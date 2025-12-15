from dataclasses import dataclass


@dataclass(frozen=True)
class TurnOutcome:
    """Result of simulating exactly one turn for a specific racer."""

    vp_delta: list[int]  # per racer: final_vp - start_vp
    position: list[int]  # per racer final positions
    tripped: list[bool]  # per racer tripped flags at end of turn
    eliminated: list[bool]  # per racer eliminated flags at end of turn
    start_position: list[int]  # per racer start positions
