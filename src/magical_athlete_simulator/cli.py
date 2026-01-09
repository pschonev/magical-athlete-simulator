"""Command-line interface for batch simulations."""

import logging
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import cappa
from tqdm import tqdm

from magical_athlete_simulator.simulation.combinations import (
    compute_total_runs,
    generate_combinations,
)
from magical_athlete_simulator.simulation.config import SimulationConfig
from magical_athlete_simulator.simulation.db.manager import SimulationDatabase
from magical_athlete_simulator.simulation.db.models import Race
from magical_athlete_simulator.simulation.runner import run_single_simulation

logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

BATCH_SIZE = 1000
RESULTS_DIR = Path("results")


def delete_existing_results(
    dir_path: Path,
    patterns: Iterable[str] = ("*.parquet", "*.duckdb"),
) -> None:
    """Delete files matching patterns in dir_path (non-recursive)."""
    if not dir_path.exists():
        return

    deleted = 0
    for pattern in patterns:
        for file in dir_path.glob(pattern):
            if file.is_file():
                file.unlink()
                deleted += 1
    tqdm.write(f"🧹 Deleted {deleted} files from {dir_path}")


@dataclass
class Args:
    """CLI arguments for simulation runner."""

    config: Path
    runs_per_combination: int | None = None
    max_total_runs: int | None = None
    max_turns: int = 500
    seed_offset: int = 0

    def __call__(self) -> int:
        if not self.config.exists():
            tqdm.write(f"Error: Config file not found: {self.config}", file=sys.stderr)
            return 1

        # Ask whether to wipe existing result files first
        if RESULTS_DIR.exists():
            while True:
                answer = (
                    input(
                        f"Delete all .parquet and .duckdb files in '{RESULTS_DIR}' before running? (y/n): ",
                    )
                    .strip()
                    .lower()
                )
                if answer in {"y", "yes"}:
                    delete_existing_results(RESULTS_DIR)
                    break
                if answer in {"n", "no", ""}:
                    tqdm.write("Keeping existing result files.")
                    break
                tqdm.write("Please answer with 'y' or 'n'.")

        config = SimulationConfig.from_toml(str(self.config))

        runs_per_combo = self.runs_per_combination or config.runs_per_combination
        max_total = self.max_total_runs or config.max_total_runs
        max_turns = self.max_turns or config.max_turns_per_race

        eligible_racers = config.get_eligible_racers()
        if not eligible_racers:
            tqdm.write(
                "Error: No eligible racers after include/exclude filters",
                file=sys.stderr,
            )
            return 1

        tqdm.write(f"Eligible racers: {len(eligible_racers)}")
        tqdm.write(f"Racer counts: {config.racer_counts}")
        tqdm.write(f"Boards: {config.boards}")
        tqdm.write(f"Runs per combination: {runs_per_combo or 'unlimited'}")
        tqdm.write(f"Max total runs: {max_total or 'unlimited'}")
        tqdm.write("")

        combo_gen = generate_combinations(
            eligible_racers=eligible_racers,
            racer_counts=config.racer_counts,
            boards=config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
            seed_offset=self.seed_offset,
        )

        db = SimulationDatabase(RESULTS_DIR)
        seen_hashes = db.get_known_hashes()
        initial_seen_count = len(seen_hashes)

        completed = 0
        skipped = 0
        aborted = 0
        unsaved_changes = 0

        total_expected = compute_total_runs(
            eligible_racers=eligible_racers,
            racer_counts=config.racer_counts,
            boards=config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
        )

        try:
            with tqdm(
                desc="Simulating",
                unit="race",
                total=total_expected,
                dynamic_ncols=True,
            ) as pbar:
                for game_config in combo_gen:
                    try:
                        config_hash = game_config.compute_hash()

                        if config_hash in seen_hashes:
                            skipped += 1
                            continue  # This triggers the finally block update

                        seen_hashes.add(config_hash)

                        result = run_single_simulation(game_config, max_turns)

                        if result.error_code == "MAX_TURNS_REACHED":
                            aborted += 1
                        else:
                            completed += 1
                            unsaved_changes += 1

                            # --- Ranking Logic ---
                            standings = sorted(
                                result.metrics,
                                key=lambda m: (m.final_vp, -m.turns_taken),
                                reverse=True,
                            )
                            rank_map: dict[int, int] = {}
                            if len(standings) > 0 and standings[0].final_vp > 0:
                                rank_map[standings[0].racer_id] = 1
                            if len(standings) > 1 and standings[1].final_vp > 0:
                                rank_map[standings[1].racer_id] = 2

                            for m in result.metrics:
                                m.rank = rank_map.get(m.racer_id)

                            race_record = Race(
                                config_hash=result.config_hash,
                                config_encoded=game_config.encoded,
                                seed=game_config.seed,
                                board=game_config.board,
                                racer_names=list(game_config.racers),
                                racer_count=len(game_config.racers),
                                timestamp=result.timestamp,
                                execution_time_ms=result.execution_time_ms,
                                error_code=result.error_code,
                                total_turns=result.turn_count,
                            )

                            # Changed: Pass position_logs to save_simulation
                            db.save_simulation(
                                race_record,
                                result.metrics,
                                result.position_logs,
                            )

                        if unsaved_changes >= BATCH_SIZE:
                            tqdm.write(
                                f"💾 Flushing {unsaved_changes} records to disk...",
                            )
                            db.flush_to_parquet()
                            unsaved_changes = 0

                    finally:
                        # Ensures progress bar moves even if we continue/skip
                        pbar.update(1)

        finally:
            if unsaved_changes > 0:
                tqdm.write(
                    f"💾 Flushing {unsaved_changes} remaining records to disk...",
                )
                db.flush_to_parquet()

            # Restore the nice summary
            summary = f"""
🏁 Simulation Batch Completed 🏁
──────────────────────────────
✅ Completed:       {completed}
⏭️  Skipped:         {skipped}
🛑 Aborted:         {aborted}
🆕 Unique Processed: {len(seen_hashes) - initial_seen_count}
📦 Total DB Size:    {len(seen_hashes)} races
──────────────────────────────
            """
            tqdm.write(summary)

        return 0


def main():
    """Entry point for CLI."""
    cappa.invoke(Args)


if __name__ == "__main__":
    sys.exit(main())
