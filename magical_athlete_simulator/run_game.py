import random
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.state import GameState, LogContext, RacerState
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.game_engine import GameEngine

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import RacerName

if __name__ == "__main__":
    roster: list[RacerName] = [
        "PartyAnimal",
        "Scoocher",
        "Magician",
        "HugeBaby",
        "Centaur",
        "Banana",
    ]
    racers = [RacerState(i, n) for i, n in enumerate(roster)]
    engine_id = next(ENGINE_ID_COUNTER)
    eng = GameEngine(
        GameState(racers=racers, board=BOARD_DEFINITIONS["standard"]()),
        random.Random(1),
        log_context=LogContext(
            engine_id=engine_id,
            engine_level=0,
            parent_engine_id=None,
        ),
    )

    eng.run_race()
