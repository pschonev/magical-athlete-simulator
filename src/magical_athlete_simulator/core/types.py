from __future__ import annotations

from typing import Literal

RacerName = Literal[
    "BabaYaga",
    "Banana",
    "Centaur",
    "Copycat",
    "FlipFlop",
    "Gunk",
    "HugeBaby",
    "Romantic",
    "Scoocher",
    "PartyAnimal",
    "Magician",
    "Skipper",
    "Genius",
    "Legs",
    "Hare",
    "Lackey",
    "Dicemonger",
    "Suckerfish",
    "Duelist",
    "Leaptoad",
    "Mastermind",
    "Stickler",
]

AbilityName = Literal[
    "BabaYagaTrip",
    "BananaTrip",
    "CentaurTrample",
    "CopyLead",
    "FlipFlopSwap",
    "GunkSlime",
    "HugeBabyPush",
    "MagicalReroll",
    "PartyPull",
    "PartyBoost",
    "RomanticMove",
    "ScoochStep",
    "SkipperTurn",
    "GeniusPrediction",
    "LegsMove5",
    "HareSpeed",
    "LackeyInterference",
    "LeaptoadJumpManager",
    "DicemongerProfit",
    "SticklerStrictFinishManager",
    "SuckerfishRide",
    "DuelistChallenge",
    "MastermindPredict",
]

ModifierName = Literal[
    "GunkSlimeModifier",
    "HugeBabyBlocker",
    "LeaptoadJump",
    "MastermindPrediction",
    "MoveDeltaTile",
    "PartySelfBoost",
    "SticklerStrictFinish",
    "TripTile",
    "VictoryPointTile",
]

BoardName = Literal["standard", "wild_wilds"]

SystemSource = Literal["Board", "System"]
Source = AbilityName | ModifierName | SystemSource

ErrorCode = Literal[
    "CRITICAL_LOOP_DETECTED",
    "MINOR_LOOP_DETECTED",
    "MAX_TURNS_REACHED",
]
