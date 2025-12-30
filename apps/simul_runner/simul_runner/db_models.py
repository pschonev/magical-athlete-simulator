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
    Maps to racer_results.parquet
    """

    __tablename__ = "racer_results"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Composite Primary Key (config_hash + racer_name)
    config_hash: str = Field(primary_key=True)
    racer_name: str = Field(primary_key=True)

    # Results
    final_vp: int
    turns_taken: int
    total_dice_rolled: int
    ability_trigger_count: int

    # Status
    finished: bool
    eliminated: bool

    # Ranking (1st, 2nd, etc. - useful for analysis)
    rank: int | None = None
