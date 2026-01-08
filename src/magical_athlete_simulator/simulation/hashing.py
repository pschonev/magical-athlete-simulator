"""Hash game configurations for deduplication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import BoardName, RacerName


@dataclass(frozen=True, slots=True)
class GameConfiguration:
    """Immutable representation of a single game setup."""

    racers: tuple[RacerName, ...]  # Ordered tuple of racer names
    board: BoardName
    seed: int

    def compute_hash(self) -> str:
        """Compute stable SHA-256 hash of this configuration."""
        # Canonical JSON representation (sorted keys, no whitespace)
        canonical = json.dumps(
            {
                "racers": list(self.racers),
                "board": self.board,
                "seed": self.seed,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
