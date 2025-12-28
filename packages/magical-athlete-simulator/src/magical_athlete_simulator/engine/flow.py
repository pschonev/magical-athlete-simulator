from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import Phase, RacerFinishedEvent

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.engine.game_engine import GameEngine


def log_final_standings(engine: GameEngine):
    if not engine.verbose:
        return
    engine.log_info("=== FINAL STANDINGS ===")
    for racer in sorted(
        engine.state.racers,
        key=lambda r: r.finish_position if r.finish_position else 999,
    ):
        if racer.finish_position:
            status = f"Rank {racer.finish_position}"
        else:
            status = "Eliminated"
        engine.log_info(
            f"Result: {racer.repr} pos={racer.position} vp={racer.victory_points} {status}",
        )


def check_finish(engine: GameEngine, racer: RacerState) -> bool:
    """
    Checks if a racer has physically crossed the finish line.
    If so, triggers the standard finish flow.
    """
    # If already finished, do nothing (prevent double counting)
    if racer.finished:
        return False

    # Standard rule: Position >= Board Length
    if racer.position >= engine.state.board.length:
        mark_finished(engine, racer)
        return True

    return False


def mark_finished(
    engine: GameEngine,
    racer: RacerState,
    rank: int | None = None,
) -> None:
    """
    Sets a racer as finished at a specific rank.
    WARNING: Does not handle collisions. If rank X is taken, it overwrites.
    Callers doing complex re-ordering must manage displacement manually.
    """
    if rank is None:
        # Default behavior: Append to next available spot
        finished_count = sum(1 for r in engine.state.racers if r.finished)
        rank = finished_count + 1

    # Update State
    old_rank = racer.finish_position
    racer.finish_position = rank

    # Update VP
    rewards = engine.state.rules.winner_vp

    # Undo old VP if re-ranking (e.g., bumping down)
    if old_rank is not None and old_rank > 0 and old_rank <= len(rewards):
        racer.victory_points -= rewards[old_rank - 1]

    # Apply new VP
    if rank <= len(rewards):
        racer.victory_points += rewards[rank - 1]

    engine.log_info(
        f"!!! {racer.repr} FINISHED rank {rank} ({racer.victory_points} VP) !!!",
    )

    # Emit event (important for listeners)
    # Only emit if it's a new finish or a meaningful change
    if old_rank is None:
        engine.push_event(
            RacerFinishedEvent(
                target_racer_idx=racer.idx,
                finishing_position=rank,
                phase=Phase.REACTION,
                responsible_racer_idx=None,
                source="System",
            ),
        )

    # Strip abilities
    engine.update_racer_abilities(racer.idx, set())

    # Auto-check for race end
    check_race_over_condition(engine)


def check_race_over_condition(engine: GameEngine) -> None:
    """Standard check: If 2+ racers finished, end race."""
    count = sum(1 for r in engine.state.racers if r.finished)
    if count >= 2:
        end_race(engine)


def end_race(engine: GameEngine) -> None:
    """Forces the race to end immediately."""
    if engine.state.race_over:
        return

    engine.state.race_over = True
    engine.log_info("Race Ended.")

    # Mark everyone else eliminated
    for r in engine.state.racers:
        if not r.finished:
            r.eliminated = True

    engine.state.queue.clear()
    log_final_standings(engine)
