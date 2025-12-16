from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import Phase, RacerFinishedEvent

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.engine.game_engine import GameEngine


def check_finish(engine: GameEngine, racer: RacerState) -> bool:
    if racer.finished:
        return False

    if racer.position >= engine.state.board.length:
        # Count how many finished before this one
        finishing_position = sum(1 for r in engine.state.racers if r.finished) + 1
        racer.finish_position = finishing_position
        racer.victory_points += engine.state.rules.winner_vp[finishing_position - 1]

        engine.log_info(f"!!! {racer.repr} FINISHED rank {finishing_position} !!!")

        # Emit finish event
        engine.push_event(
            RacerFinishedEvent(racer.idx, finishing_position),
            phase=Phase.REACTION,
        )

        # Strip abilities
        engine.update_racer_abilities(racer.idx, set())

        # Check if race is over (2 finishers)
        finished_count = sum(1 for r in engine.state.racers if r.finished)
        if finished_count >= 2:
            engine.state.race_over = True
            # Mark remaining as eliminated
            for r in engine.state.racers:
                if not r.finished:
                    r.eliminated = True
            engine.state.queue.clear()
            log_final_standings(engine)

        return True

    return False


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
