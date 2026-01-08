from __future__ import annotations  # noqa: INP001

import random
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.state import (
    GameRules,
    GameState,
    LogContext,
    RacerState,
)
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.game_engine import GameEngine

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import RacerName

if __name__ == "__main__":
    roster: list[RacerName] = [
        "Romantic",
        "Banana",
        "Centaur",
        "Magician",
        "Scoocher",
    ]
    racers = [RacerState(i, n) for i, n in enumerate(roster)]
    engine_id = next(ENGINE_ID_COUNTER)
    eng = GameEngine(
        GameState(
            racers=racers,
            board=BOARD_DEFINITIONS["wild_wilds"](),
            rules=GameRules(timing_mode="DFS"),
        ),
        random.Random(9),
        log_context=LogContext(
            engine_id=engine_id,
            engine_level=0,
            parent_engine_id=None,
        ),
    )

    eng.run_race()
