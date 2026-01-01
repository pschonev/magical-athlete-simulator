"""Command-line interface for batch simulations."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cappa
from tqdm import tqdm

from simul_runner.combinations import compute_total_runs, generate_combinations
from simul_runner.config import SimulationConfig
from simul_runner.db.manager import SimulationDatabase
from simul_runner.db.models import Race, RacerResult
from simul_runner.runner import run_single_simulation

# Suppress game engine logs at module level
logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

# Performance Tuning: Write to disk every N simulations
BATCH_SIZE = 1000


@dataclass
class Args:
    """CLI arguments for simulation runner."""

    config: Path
    """Path to TOML configuration file"""

    runs_per_combination: int | None = None
    """Override: number of seeds per racer+board combo"""

    max_total_runs: int | None = None
    """Override: absolute cap on total simulations"""

    max_turns: int = 500
    """Override: abort races exceeding this many turns"""

    seed_offset: int = 0
    """Starting seed value (for resuming runs)"""

    def __call__(self) -> int:
        """Execute batch simulations with progress tracking."""

        # Load config
        if not self.config.exists():
            tqdm.write(f"Error: Config file not found: {self.config}", file=sys.stderr)
            return 1

        config = SimulationConfig.from_toml(str(self.config))

        # CLI overrides
        runs_per_combo = self.runs_per_combination or config.runs_per_combination
        max_total = self.max_total_runs or config.max_total_runs
        max_turns = self.max_turns or config.max_turns_per_race

        # Resolve racers
        eligible_racers = config.get_eligible_racers()

        if not eligible_racers:
            tqdm.write(
                "Error: No eligible racers after include/exclude filters",
                file=sys.stderr,
            )
            return 1

        # Print configuration summary before progress bar starts
        tqdm.write(f"Eligible racers: {len(eligible_racers)}")
        tqdm.write(f"Racer counts: {config.racer_counts}")
        tqdm.write(f"Boards: {config.boards}")
        tqdm.write(f"Runs per combination: {runs_per_combo or 'unlimited'}")
        tqdm.write(f"Max total runs: {max_total or 'unlimited'}")
        tqdm.write("")  # Blank line

        # Generate combinations
        combo_gen = generate_combinations(
            eligible_racers=eligible_racers,
            racer_counts=config.racer_counts,
            boards=config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
            seed_offset=self.seed_offset,
        )

        # Initialize DB and Load Existing Hashes
        db = SimulationDatabase(Path("results"))
        seen_hashes = db.get_known_hashes()
        initial_seen_count = len(seen_hashes)

        # Track results
        completed = 0
        skipped = 0
        aborted = 0
        unsaved_changes = 0

        # Calculate expected total for progress bar (if possible)
        total_expected = compute_total_runs(
            eligible_racers=eligible_racers,
            racer_counts=config.racer_counts,
            boards=config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
        )

        try:
            # Progress bar with dynamic total
            with tqdm(
                desc="Simulating",
                unit="race",
                total=total_expected,
                dynamic_ncols=True,
            ) as pbar:
                for game_config in combo_gen:
                    config_hash = game_config.compute_hash()

                    # Idempotency Check
                    if config_hash in seen_hashes:
                        skipped += 1
                        continue

                    seen_hashes.add(config_hash)

                    # Run simulation
                    result = run_single_simulation(game_config, max_turns)

                    if result.aborted:
                        aborted += 1
                    else:
                        completed += 1
                        unsaved_changes += 1

                        # 1. Determine Rank (1st, 2nd, None)
                        # We sort a copy to determine standing, but keep original metrics order
                        # SORT LOGIC: VP Descending > Fewest Turns (highest negative)
                        standings = sorted(
                            result.metrics,
                            key=lambda m: (m.final_vp, -m.turns_taken),
                            reverse=True,
                        )

                        rank_map = {}
                        # Only the top 2 racers with positive VP get a rank
                        if len(standings) > 0 and standings[0].final_vp > 0:
                            rank_map[standings[0].racer_idx] = 1
                        if len(standings) > 1 and standings[1].final_vp > 0:
                            rank_map[standings[1].racer_idx] = 2

                        # 2. Create Race Record
                        race_record = Race(
                            config_hash=result.config_hash,
                            seed=game_config.seed,
                            board=game_config.board,
                            racer_names=",".join(game_config.racers),
                            racer_count=len(game_config.racers),
                            timestamp=result.timestamp,
                            execution_time_ms=result.execution_time_ms,
                            aborted=result.aborted,
                            total_turns=result.turn_count,
                        )

                        # 3. Create Racer Results (Preserving ID/Turn Order)
                        racer_records = [
                            RacerResult(
                                config_hash=result.config_hash,
                                racer_id=m.racer_idx,
                                racer_name=m.racer_name,
                                final_vp=m.final_vp,
                                turns_taken=m.turns_taken,
                                recovery_turns=m.recovery_turns,
                                sum_dice_rolled=m.total_dice_rolled,
                                ability_trigger_count=m.ability_trigger_count,
                                ability_self_target_count=m.ability_self_target,
                                ability_target_count=m.ability_target,
                                eliminated=m.eliminated,
                                rank=rank_map.get(m.racer_idx),
                            )
                            for m in result.metrics
                        ]

                        # 4. Save to Memory
                        db.save_simulation(race_record, racer_records)

                        # 5. Batch Flush to Disk
                        if unsaved_changes >= BATCH_SIZE:
                            tqdm.write(
                                f"💾 Flushing {unsaved_changes} records to disk...",
                            )
                            db.flush_to_parquet()
                            unsaved_changes = 0
                    pbar.update(1)

        finally:
            # Always flush remaining data on exit/crash/Ctrl+C
            if unsaved_changes > 0:
                tqdm.write(
                    f"\n💾 Flushing {unsaved_changes} remaining records to disk..."
                )
                db.flush_to_parquet()

        # Final summary (after progress bar completes)
        tqdm.write(
            f"""
        ✅ Completed: {completed}
        ⏭️  Skipped:   {skipped} (Already in DB)
        ⚠️  Aborted:   {aborted}
        🔑 Unique configs processed: {len(seen_hashes) - initial_seen_count}
        💾 Total DB Size: {len(seen_hashes)} races
        """,
        )

        return 0


def main():
    """Entry point for CLI."""
    cappa.invoke(Args)


if __name__ == "__main__":
    sys.exit(main())
