import itertools
from test_utils import GameScenario, RacerConfig


def test_mastermind_predicts_winner_and_takes_second(scenario: type[GameScenario]):
    """
    Scenario: 
      - Mastermind (idx 0) vs Scoocher (idx 1) vs Gunk (idx 2).
      - Mastermind should predict Gunk (logic: pick leader).
      - Gunk finishes 1st.
    Verify: 
      - Mastermind correctly predicts Scoocher.
      - When Scoocher finishes 1st, Mastermind immediately becomes 2nd.
    """
    infinite_dice = itertools.cycle([2, 1, 6])
    
    game = scenario(
        [
            RacerConfig(idx=0, name="Mastermind", start_pos=0),
            RacerConfig(idx=1, name="Gunk", start_pos=10),
            RacerConfig(idx=2, name="Scoocher", start_pos=0),
        ],
        # Rolls: 
        # 1. Mastermind Turn: Rolls 1. Moves 1. Predicts Scoocher.
        # 2. Scoocher Turn: Rolls 6 (Cheat). Finishes (10+6 > Finish).
        dice_rolls=list(itertools.islice(infinite_dice, 100)), 
    )
    game.engine.rng.randint.side_effect = infinite_dice   # pyright: ignore[reportAttributeAccessIssue]
    # Turn 1: Mastermind
    # Triggers TurnStart -> MastermindPredict -> Selects Scoocher
    game.engine.run_race()
    
    mastermind = game.get_racer(0)
    gunk = game.get_racer(1)

    # Verify Scoocher Win
    assert gunk.finished
    assert gunk.finish_position == 1

    # Verify Mastermind "Piggyback" Win
    assert mastermind.finished
    assert mastermind.finish_position == 2


def test_mastermind_houserule_predicts_winner_and_takes_first(scenario: type[GameScenario]):
    """
    Scenario: 
      - Mastermind (idx 0) vs Scoocher (idx 1) vs Gunk (idx 2).
      - Scoocher starts significantly ahead (pos 10).
      - Mastermind should predict Scoocher (logic: pick leader).
      - Scoocher finishes 1st.
    Verify: 
      - Mastermind correctly predicts Scoocher.
      - When Scoocher finishes 1st, Mastermind steals 1st place.
    """
    infinite_dice = itertools.cycle([2, 1, 6])
    
    game = scenario(
        [
            RacerConfig(idx=0, name="Mastermind", start_pos=0),
            RacerConfig(idx=1, name="Gunk", start_pos=10),
            RacerConfig(idx=2, name="Scoocher", start_pos=0),
        ],
        # Rolls: 
        # 1. Mastermind Turn: Rolls 1. Moves 1. Predicts Scoocher.
        # 2. Scoocher Turn: Rolls 6 (Cheat). Finishes (10+6 > Finish).
        dice_rolls=list(itertools.islice(infinite_dice, 100)), 
    )
    game.engine.rng.randint.side_effect = infinite_dice   # pyright: ignore[reportAttributeAccessIssue]
    game.engine.state.rules.hr_mastermind_steal_1st = True
    # Turn 1: Mastermind
    # Triggers TurnStart -> MastermindPredict -> Selects Scoocher
    game.engine.run_race()
    
    mastermind = game.get_racer(0)
    gunk = game.get_racer(1)

    # Verify Gunk bumped to 2nd
    assert gunk.finished
    assert gunk.finish_position == 2
    assert gunk.victory_points == game.state.rules.winner_vp[gunk.finish_position - 1]

    # Verify Mastermind win steal
    assert mastermind.finished
    assert mastermind.finish_position == 1
    assert mastermind.victory_points == game.state.rules.winner_vp[mastermind.finish_position - 1]
