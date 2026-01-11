from magical_athlete_simulator.core.state import GameRules
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_stickler_blocks_overshoot(scenario: type[GameScenario]):
    """Stickler prevents another racer from moving if they overshoot the finish."""
    game = scenario(
        [
            RacerConfig(0, "Stickler", start_pos=0),
            RacerConfig(1, "Banana", start_pos=28),  # Normal racer close to finish
        ],
        dice_rolls=[
            3,  # Stickler rolls 3 (moves 0->3)
            3,  # Banana rolls 3 (28 + 3 = 31 > 30). Should be vetoed.
            2,  # Stickler rolls 2
            2,  # Banana rolls 2 (28 + 2 = 30). Exact finish. Allowed.
        ],
        rules=GameRules(),
    )

    # Stickler turn 1
    game.run_turn()

    # Banana turn 1: Rolls 3. 28->31 is blocked. Stays at 28.
    game.run_turn()
    banana = game.get_racer(1)
    assert banana.position == 28
    assert not banana.finished

    # Stickler turn 2
    game.run_turn()

    # Banana turn 2: Rolls 2. 28->30 is exact. Finishes.
    game.run_turn()
    assert banana.position == 30
    assert banana.finished


def test_stickler_does_not_block_self(scenario: type[GameScenario]):
    """Stickler allows themselves to overshoot (rule says 'Other racers')."""
    game = scenario(
        [
            RacerConfig(0, "Stickler", start_pos=28),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[
            3,  # Stickler rolls 3 (28 + 3 = 31). Overshoot allowed for self?
                # Rules say "Other racers..." implying Stickler is exempt.
        ],
    )
    
    game.run_turn()
    stickler = game.get_racer(0)
    
    # Standard engine logic usually clamps finish to board length (30)
    # or marks them finished. Stickler constraint should NOT trigger a veto here.
    assert stickler.finished
    assert stickler.position == 31
