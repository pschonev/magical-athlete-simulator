from magical_athlete_simulator.engine.board import TripTile
from tests.test_utils import GameScenario, RacerConfig
from magical_athlete_simulator.engine.board import Board, MoveDeltaTile
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



def build_finish_priority_board() -> Board:
    """
    Custom board for the finish-line priority test:
    - Tile 27: +3 MoveDeltaTile
    - Finish at 30
    """
    return Board(
        length=30,
        static_features={
            27: [MoveDeltaTile(owner_idx=None, delta=3)],
        },
    )

def test_board_tile_priority_over_scoocher(scenario: type[GameScenario]):
    """
    Scenario:
    - Board: finish at 30, +3 tile on 27.
    - Racers:
      0: Centaur at 25 (active)
      1: Gunk at 26 (Slime: -1 to others' rolls)
      2: Scoocher at 28 (ScoochStep: +1 when others move)
    - Dice: Centaur rolls 3.

    Expected logic:
    - Raw roll 3, Gunk's Slime reduces effective move by 1 → Centaur moves 25 -> 27.
    - Landing on tile 27 triggers MoveDelta(+3) as a board effect.
    - Centaur is moved 27 -> 30 and crosses the finish line FIRST, earning 4 VP.
    - Scoocher may or may not move from ScoochStep, but must not finish before Centaur.
    """

    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=25),
            RacerConfig(1, "Gunk", start_pos=26),
            RacerConfig(2, "Scoocher", start_pos=28),
        ],
        dice_rolls=[3],  # Shown roll 3 -> effective 2 before tile, then +3 from tile
        board=build_finish_priority_board(),
    )

    game.run_turn()

    centaur = game.get_racer(0)
    scoocher = game.get_racer(2)

    # Centaur should have finished first at position 30
    assert centaur.position == 30, f"Centaur should be at 30, but is at {centaur.position}"
    assert centaur.finished is True
    assert centaur.finish_position == 1, (
        f"Centaur should finish first, but has finish_position={centaur.finish_position}"
    )
    assert centaur.victory_points == 4, (
        f"Centaur should have 4 VP for first place, but has {centaur.victory_points}"
    )

    # Scoocher must not have finished before Centaur
    assert not (scoocher.finished and scoocher.finish_position == 1), (
        "Scoocher must not finish before Centaur in this scenario"
    )
