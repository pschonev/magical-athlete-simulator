from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, RacerName

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "BabaYaga": {"BabaYagaTrip"},
    "Banana": {"BananaTrip"},
    "Centaur": {"CentaurTrample"},
    "Copycat": {"CopyLead"},
    "FlipFlop": {"FlipFlopSwap"},
    "Gunk": {"GunkSlime"},
    "HugeBaby": {"HugeBabyPush"},
    "Magician": {"MagicalReroll"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
    "Romantic": {"RomanticMove"},
    "Scoocher": {"ScoochStep"},
}
