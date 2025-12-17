from typing import Callable
import pytest
from magical_athlete_simulator.engine.board import Board
from tests.test_utils import GameScenario, RacerConfig


@pytest.fixture
def scenario() -> Callable[..., GameScenario]:
    """Factory fixture to create scenarios."""

    def _builder(racers_config: list[RacerConfig], dice_rolls: list[int], board: Board | None = None) -> GameScenario:
        return GameScenario(racers_config, dice_rolls, board)

    return _builder
