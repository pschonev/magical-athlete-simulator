from dataclasses import dataclass
from unittest.mock import MagicMock
from magical_athlete_simulator.game import (
    GameEngine,
    GameState,
    RacerName,
    RacerState,
    AbilityName,
    RACER_ABILITIES,
)


@dataclass
class RacerConfig:
    idx: int
    name: RacerName
    # Default to None to signal "use defaults"
    abilities: set[AbilityName] | None = None
    start_pos: int = 0

    def __post_init__(self):
        if self.abilities is None:
            # Enforce that the racer exists in our definition
            if self.name not in RACER_ABILITIES:
                raise ValueError(f"Racer '{self.name}' not found in RACER_ABILITIES. ")

            # Fetch default abilities
            defaults = RACER_ABILITIES[self.name]

            # Enforce that defaults aren't empty
            if not defaults:
                raise ValueError(
                    f"Racer '{self.name}' has no default abilities defined."
                )

            self.abilities = defaults.copy()


class GameScenario:
    """
    A reusable harness that wraps the GameEngine for testing.
    """

    def __init__(
        self,
        racers_config: list[RacerConfig],
        dice_rolls: list[int] | None = None,
    ):
        racers: list[RacerState] = []

        # 1. Setup Racers from Config
        for cfg in racers_config:
            r = RacerState(cfg.idx, cfg.name, position=cfg.start_pos)
            racers.append(r)

        # 2. Mock the RNG
        self.mock_rng: MagicMock = MagicMock()

        # 3. Initialize Engine
        self.state: GameState = GameState(racers)
        self.engine: GameEngine = GameEngine(self.state, self.mock_rng)

        if dice_rolls:
            self.set_dice_rolls(dice_rolls)

    def set_dice_rolls(self, rolls: list[int]):
        """Script the dice rolls (e.g., [1, 6])."""
        self.mock_rng.randint.side_effect = rolls  # pyright: ignore[reportAny]

    def run_turn(self):
        self.engine.run_turn()
        self.engine.advance_turn()

    def get_racer(self, idx: int) -> RacerState:
        return self.engine.get_racer(idx)
