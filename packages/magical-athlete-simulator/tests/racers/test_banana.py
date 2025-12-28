from test_utils import GameScenario, RacerConfig


def test_banana_landing_on_is_not_passing(scenario: type[GameScenario]):
    """
    Scenario: Racer starts at 0, Banana at 4. Racer rolls 4.
    Verify: Racer lands ON Banana. Does NOT trip.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
        ],
        dice_rolls=[4],
    )
    game.run_turn()

    racer = game.get_racer(0)
    assert racer.position == 4
    assert racer.tripped is False


def test_banana_trip_mechanic_full_cycle(scenario: type[GameScenario]):
    """
    Scenario:
    1. Racer passes Banana -> Gets Tripped.
    2. Racer attempts next turn -> Skips roll, Recovers.
    3. Racer attempts 3rd turn -> Rolls normally.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=2),
        ],
        dice_rolls=[
            6,  # Centaur
            1,  # Banana
            1,  # Banana
            6,  # Centaur
        ],
    )

    # --- Turn 1: Pass Banana ---
    game.run_turn()  # Centaur
    game.run_turn()  # Banana (skip)

    racer = game.get_racer(0)
    assert racer.position == 6
    assert racer.tripped is True

    # --- Turn 2: Skip Turn ---
    game.run_turn()  # Centaur (Tripped)

    # Should NOT have moved (6 + 6 = 12 would be wrong)
    assert racer.position == 6
    # Should allow movement next time
    assert racer.tripped is False

    game.run_turn()  # Banana (skip)

    # --- Turn 3: Normal Move ---
    game.run_turn()  # Centaur

    # Now moves 6->12
    assert racer.position == 12


def test_centaur_tramples_banana_and_gets_tripped(scenario: type[GameScenario]):
    """
    Scenario: Centaur moves past Banana.
    Expected Result:
    1. Centaur triggers Trample on Banana (Banana pushed back 2).
    2. Banana triggers Trip on Centaur (Centaur ends move Tripped).

    Both effects should resolve, regardless of who triggered first.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
        ],
        dice_rolls=[6],  # Centaur moves 0 -> 6, passing 4
    )

    game.run_turn()

    centaur = game.get_racer(0)
    banana = game.get_racer(1)

    # Centaur moved 6.
    # Was tripped? Yes.
    assert centaur.position == 6
    assert centaur.tripped is True, "Centaur should have been tripped by passing Banana"

    # Banana was trampled?
    # Start 4 -> Trampled (-2) -> 2.
    assert banana.position == 2, "Banana should have been trampled back to 2"
