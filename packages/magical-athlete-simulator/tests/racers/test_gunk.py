from test_utils import GameScenario, RacerConfig


def test_gunk_slime_reduces_movement(scenario: type[GameScenario]):
    """
    Scenario: Gunk is present. Another racer rolls.
    Verify: Final move is Base - 1.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=0),
        ],
        dice_rolls=[4],  # Centaur rolls 4
    )
    game.run_turn()  # Centaur

    # 4 - 1 = 3
    assert game.get_racer(0).position == 3


def test_gunk_does_not_slime_self(scenario: type[GameScenario]):
    """
    Scenario: Gunk rolls.
    Verify: No reduction.
    """
    game = scenario([RacerConfig(0, "Gunk", start_pos=0)], dice_rolls=[4])

    game.run_turn()
    assert game.get_racer(0).position == 4


def test_gunk_triggers_scoocher(scenario: type[GameScenario]):
    """
    Scenario: Gunk slimes Centaur. Scoocher is watching.
    Verify:
    1. Slime reduces Centaur's move.
    2. Scoocher sees "Slime" ability trigger and moves 1.
    3. Scoocher moves BEFORE Centaur completes their move.
    """
    # Setup: Scoocher at 10. Centaur at 0. Gunk at 0.
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=0),
            RacerConfig(2, "Scoocher", start_pos=10),
        ],
        dice_rolls=[5],  # Centaur rolls
    )

    game.run_turn()

    # 1. Check Centaur: 5 - 1 (Slime) = 4.
    assert game.get_racer(0).position == 4

    # 2. Check Scoocher: Moved 10 -> 11.
    assert game.get_racer(2).position == 11


def test_gunk_slime_stacking_with_boost(scenario: type[GameScenario]):
    """
    Scenario: PartyAnimal (Boost +1) is Slimed by Gunk (-1).
    Verify: The modifiers cancel out perfectly.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=2),  # Neighboring Gunk
            RacerConfig(1, "Gunk", start_pos=1),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    # Base 4 + 1 (Boost) - 1 (Slime) = 4.
    # Move 2 -> 6.
    assert game.get_racer(0).position == 6
