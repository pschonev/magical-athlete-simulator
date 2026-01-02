"""Database models for simulation results."""

import datetime

from sqlmodel import Field, SQLModel


class Race(SQLModel, table=True):
    """
    Represents a single race simulation.
    Maps to races.parquet
    """

    __tablename__ = "races"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Primary Key
    config_hash: str = Field(primary_key=True)

    # Configuration Details
    seed: int
    board: str
    racer_names: str  # Comma-separated list of racer names (canonical order)
    racer_count: int

    # Execution Metadata
    timestamp: float
    execution_time_ms: float
    aborted: bool
    total_turns: int

    # Created at (for sorting/archival)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )


class RacerResult(SQLModel, table=True):
    """
    Represents the result of one racer in a specific race.
    Acts as BOTH the runtime accumulator and the database persistence model.
    """

    __tablename__ = "racer_results"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Composite Primary Key (config_hash + racer_id)
    config_hash: str = Field(primary_key=True)
    racer_id: int = Field(primary_key=True)

    # Racer Identity
    racer_name: str

    # Results (Initialized to 0/False for runtime accumulation)
    final_vp: int = 0
    turns_taken: int = 0
    recovery_turns: int = 0
    sum_dice_rolled: int = 0

    # Abilities
    ability_trigger_count: int = 0
    ability_self_target_count: int = 0
    ability_target_count: int = 0

    # Status
    finish_position: int | None = None
    eliminated: bool = False

    # Ranking (1st, 2nd, or NULL for everyone else)
    # This is calculated AFTER the race by the runner/CLI
    rank: int | None = None
