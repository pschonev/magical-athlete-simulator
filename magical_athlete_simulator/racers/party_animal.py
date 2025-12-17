from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, assert_never, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
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
    emit_ability_trigger,
    remove_racer_modifier,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityPartyPull(Ability):
    name: ClassVar[AbilityName] = "PartyPull"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngine) -> bool:
        if not isinstance(event, TurnStartEvent):
            return False

        if event.racer_idx != owner_idx:
            return False

        party_animal = engine.get_racer(owner_idx)
        any_affected = False

        # CHANGED: We only log and return True if we actually queue a move.
        for r in engine.state.racers:
            if r.idx == owner_idx or r.finished:
                continue

            direction = 0
            if r.position < party_animal.position:
                direction = 1
            elif r.position > party_animal.position:
                direction = -1

            if direction != 0:
                push_move(
                    engine,
                    r.idx,
                    direction,
                    self.name,
                    phase=Phase.PRE_MAIN,
                    owner_idx=owner_idx,
                )
                any_affected = True

        if any_affected:
            engine.log_info(f"{self.name}: Pulling everyone closer!")
            return True

        # If nobody moved (e.g. everyone is on the same tile), ability did not "happen".
        return False


@dataclass(eq=False)
class ModifierPartySelfBoost(RacerModifier, RollModificationMixin):
    """Applied TO Party Animal. Boosts their own roll based on neighbors."""

    name: ClassVar[AbilityName | ModifierName] = "PartySelfBoost"

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
            emit_ability_trigger(
                engine,
                owner_idx,
                self.name,
                f"Boosted by {bonus} guests",
            )


class AbilityPartyBoost(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "PartyBoost"
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
