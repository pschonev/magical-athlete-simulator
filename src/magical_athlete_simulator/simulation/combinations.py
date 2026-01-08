"""Generate racer combinations with perfect coverage."""

from __future__ import annotations

import itertools
import math
import random
from typing import TYPE_CHECKING

from magical_athlete_simulator.simulation.hashing import GameConfiguration

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from magical_athlete_simulator.core.types import BoardName, RacerName

# Threshold: If total combinations > 10 Million, we switch to random sampling
EXHAUSTIVE_LIMIT = 10_000_000


def compute_total_runs(
    *,
    eligible_racers: list[RacerName],
    racer_counts: Iterable[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    exhaustive_limit: int = EXHAUSTIVE_LIMIT,
) -> int | None:
    if runs_per_combination is None and max_total_runs is None:
        return None

    n = len(eligible_racers)
    if n == 0 or not boards:
        return 0

    seeds = runs_per_combination or 1
    ks = sorted({k for k in racer_counts if 0 < k <= n})
    if not ks:
        return 0

    combo_space = sum(math.comb(n, k) for k in ks)
    space_total = len(boards) * seeds * combo_space

    if space_total > exhaustive_limit:
        return max_total_runs

    if max_total_runs is None:
        return space_total

    return min(space_total, max_total_runs)


def generate_combinations(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    seed_offset: int = 0,
) -> Iterator[GameConfiguration]:
    n_seeds = runs_per_combination or 1

    total_expected = compute_total_runs(
        eligible_racers=list(eligible_racers),
        racer_counts=racer_counts,
        boards=list(boards),
        runs_per_combination=runs_per_combination,
        max_total_runs=max_total_runs,
        exhaustive_limit=EXHAUSTIVE_LIMIT,
    )

    if total_expected is None:
        yield from _generate_random_infinite(
            eligible_racers,
            racer_counts,
            boards,
            seed_offset,
            max_total_runs,
        )
        return

    n = len(eligible_racers)
    ks = [k for k in sorted(set(racer_counts)) if 0 < k <= n]
    space_total = len(boards) * n_seeds * sum(math.comb(n, k) for k in ks)

    if space_total > EXHAUSTIVE_LIMIT:
        yield from _generate_random_infinite(
            eligible_racers,
            racer_counts,
            boards,
            seed_offset,
            max_total_runs,
        )
        return

    # Exhaustive mode
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]] = {}
    for count in racer_counts:
        bucket_combinations[count] = list(
            itertools.combinations(eligible_racers, count),
        )

    yield from _generate_exhaustive(
        bucket_combinations,
        boards,
        n_seeds,
        seed_offset,
        max_total_runs,
    )


def _generate_exhaustive(
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]],
    boards: list[BoardName],
    n_seeds: int,
    seed_offset: int,
    max_total_runs: int | None,
) -> Iterator[GameConfiguration]:
    """
    Flatten the entire universe into a list of tasks, shuffle them, and yield.
    Each 'Task' is a tuple: (Board, RacerTuple, SeedIndex).
    """
    tasks: list[tuple[BoardName, tuple[RacerName, ...], int]] = []

    # Flatten the universe
    for board in boards:
        for combos in bucket_combinations.values():
            for racer_tuple in combos:
                for seed_idx in range(n_seeds):
                    tasks.append((board, racer_tuple, seed_idx))  # noqa: PERF401

    # Global shuffle of execution order
    random.shuffle(tasks)

    for yielded, (board, racer_tuple, seed_idx) in enumerate(tasks):
        if max_total_runs is not None and yielded >= max_total_runs:
            return

        final_seed = seed_offset + seed_idx

        # --- KEY CHANGE ---
        # We use the final_seed to deterministically shuffle the racer order.
        # This ensures that "Banana" isn't always Player 1.
        # We transform tuple -> list -> shuffle -> tuple
        racer_list = list(racer_tuple)

        # Create a local RNG so we don't affect global state and ensure reproducibility
        local_rng = random.Random(final_seed)
        local_rng.shuffle(racer_list)

        yield GameConfiguration(
            racers=tuple(racer_list),  # No longer sorted()
            board=board,
            seed=final_seed,
        )


def _generate_random_infinite(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    seed_offset: int,
    max_total_runs: int | None,
) -> Iterator[GameConfiguration]:
    """Infinite random sampler for massive spaces."""
    yielded = 0
    while True:
        if max_total_runs is not None and yielded >= max_total_runs:
            return

        # 1. Pick structure
        board = random.choice(boards)
        count = random.choice(racer_counts)

        # 2. Sample racers
        # --- KEY CHANGE ---
        # random.sample returns a random order. We simply REMOVED sorted().
        racers = tuple(random.sample(eligible_racers, count))

        # 3. Generate seed
        seed = seed_offset + yielded

        yield GameConfiguration(
            racers=racers,
            board=board,
            seed=seed,
        )
        yielded += 1
