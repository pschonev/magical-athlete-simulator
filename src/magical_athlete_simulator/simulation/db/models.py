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
    racer_names: str
    racer_count: int

    # Execution Metadata
    timestamp: float
    execution_time_ms: float
    aborted: bool
    total_turns: int

    # Created at
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )


class RacerResult(SQLModel, table=True):
    """
    Represents the result of one racer in a specific race.
    """

    __tablename__ = "racer_results"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Composite Primary Key
    config_hash: str = Field(primary_key=True)
    racer_id: int = Field(primary_key=True)

    # Racer Identity
    racer_name: str

    # Results
    final_vp: int = 0
    turns_taken: int = 0
    recovery_turns: int = 0
    skipped_main_moves: int = 0
    rolling_turns: int = 0
    sum_dice_rolled: int = 0
    sum_dice_rolled_final: int = 0

    # Abilities
    ability_trigger_count: int = 0
    ability_self_target_count: int = 0
    ability_target_count: int = 0

    # Status
    finish_position: int | None = None
    eliminated: bool = False

    # Ranking
    rank: int | None = None


class RacePositionLog(SQLModel, table=True):
    """
    Log of board state at the end of each turn (flat format).
    One row per turn, with columns for each racer position.
    """

    __tablename__ = "race_position_logs"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    config_hash: str = Field(primary_key=True)
    turn_index: int = Field(primary_key=True)

    current_racer_id: int

    # Position columns (nullable for 4-racer games)
    pos_r0: int | None = None
    pos_r1: int | None = None
    pos_r2: int | None = None
    pos_r3: int | None = None
    pos_r4: int | None = None
    pos_r5: int | None = None
