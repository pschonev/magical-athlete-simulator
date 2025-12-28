from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import AbilityTriggeredEvent, Phase
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent, MoveDistanceQuery
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class ModifierSlime(RacerModifier, RollModificationMixin):
    """Applied TO a victim racer. Reduces their roll by 1.
    Owned by Gunk.
    """

    name: AbilityName | ModifierName = "GunkSlimeModifier"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
    ) -> None:
        # This modifier is attached to the VICTIM, and affects their roll
        # owner_idx is Gunk, query.racer_idx is the victim
        query.modifiers.append(-1)
        query.modifier_sources.append((self.name, -1))

        if owner_idx is None:
            raise ValueError("owner_idx should never be None for ModifierSlime")
        engine.push_event(
            AbilityTriggeredEvent(owner_idx, self.name, phase=Phase.ROLL_WINDOW),
        )


@dataclass
class AbilitySlime(Ability, LifecycleManagedMixin):
    name: AbilityName = "GunkSlime"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    @staticmethod
    def on_gain(engine: GameEngine, owner_idx: int) -> None:
        # Apply debuff to ALL other active racers
        for r in engine.state.racers:
            if r.idx != owner_idx and not r.finished:
                add_racer_modifier(engine, r.idx, ModifierSlime(owner_idx=owner_idx))

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int) -> None:
        # Clean up debuff from everyone
        for r in engine.state.racers:
            remove_racer_modifier(engine, r.idx, ModifierSlime(owner_idx=owner_idx))
