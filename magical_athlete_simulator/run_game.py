import random

from magical_athlete_simulator.core.protocols import GameState, RacerState
from magical_athlete_simulator.core.types import RacerName
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.game_engine import GameEngine

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
    eng = GameEngine(
        GameState(racers, board=BOARD_DEFINITIONS["standard"]()),
        random.Random(1),
    )

    eng.run_race()
