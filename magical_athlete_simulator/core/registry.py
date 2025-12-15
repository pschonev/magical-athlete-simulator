# Build these automatically at module load
from magical_athlete_simulator.core.ability_base import Ability
from magical_athlete_simulator.core.modifier_base import Modifier
from magical_athlete_simulator.core.types import AbilityName, RacerName

ABILITY_CLASSES: dict[AbilityName, type[Ability]] = {
    cls.name: cls for cls in Ability.__subclasses__()
}
MODIFIER_CLASSES: dict[AbilityName | str, type[Modifier]] = {
    cls.name: cls for cls in Modifier.__subclasses__()
}

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "Centaur": {"Trample"},
    "HugeBaby": {"HugeBabyPush"},
    "Scoocher": {"ScoochStep"},
    "Banana": {"BananaTrip"},
    "Copycat": {"CopyLead"},
    "Gunk": {"Slime"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
    "Magician": {"MagicalReroll"},
}
