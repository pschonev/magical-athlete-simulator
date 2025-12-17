from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import AbilityTriggeredEvent, Phase

if TYPE_CHECKING:
    from magical_athlete_simulator.core.modifiers import RacerModifier
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


def add_racer_modifier(engine: GameEngine, target_idx: int, modifier: RacerModifier):
    racer = engine.get_racer(target_idx)
    if modifier not in racer.modifiers:
        racer.modifiers.append(modifier)
        engine.log_info(f"ENGINE: Added {modifier.name} to {racer.repr}")


def remove_racer_modifier(engine: GameEngine, target_idx: int, modifier: RacerModifier):
    racer = engine.get_racer(target_idx)
    if modifier in racer.modifiers:
        racer.modifiers.remove(modifier)
        engine.log_info(f"ENGINE: Removed {modifier.name} from {racer.repr}")


def emit_ability_trigger(
    engine: GameEngine,
    source_idx: int | None,
    ability: AbilityName | ModifierName | str,
    log_context: str,
):
    engine.push_event(
        AbilityTriggeredEvent(source_idx, ability, log_context),
        phase=Phase.REACTION,
        owner_idx=source_idx,
    )
