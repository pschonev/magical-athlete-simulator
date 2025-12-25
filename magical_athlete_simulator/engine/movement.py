from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    EventTriggerMode,
    MoveCmdEvent,
    PassingEvent,
    Phase,
    PostMoveEvent,
    PostWarpEvent,
    PreMoveEvent,
    PreWarpEvent,
    TripCmdEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.engine.flow import check_finish

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import Source
    from magical_athlete_simulator.engine.game_engine import GameEngine


def handle_move_cmd(engine: GameEngine, evt: MoveCmdEvent):
    racer = engine.get_racer(evt.target_racer_idx)
    if not racer.active:
        return

    # Moving 0 is not moving at all
    if evt.distance == 0:
        return

    start = racer.position
    distance = evt.distance

    # 1. Departure hook
    engine.publish_to_subscribers(
        PreMoveEvent(
            target_racer_idx=evt.target_racer_idx,
            start_tile=start,
            distance=distance,
            source=evt.source,
            phase=evt.phase,
            responsible_racer_idx=evt.responsible_racer_idx,
        ),
    )

    # 2. Resolve spatial modifiers (Huge Baby etc.)
    intended = start + distance
    end = engine.state.board.resolve_position(
        intended,
        evt.target_racer_idx,
        engine,
        event=evt,
    )  # [file:1]

    if end < 0:
        engine.log_info(
            f"Attempted to move {racer.repr} to {end}. Instead moving to starting tile (0).",
        )
        end = 0

    # If you get fully blocked back to your start, treat as “no movement”
    if standing_still := (end == start):
        return

    if evt.emit_ability_triggered == "after_resolution":
        ability_triggered = (
            not standing_still
        ) or engine.state.rules.count_0_moves_for_ability_triggered

        if ability_triggered:
            engine.push_event(
                event=AbilityTriggeredEvent.from_event(evt),
            )

    engine.log_info(f"Move: {racer.repr} {start}->{end} ({evt.source})")  # [file:1]

    # 3. Passing events
    if distance != 0:
        # Determine step direction: 1 for forward, -1 for backward
        step = 1 if distance > 0 else -1

        current = start + step
        while current != end:
            # Check bounds just in case
            if 0 <= current < engine.state.board.length:
                victims = [
                    r
                    for r in engine.state.racers
                    if r.position == current and r.idx != racer.idx and not r.finished
                ]
                for v in victims:
                    engine.push_event(
                        PassingEvent(
                            responsible_racer_idx=racer.idx,
                            target_racer_idx=v.idx,
                            phase=evt.phase,
                            source=evt.source,
                            tile_idx=current,
                        ),
                    )
            current += step
            # Safety break if we overshoot (shouldn't happen with step logic but good practice)
            if (step > 0 and current > end) or (step < 0 and current < end):
                break

    # 4. Commit position
    racer.position = end

    # Finish check as in your current engine
    if check_finish(engine, racer):  # may log finish + mark race_over, etc. [file:1]
        return

    # 5. Board “on land” hooks (Trip, VP, MoveDelta, etc.)
    engine.state.board.trigger_on_land(end, racer.idx, evt.phase, engine)  # [file:1]

    # 6. Arrival hook
    engine.publish_to_subscribers(
        PostMoveEvent(
            target_racer_idx=evt.target_racer_idx,
            start_tile=start,
            end_tile=end,
            source=evt.source,
            phase=evt.phase,
            responsible_racer_idx=evt.responsible_racer_idx,
        ),
    )


def handle_warp_cmd(engine: GameEngine, evt: WarpCmdEvent):
    racer = engine.get_racer(evt.target_racer_idx)
    if not racer.active:
        return

    start = racer.position

    # Warping to the same tile is not movement
    if start == evt.target_tile:
        return

    # 1. Departure hook
    engine.publish_to_subscribers(
        PreWarpEvent(
            target_racer_idx=evt.target_racer_idx,
            start_tile=start,
            target_tile=evt.target_tile,
            source=evt.source,
            phase=evt.phase,
            responsible_racer_idx=evt.responsible_racer_idx,
        ),
    )

    # 2. Resolve spatial modifiers on the target
    resolved = engine.state.board.resolve_position(
        evt.target_tile,
        evt.target_racer_idx,
        engine,
        event=evt,
    )  # [file:1]

    if resolved < 0:
        engine.log_info(
            f"Attempted to warp to {resolved}. Instead moving to starting tile (0).",
        )
        resolved = 0

    if resolved == start:
        return

    if evt.emit_ability_triggered == "after_resolution":
        engine.push_event(
            event=AbilityTriggeredEvent.from_event(evt),
        )

    engine.log_info(f"Warp: {racer.repr} -> {resolved} ({evt.source})")  # [file:1]
    racer.position = resolved

    if check_finish(engine, racer):
        return

    # 3. Board hooks on landing
    engine.state.board.trigger_on_land(
        resolved,
        racer.idx,
        evt.phase,
        engine,
    )  # [file:1]

    # 4. Arrival hook
    engine.publish_to_subscribers(
        PostWarpEvent(
            target_racer_idx=evt.target_racer_idx,
            start_tile=start,
            end_tile=resolved,
            source=evt.source,
            phase=evt.phase,
            responsible_racer_idx=evt.responsible_racer_idx,
        ),
    )


def handle_trip_cmd(engine: GameEngine, evt: TripCmdEvent):
    racer = engine.get_racer(evt.target_racer_idx)

    # If already tripped or finished, do nothing AND emit nothing.
    if not racer.active or racer.tripped:
        return

    # Apply effect
    racer.tripped = True
    engine.log_info(f"{evt.source}: {racer.repr} is now Tripped.")

    if evt.emit_ability_triggered != "never":
        engine.push_event(
            event=AbilityTriggeredEvent.from_event(evt),
        )


def push_move(
    engine: GameEngine,
    distance: int,
    phase: Phase,
    *,
    moved_racer_idx: int,
    source: Source,
    responsible_racer_idx: int | None,
    emit_ability_triggered: EventTriggerMode = "never",
):
    engine.push_event(
        MoveCmdEvent(
            target_racer_idx=moved_racer_idx,
            distance=distance,
            source=source,
            phase=phase,
            emit_ability_triggered=emit_ability_triggered,
            responsible_racer_idx=responsible_racer_idx,
        ),
    )


def push_warp(
    engine: GameEngine,
    target: int,
    phase: Phase,
    *,
    warped_racer_idx: int,
    source: Source,
    responsible_racer_idx: int | None,
    emit_ability_triggered: EventTriggerMode = "never",
):
    engine.push_event(
        WarpCmdEvent(
            target_racer_idx=warped_racer_idx,
            target_tile=target,
            source=source,
            phase=phase,
            emit_ability_triggered=emit_ability_triggered,
            responsible_racer_idx=responsible_racer_idx,
        ),
    )


def push_trip(
    engine: GameEngine,
    phase: Phase,
    *,
    tripped_racer_idx: int,
    source: Source,
    responsible_racer_idx: int | None,
    emit_ability_triggered: EventTriggerMode = "after_resolution",
):
    engine.push_event(
        TripCmdEvent(
            target_racer_idx=tripped_racer_idx,
            source=source,
            phase=phase,
            emit_ability_triggered=emit_ability_triggered,
            responsible_racer_idx=responsible_racer_idx,
        ),
    )
