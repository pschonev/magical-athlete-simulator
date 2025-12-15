import random

from magical_athlete_simulator.core.types import RacerName
from magical_athlete_simulator.engine.game_engine import GameEngine
from magical_athlete_simulator.engine.state import GameState, RacerState

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
    eng = GameEngine(GameState(racers), random.Random(1))

    eng.run_race()
