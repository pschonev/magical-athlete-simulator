import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.modifiers import RacerModifier

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName


def _import_modules() -> None:
    for _, module_name, _ in pkgutil.iter_modules([Path(__file__).parent]):
        _ = importlib.import_module(f"{__name__}.{module_name}")


def get_ability_classes() -> dict[AbilityName, type[Ability]]:
    # Dynamically import all modules in this package
    _import_modules()
    return {cls.name: cls for cls in Ability.__subclasses__()}


def get_modifier_classes() -> dict[AbilityName | str, type[RacerModifier]]:
    return {cls.name: cls for cls in RacerModifier.__subclasses__()}
