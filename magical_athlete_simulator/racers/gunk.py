import logging
from dataclasses import dataclass
from typing import ClassVar, override

from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.events import GameEvent, MoveDistanceQuery
from magical_athlete_simulator.core.protocols import (
    Ability,
    GameEngineLike,
    LifecycleManagedMixin,
    RacerModifier,
    RollModificationMixin,
)
from magical_athlete_simulator.core.types import AbilityName

logger = logging.getLogger(LOGGER_NAME)


@dataclass(eq=False)
class ModifierSlime(RacerModifier, RollModificationMixin):
    """Applied TO a victim racer. Reduces their roll by 1.
    Owned by Gunk.
    """

    name: ClassVar[AbilityName | str] = "Slime"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngineLike,
    ) -> None:
        # This modifier is attached to the VICTIM, and affects their roll
        # owner_idx is Gunk, query.racer_idx is the victim
        query.modifiers.append(-1)
        query.modifier_sources.append((self.name, -1))
        engine.emit_ability_trigger(
            owner_idx,
            self.name,
            f"Sliming {engine.get_racer(query.racer_idx).name}",
        )


class AbilitySlime(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "Slime"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    @staticmethod
    def on_gain(engine: GameEngineLike, owner_idx: int) -> None:
        # Apply debuff to ALL other active racers
        for r in engine.state.racers:
            if r.idx != owner_idx and not r.finished:
                engine.add_racer_modifier(r.idx, ModifierSlime(owner_idx=owner_idx))

    @override
    @staticmethod
    def on_loss(engine: GameEngineLike, owner_idx: int) -> None:
        # Clean up debuff from everyone
        for r in engine.state.racers:
            engine.remove_racer_modifier(r.idx, ModifierSlime(owner_idx=owner_idx))
