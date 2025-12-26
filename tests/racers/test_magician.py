from tests.test_utils import GameScenario, RacerConfig


def test_magician_reroll_scoocher_interaction(scenario: type[GameScenario]):
    """
    Scenario: Magician rolls a 1 (triggers reroll), then a 6.
    Verify: Scoocher moves EXACTLY ONCE for the reroll event.
    """
    # CLEAR: We know exactly what 0, "Magician", and "MagicalReroll" refer to.
    # We can omit start_pos since it defaults to 0.
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(idx=1, name="Scoocher", abilities={"ScoochStep"}),
        ],
        dice_rolls=[1, 6],
    )

    game.run_turn()

    scoocher = game.get_racer(1)
    assert scoocher.position == 1

def test_magician_reroll_uses_new_roll_value(scenario: type[GameScenario]):
    """
    Scenario: Magician rolls a 1 (triggers reroll), then a 6.
    Verify: 
      1. Scoocher moves EXACTLY TWICE for the reroll event.
      2. Magician's final position is based on the NEW roll of 6.
    """
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(idx=1, name="Scoocher", abilities={"ScoochStep"}),
        ],
        dice_rolls=[1, 1, 6],
    )

    # run_turn() processes all events for the current racer's turn
    game.run_turn()

    magician = game.get_racer(0)
    scoocher = game.get_racer(1)

    # This assertion will pass, as the AbilityTriggeredEvent still fires.
    assert scoocher.position == 2, "Scoocher should have moved 2 spaces from ScoochStep"
    
    # THIS ASSERTION WILL FAIL: Magician's position will be 1, not 6.
    assert magician.position == 6, "Magician should have used the new roll value of 6"

def test_magician_reroll_applies_new_roll(scenario: type[GameScenario]):
    """
    Scenario: single Magician with MagicalReroll.
    First roll: 1 (triggers reroll), second roll: 6.
    Expectation: final position should be 6, not 1.
    """
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[1, 6],
    )

    game.run_turn()

    magician = game.get_racer(0)
    assert magician.position == 6
