from tests.test_utils import GameScenario, RacerConfig


def test_scoocher_ignores_own_ability(scenario: type[GameScenario]):
    """
    Scenario: Scoocher uses an ability (e.g. if they had one, or simple move).
    Verify: Does not trigger self.
    """
    game = scenario([RacerConfig(0, "Scoocher", start_pos=0)], dice_rolls=[4])
    game.run_turn()
    assert game.get_racer(0).position == 4  # Just the main move


def test_scoocher_productive_loop_duplicate(scenario: type[GameScenario]):
    """
    Scenario: Two Scoochers. Someone else triggers an ability.
    Sequence:
    - Trigger happens.
    - Scoocher A moves (Triggers B).
    - Scoocher B moves (Triggers A).
    - Scoocher A moves (Triggers B)...
    Verify: Engine detects loop and halts after one cycle.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=10),  # Scoocher A
            RacerConfig(2, "Scoocher", start_pos=19),  # Scoocher B
        ],
        dice_rolls=[1, 6],  # Magician rolls 1 (Trigger), then 6
    )

    game.run_turn()

    assert game.get_racer(1).position == 22
    assert game.get_racer(2).position == 30


def test_scoocher_reacts_to_every_huge_baby_push(scenario: type[GameScenario]):
    """
    Scenario: Huge Baby moves onto a tile with two other racers.
    Verify: Scoocher reacts to BOTH push events and moves twice.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=8),  # Victim 1
            RacerConfig(2, "Banana", start_pos=8),  # Victim 2
            RacerConfig(3, "Scoocher", start_pos=20),  # Observer
        ],
        dice_rolls=[3],  # Huge Baby moves 5 -> 8
    )

    game.run_turn()

    # Centaur and Banana are pushed from 8 to 7.
    assert game.get_racer(1).position == 7
    assert game.get_racer(2).position == 7

    # Scoocher should have moved twice (20 -> 22).
    assert game.get_racer(3).position == 22, (
        f"Scoocher should be at 22 but is at {game.get_racer(3).position}"
    )
