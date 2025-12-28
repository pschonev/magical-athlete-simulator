from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import (
    MoveDistanceQuery,
    PerformMainRollEvent,
    Phase,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
)
from magical_athlete_simulator.core.mixins import RollModificationMixin
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import Source
    from magical_athlete_simulator.engine.game_engine import GameEngine


def handle_perform_main_roll(engine: GameEngine, event: PerformMainRollEvent) -> None:
    racer = engine.get_racer(event.target_racer_idx)
    if racer.main_move_consumed:
        engine.log_info(f"Skipping roll because {racer.repr} already used main move.")
        return

    engine.state.roll_state.serial_id += 1
    current_serial = engine.state.roll_state.serial_id

    base = engine.rng.randint(1, 6)
    query = MoveDistanceQuery(event.target_racer_idx, base)

    # Apply ALL modifiers attached to this racer
    for mod in engine.get_racer(event.target_racer_idx).modifiers:
        if isinstance(mod, RollModificationMixin):
            mod.modify_roll(query, mod.owner_idx, engine)

    final = query.final_value
    engine.state.roll_state.base_value = base
    engine.state.roll_state.final_value = final

    # Logging with sources
    if query.modifier_sources:
        parts = [f"{name}:{delta:+d}" for (name, delta) in query.modifier_sources]
        mods_str = ", ".join(parts)
        total_delta = sum(delta for _, delta in query.modifier_sources)
        engine.log_info(
            f"Dice Roll: {base} (Mods: {total_delta} [{mods_str}]) -> Result: {final}",
        )
    else:
        engine.log_info(f"Dice Roll: {base} (Mods: 0) -> Result: {final}")

    # 3. Fire the 'Window' event. Listeners can call trigger_reroll() here.
    engine.push_event(
        RollModificationWindowEvent(
            target_racer_idx=event.target_racer_idx,
            current_roll_val=final,
            roll_serial=current_serial,
            responsible_racer_idx=event.target_racer_idx,
            source=event.source,
        ),
    )

    # 4. Schedule the resolution. If trigger_reroll() was called in step 3,
    # serial_id will increment, and this event will be ignored in _resolve_main_move.
    engine.push_event(
        ResolveMainMoveEvent(
            target_racer_idx=event.target_racer_idx,
            roll_serial=current_serial,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
        ),
    )


def resolve_main_move(engine: GameEngine, event: ResolveMainMoveEvent):
    # If serial doesn't match, it means a re-roll happened.
    if event.roll_serial != engine.state.roll_state.serial_id:
        engine.log_debug("Ignoring stale roll resolution (Re-roll occurred).")
        return

    dist = engine.state.roll_state.final_value
    if dist > 0:
        push_move(
            engine=engine,
            moved_racer_idx=event.target_racer_idx,
            distance=dist,
            phase=Phase.MOVE_EXEC,
            source=event.source,
            responsible_racer_idx=event.responsible_racer_idx,
            emit_ability_triggered="never",
        )


def trigger_reroll(engine: GameEngine, source_idx: int, source: Source):
    """Cancels the current roll resolution and schedules a new roll immediately."""
    engine.log_info(
        f"RE-ROLL TRIGGERED by {engine.get_racer(source_idx).name} ({source})",
    )
    # Increment serial to kill any pending ResolveMainMove events
    engine.state.roll_state.serial_id += 1

    engine.push_event(
        PerformMainRollEvent(
            target_racer_idx=engine.state.current_racer_idx,
            phase=Phase.ROLL_DICE,
            source=source,
            responsible_racer_idx=engine.state.current_racer_idx,
        ),
    )
