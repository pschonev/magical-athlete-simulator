"""Configuration schema for batch simulations using msgspec."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import msgspec

from magical_athlete_simulator.core.types import BoardName, RacerName


class CombinationFilter(msgspec.Struct):
    """
    Exclusion rule.
    If a generated game matches specific racers AND specific boards, it is skipped.
    """

    # The game must contain ALL of these racers to match this filter.
    # Empty set = Matches any racer combination.
    racers: set[RacerName] = msgspec.field(default_factory=set)

    # The game must be on ONE of these boards to match this filter.
    # Empty set = Matches any board.
    boards: set[BoardName] = msgspec.field(default_factory=set)


class SimulationConfig(msgspec.Struct):
    """
    TOML-backed configuration for batch race simulations.

    msgspec handles mutable defaults (like lists) safely automatically,
    so we don't need default_factory.
    """

    include_racers: list[RacerName] = msgspec.field(default_factory=list)
    exclude_racers: list[RacerName] = msgspec.field(default_factory=list)

    # Combinations to test
    # Use a lambda to return your specific default lists
    racer_counts: list[int] = msgspec.field(default_factory=lambda: [2, 3, 4, 5])
    boards: list[BoardName] = msgspec.field(default_factory=lambda: ["standard"])

    filters: list[CombinationFilter] = msgspec.field(default_factory=list)

    # Execution limits
    runs_per_combination: int | None = None
    max_total_runs: int | None = None
    max_turns_per_race: int = 500

    @classmethod
    def from_toml(cls, path: str) -> SimulationConfig:
        """Load configuration from a TOML file path."""
        with Path(path).open("rb") as f:
            # Decode bytes directly for max performance
            return msgspec.toml.decode(f.read(), type=cls)

    def get_eligible_racers(self) -> list[RacerName]:
        """Resolve final list of racers based on include/exclude."""
        # Imports inside method to avoid top-level circular dependencies if any

        all_racers: list[RacerName] = list(get_args(RacerName))

        # Start with allow-list or all
        if self.include_racers:
            eligible: list[RacerName] = [
                r for r in self.include_racers if r in all_racers
            ]
        else:
            eligible = all_racers

        # Apply block-list
        if self.exclude_racers:
            eligible = [r for r in eligible if r not in self.exclude_racers]

        return eligible
