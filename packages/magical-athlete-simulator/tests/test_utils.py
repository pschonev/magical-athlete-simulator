from dataclasses import dataclass
from unittest.mock import MagicMock

from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.state import GameRules, GameState, LogContext, RacerState
from magical_athlete_simulator.core.types import AbilityName, RacerName
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS, Board
from magical_athlete_simulator.engine.game_engine import GameEngine



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
        board: Board | None = None,
        rules: GameRules | None = None,
    ):
        racers: list[RacerState] = []

        # 1. Setup Racers from Config
        for cfg in racers_config:
            r = RacerState(cfg.idx, cfg.name, position=cfg.start_pos)
            racers.append(r)

        # 2. Mock the RNG
        self.mock_rng: MagicMock = MagicMock()


        # 3. Initialize Engine
        if board is None:
            board = BOARD_DEFINITIONS["standard"]()

        if rules is None:
            rules = GameRules()
        self.state: GameState = GameState(racers, board=board, rules=rules)

        engine_id = next(ENGINE_ID_COUNTER)
        self.engine: GameEngine = GameEngine(self.state, self.mock_rng, log_context=LogContext(engine_id=engine_id,
            engine_level=0,
            parent_engine_id=None,
            ))

        if dice_rolls:
            self.set_dice_rolls(dice_rolls)

    def set_dice_rolls(self, rolls: list[int]):
        """Script the dice rolls (e.g., [1, 6])."""
        self.mock_rng.randint.side_effect = rolls

    def run_turn(self):
        self.engine.run_turn()
        self.engine._advance_turn()  # pyright: ignore[reportPrivateUsage]

    def get_racer(self, idx: int) -> RacerState:
        return self.engine.get_racer(idx)
