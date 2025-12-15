from magical_athlete_simulator.engine.board import TripTile
from tests.test_utils import GameScenario, RacerConfig



def test_redirect_into_trap(scenario: type[GameScenario]):
    """
    Scenario: Racer tries to land on Huge Baby (at 5).
    Huge Baby blocks them to 4.
    Tile 4 has a TripTile.
    Verify: Racer lands on 4 and gets Tripped.
    """
    game = scenario(
        [
            RacerConfig(0, "Scoocher", start_pos=0),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[5],  # 0->5
    )

    # Manually inject a trap at tile 4
    game.engine.state.board.static_features[4] = [TripTile(None)]

    game.run_turn()

    scoocher = game.get_racer(0)

    # Should be at 4 (Blocked by Baby)
    assert scoocher.position == 4
    # Should be tripped (Landed on Trap)
    assert scoocher.tripped is True
