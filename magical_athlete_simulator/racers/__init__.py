import importlib
import pkgutil
from pathlib import Path

from magical_athlete_simulator.core.protocols import Ability, RacerModifier
from magical_athlete_simulator.core.types import AbilityName

# Dynamically import all modules in this package
for _, module_name, _ in pkgutil.iter_modules([Path(__file__).parent]):
    _ = importlib.import_module(f"{__name__}.{module_name}")

ABILITY_CLASSES: dict[AbilityName, type[Ability]] = {
    cls.name: cls for cls in Ability.__subclasses__()
}
MODIFIER_CLASSES: dict[AbilityName | str, type[RacerModifier]] = {
    cls.name: cls for cls in RacerModifier.__subclasses__()
}
