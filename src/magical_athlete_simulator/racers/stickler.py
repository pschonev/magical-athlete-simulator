from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
    MovementValidatorMixin,
)
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class SticklerConstraint(RacerModifier, MovementValidatorMixin):
    """
    Prevents the racer from moving if the destination exceeds the board length.
    Applied by Stickler to all OTHER racers.
    """

    name: AbilityName | ModifierName = "SticklerStrictFinish"
    priority: int = 0  # High priority validation

    @override
    def validate_move(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        end_tile: int,
    ) -> bool:
        board_len = engine.state.board.length
        if end_tile > board_len:
            engine.log_info(
                f"Stickler Constraint: {engine.get_racer(racer_idx).repr} cannot finish unless landing exactly on {board_len}. Destination {end_tile} is invalid.",
            )
            return False
        return True


@dataclass
class SticklerStrictFinish(Ability, LifecycleManagedMixin):
    name: AbilityName = "SticklerStrictFinishManager"
    triggers: tuple[type[GameEvent], ...] = ()  # No active event triggers

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        return "skip_trigger"

    @staticmethod
    @override
    def on_gain(engine: GameEngine, owner_idx: int) -> None:
        """Apply the constraint modifier to all other racers."""
        constraint = SticklerConstraint(owner_idx=owner_idx)
        for racer in engine.state.racers:
            if racer.idx != owner_idx:
                add_racer_modifier(engine, racer.idx, constraint)

    @staticmethod
    @override
    def on_loss(engine: GameEngine, owner_idx: int) -> None:
        """Remove the constraint modifier from all other racers."""
        constraint = SticklerConstraint(owner_idx=owner_idx)
        for racer in engine.state.racers:
            if racer.idx != owner_idx:
                remove_racer_modifier(engine, racer.idx, constraint)
