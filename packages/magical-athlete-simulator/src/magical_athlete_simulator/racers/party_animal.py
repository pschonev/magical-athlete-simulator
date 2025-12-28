from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveDistanceQuery,
    Phase,
    TurnStartEvent,
)
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)
from magical_athlete_simulator.engine.movement import push_simultaneous_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class PartyAnimalPull(Ability):
    name: AbilityName = "PartyPull"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
    )  # Triggers before main move (PRE_MAIN)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        # Only trigger on Party Animal's own turn start
        if not isinstance(event, TurnStartEvent) or owner_idx != event.target_racer_idx:
            return "skip_trigger"

        pa = engine.get_racer(owner_idx)
        if not pa.active:
            return "skip_trigger"

        moves_to_make: list[tuple[int, int]] = []
        for r in engine.state.racers:
            if r.idx == owner_idx or (not r.active) or (r.position == pa.position):
                continue

            direction = 1 if r.position < pa.position else -1
            moves_to_make.append((r.idx, direction))

        if moves_to_make:
            push_simultaneous_move(
                engine,
                moves=moves_to_make,
                phase=event.phase,
                source=self.name,
                responsible_racer_idx=owner_idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"


@dataclass(eq=False)
class ModifierPartySelfBoost(RacerModifier, RollModificationMixin):
    """Applied TO Party Animal. Boosts their own roll based on neighbors."""

    name: AbilityName | ModifierName = "PartySelfBoost"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
    ) -> None:
        # This modifier is attached to Party Animal, affects their own roll
        # owner_idx is Party Animal, query.racer_idx is also Party Animal
        if query.racer_idx != owner_idx:
            return  # Safety check (should never happen)

        if owner_idx is None:
            _ = assert_never
            raise ValueError("owner_idx should never be None")

        owner = engine.get_racer(owner_idx)
        guests = [
            r
            for r in engine.state.racers
            if r.idx != owner_idx and not r.finished and r.position == owner.position
        ]
        if guests:
            bonus = len(guests)
            query.modifiers.append(bonus)
            query.modifier_sources.append((self.name, bonus))
            engine.push_event(
                AbilityTriggeredEvent(owner_idx, self.name, Phase.ROLL_WINDOW),
            )


@dataclass
class AbilityPartyBoost(Ability, LifecycleManagedMixin):
    name: AbilityName = "PartyBoost"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    @staticmethod
    def on_gain(engine: GameEngine, owner_idx: int):
        # Apply the "Check for Neighbors" modifier to MYSELF
        add_racer_modifier(
            engine,
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int):
        remove_racer_modifier(
            engine,
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )
