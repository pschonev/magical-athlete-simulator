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
    "Mastermind",
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
    "DicemongerProfit",
    "SuckerfishRide",
    "DuelistChallenge",
    "MastermindPredict",
]

ModifierName = Literal[
    "GunkSlimeModifier",
    "HugeBabyBlocker",
    "MoveDeltaTile",
    "PartySelfBoost",
    "TripTile",
    "VictoryPointTile",
    "MastermindPrediction",
]

BoardName = Literal["standard", "wild_wilds"]

SystemSource = Literal["Board", "System"]
Source = AbilityName | ModifierName | SystemSource
