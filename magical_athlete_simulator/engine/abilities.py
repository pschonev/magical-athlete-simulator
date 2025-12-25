from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.modifiers import RacerModifier
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
