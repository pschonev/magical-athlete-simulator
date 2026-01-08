"""Testing utilities for creating reproducible game scenarios."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.state import (
    GameRules,
    GameState,
    LogContext,
    RacerState,
)
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS, Board
from magical_athlete_simulator.engine.game_engine import GameEngine

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, RacerName


@dataclass
class RacerConfig:
    """Configuration for a single racer in a scenario."""

    idx: int
    name: RacerName
    abilities: set[AbilityName] | None = None
    start_pos: int = 0

    def __post_init__(self):
        if self.abilities is None:
            if self.name not in RACER_ABILITIES:
                msg = f"Racer '{self.name}' not found in RACER_ABILITIES."
                raise ValueError(msg)

            defaults = RACER_ABILITIES[self.name]

            if not defaults:
                msg = f"Racer '{self.name}' has no default abilities defined."
                raise ValueError(msg)

            self.abilities = defaults.copy()


@dataclass
class GameScenario:
    """
    A reusable harness for creating controlled game scenarios.

    Useful for both testing and visual debugging in the frontend.
    Allows scripting dice rolls and custom starting positions.
    """

    racers_config: list[RacerConfig]
    dice_rolls: list[int] | None = None
    board: Board | None = None
    rules: GameRules | None = None
    seed: int | None = None

    # These are set in __post_init__
    state: GameState = field(init=False)
    engine: GameEngine = field(init=False)
    mock_rng: MagicMock | None = field(init=False, default=None)

    def __post_init__(self):
        racers: list[RacerState] = []

        # Setup racers from config
        for cfg in self.racers_config:
            r = RacerState(cfg.idx, cfg.name, position=cfg.start_pos)
            racers.append(r)

        # Choose RNG strategy
        if self.dice_rolls is not None:
            self.mock_rng = MagicMock()
            self.mock_rng.randint.side_effect = itertools.cycle(self.dice_rolls)
            rng = self.mock_rng
        elif self.seed is not None:
            # Use seeded random for reproducible but natural randomness
            rng = random.Random(self.seed)
            self.mock_rng = None
        else:
            # Use truly random RNG
            rng = random.Random()
            self.mock_rng = None

        # Initialize engine
        board = (
            self.board if self.board is not None else BOARD_DEFINITIONS["standard"]()
        )
        rules = self.rules if self.rules is not None else GameRules()

        self.state = GameState(racers, board=board, rules=rules)

        engine_id = next(ENGINE_ID_COUNTER)
        self.engine = GameEngine(
            self.state,
            rng,
            log_context=LogContext(
                engine_id=engine_id,
                engine_level=0,
                parent_engine_id=None,
            ),
        )

    def set_dice_rolls(self, rolls: list[int]):
        if self.mock_rng is None:
            msg = "Cannot set dice rolls when using a real Random instance. Create scenario with dice_rolls parameter instead."
            raise ValueError(msg)
        self.mock_rng.randint.side_effect = itertools.cycle(rolls)

    def run_turn(self):
        """Run one turn and advance to the next racer."""
        self.engine.run_turn()
        self.engine._advance_turn()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    def run_turns(self, n: int):
        """Run n consecutive turns."""
        for _ in range(n):
            if self.engine.state.race_over:
                break
            self.run_turn()

    def get_racer(self, idx: int) -> RacerState:
        """Get racer state by index."""
        return self.engine.get_racer(idx)
