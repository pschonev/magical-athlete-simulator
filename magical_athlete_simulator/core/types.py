from enum import IntEnum
from typing import Literal

RacerName = Literal[
    "Centaur",
    "HugeBaby",
    "Scoocher",
    "Banana",
    "Copycat",
    "Gunk",
    "PartyAnimal",
    "Magician",
]
AbilityName = Literal[
    "Trample",
    "HugeBabyPush",
    "BananaTrip",
    "ScoochStep",
    "CopyLead",
    "Slime",
    "PartyPull",
    "PartyBoost",
    "MagicalReroll",
]

ModifierName = Literal["PartySelfBoost"]


class Phase(IntEnum):
    SYSTEM = 0
    PRE_MAIN = 10
    ROLL_DICE = 15
    ROLL_WINDOW = 18  # Hook for re-rolls
    MAIN_ACT = 20
    REACTION = 25
    MOVE_EXEC = 30
    BOARD = 40
