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
    # New Racers
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
    # New Abilities
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
    # New Modifiers
    "MastermindPrediction",
]

SystemSource = Literal["Board", "System"]
Source = AbilityName | ModifierName | SystemSource
