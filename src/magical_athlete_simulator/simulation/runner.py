"""Core simulation execution logic."""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.simulation.telemetry import MetricsAggregator

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.engine.game_engine import GameEngine
    from magical_athlete_simulator.simulation.db.models import RacerResult
    from magical_athlete_simulator.simulation.hashing import GameConfiguration


@dataclass(slots=True)
class SimulationResult:
    """Result of a single race simulation."""

    config_hash: str
    timestamp: float
    execution_time_ms: float
    aborted: bool
    turn_count: int
    metrics: list[RacerResult]


def run_single_simulation(
    config: GameConfiguration,
    max_turns: int,
) -> SimulationResult:
    """
    Execute one race and return aggregated metrics.
    """
    start_time = time.perf_counter()
    timestamp = time.time()

    config_hash = config.compute_hash()

    # Build scenario from config
    racers_config = [
        RacerConfig(idx=i, name=name) for i, name in enumerate(config.racers)
    ]

    board = BOARD_DEFINITIONS[config.board]()

    scenario = GameScenario(
        racers_config=racers_config,
        seed=config.seed,
        board=board,
    )

    engine = scenario.engine

    # Pass config_hash to aggregator so it can init the Result objects correctly
    aggregator = MetricsAggregator(config_hash=config_hash)
    aggregator.initialize_racers(engine)

    turn_counter = 0

    def on_event(_: GameEngine, event: GameEvent):
        aggregator.on_event(event=event)

    engine.on_event_processed = on_event

    aborted = False

    while not engine.state.race_over:
        active_racer_idx = engine.state.current_racer_idx

        scenario.run_turn()

        aggregator.on_turn_end(
            engine,
            turn_index=turn_counter,
            active_racer_idx=active_racer_idx,
        )
        turn_counter += 1

        if turn_counter >= max_turns:
            aborted = True
            break

    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    metrics = [] if aborted else aggregator.finalize_metrics(engine)

    return SimulationResult(
        config_hash=config_hash,
        timestamp=timestamp,
        execution_time_ms=execution_time_ms,
        aborted=aborted,
        turn_count=turn_counter,
        metrics=metrics,
    )
