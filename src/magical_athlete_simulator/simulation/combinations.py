"""Generate racer combinations with perfect coverage and no duplicates."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from magical_athlete_simulator.simulation.hashing import GameConfiguration

if TYPE_CHECKING:
    from collections.abc import Iterator

    from magical_athlete_simulator.core.types import BoardName, RacerName


def compute_total_runs(
    *,
    eligible_racers: list[RacerName],
    racer_counts: Iterable[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
) -> int:
    """
    Computes the total number of simulations that will be run.
    Calculates the exact theoretical universe size and clamps it to the user's limit.
    """
    n = len(eligible_racers)
    if n == 0 or not boards:
        return 0

    # Filter for valid team sizes (e.g., can't have 5-racer team with only 3 eligible racers)
    valid_ks = {k for k in racer_counts if 0 < k <= n}
    if not valid_ks:
        return 0

    seeds = runs_per_combination or 1

    # Calculate Universe Size: Boards * Seeds * Sum(nCk)
    # math.comb calculates exact combinations efficiently without iterating
    combinations_sum = sum(math.comb(n, k) for k in valid_ks)
    theoretical_total = len(boards) * seeds * combinations_sum

    # If the user wants infinite runs (None), we return the theoretical max.
    if max_total_runs is None:
        return theoretical_total

    # Otherwise, the progress bar is simply the smaller of the two numbers.
    return min(theoretical_total, max_total_runs)


# -------------------------------------------------------------------------
#  Mathematical Helper: The "Unranker"
# -------------------------------------------------------------------------


def get_combination_at_index(n: int, k: int, index: int) -> list[int]:
    """
    Decodes a linear index into a specific combination (Unranking).

    This implements the 'Combinadic' (Combinatorial Number System).
    It allows us to treat the set of all possible combinations as a linear
    array without ever allocating that array in memory.

    Mathematically:
    Any integer 'index' < (n choose k) has a unique representation as a sum
    of combinatorial coefficients:
      index = (c_k choose k) + ... + (c_1 choose 1)
      where n > c_k > ... > c_1 >= 0

    Args:
        n: Size of the eligible population (e.g., 20 racers)
        k: Size of the team to pick (e.g., 4 racers)
        index: The i-th lexicographical combination (0-based)

    Returns:
        A list of 'k' integers representing the indices of the selected items.
        (e.g., [0, 5, 12] means 1st, 6th, and 13th racer in the list).
    """
    result = []
    a = n
    b = k
    x = (math.comb(n, k) - 1) - index  # Dual index mapping for easier math

    for i in range(k):
        a -= 1
        while True:
            c = math.comb(a, b)
            if x >= c:
                x -= c
                result.append(n - 1 - a)
                b -= 1
                break
            a -= 1
    return result


# -------------------------------------------------------------------------
#  Core Logic
# -------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskBucket:
    board: BoardName
    racer_count: int
    pool_size: int
    num_to_draw: int


def generate_combinations(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    seed_offset: int = 0,
) -> Iterator[GameConfiguration]:
    """
    Smart generator that guarantees unique combinations even in massive spaces
    by sampling indices instead of racers.
    """
    n_racers = len(eligible_racers)
    n_seeds = runs_per_combination or 1

    # 1. Identify all "Buckets" (Map + Player Count pairs)
    #    and calculate the theoretical size of each.
    valid_counts = [k for k in sorted(set(racer_counts)) if 0 < k <= n_racers]
    buckets: list[TaskBucket] = []

    for board in boards:
        for k in valid_counts:
            # How many unique racer teams exist? (n choose k)
            unique_teams = math.comb(n_racers, k)
            # Total unique games = teams * seeds
            total_possibilities = unique_teams * n_seeds

            # Initially, we don't know how many to draw. Set 0.
            buckets.append(TaskBucket(board, k, total_possibilities, 0))

    if not buckets:
        return

    # 2. Allocate our 'max_total_runs' budget across buckets.
    #    We want to test every Map/Count combo equally if possible.
    if max_total_runs is None:
        # Infinite/Max mode: Take EVERYTHING from every bucket
        final_buckets = [b.replace(num_to_draw=b.pool_size) for b in buckets]
    else:
        # Distribute budget evenly
        final_buckets = _distribute_budget(buckets, max_total_runs)

    # 3. Execution: Draw samples from each bucket
    #    We yield strictly unique configurations.

    # Global yielded counter for the seed generation
    global_yield_counter = 0

    # Shuffle buckets so we don't process all "Map 1" games before "Map 2"
    # (Optional: depends if you want streaming diversity)
    execution_order = list(final_buckets)
    random.shuffle(execution_order)

    for bucket in execution_order:
        if bucket.num_to_draw == 0:
            continue

        # KEY OPTIMIZATION:
        # Instead of generating racers, we generate integer Indices.
        # random.sample on a range is O(k) memory, not O(N).
        # It handles the "No Duplicates" logic for us instantly.
        indices = random.sample(range(bucket.pool_size), bucket.num_to_draw)

        for idx in indices:
            # Decode the linear index back into (Team Index, Seed Index)
            # Total Size = Teams * Seeds
            # So:
            # team_idx = idx // n_seeds
            # seed_offset_local = idx % n_seeds

            # Calculate breakdown
            team_comb_idx = idx // n_seeds
            local_seed_idx = idx % n_seeds

            # A. Unrank the racers
            # "get_combination_at_index" gives us indices like [0, 5, 12]
            racer_indices = get_combination_at_index(
                n_racers,
                bucket.racer_count,
                team_comb_idx,
            )
            selected_racers = [eligible_racers[i] for i in racer_indices]

            # B. Handle Seed & Shuffle
            # Use a deterministic seed based on the request (for reproducibility)
            # or purely sequential. Let's stick to your pattern:
            final_seed = seed_offset + global_yield_counter

            # Deterministic shuffle of the racer positions
            rng = random.Random(final_seed)
            rng.shuffle(selected_racers)

            yield GameConfiguration(
                racers=tuple(selected_racers),
                board=bucket.board,
                seed=final_seed,
            )
            global_yield_counter += 1


def _distribute_budget(
    buckets: list[TaskBucket],
    total_budget: int,
) -> list[TaskBucket]:
    """
    Distributes the total run budget evenly across buckets.
    If a bucket is smaller than its share, it gets capped (exhausted),
    and the spare budget is redistributed to larger buckets.
    """
    remaining_budget = total_budget
    pending_buckets = list(buckets)
    final_allocation = {id(b): 0 for b in buckets}  # Map ID -> Count

    while pending_buckets and remaining_budget > 0:
        # How much does each remaining bucket get?
        share = math.ceil(remaining_budget / len(pending_buckets))

        still_pending = []
        for b in pending_buckets:
            # If bucket is smaller than share, take all of it
            if b.pool_size <= share:
                allocation = b.pool_size
                remaining_budget -= allocation
                final_allocation[id(b)] = allocation
            else:
                # If bucket is huge, it can take the share, but we aren't done with it
                # We provisionally assign the share, but we might increase it
                # in the next loop iteration if other buckets maxed out early.
                # Actually simpler: Assign share now, subtract from budget.
                # But wait, we need to be fair.

                # Simpler logic: Just fill small buckets first.
                still_pending.append(b)

        # If no small buckets were removed, we can just distribute evenly and break
        if len(still_pending) == len(pending_buckets):
            for b in still_pending:
                take = min(share, remaining_budget)
                final_allocation[id(b)] += take
                remaining_budget -= take
            break

        pending_buckets = still_pending

    # Reconstruct buckets with new counts
    return [
        TaskBucket(b.board, b.racer_count, b.pool_size, final_allocation[id(b)])
        for b in buckets
    ]
