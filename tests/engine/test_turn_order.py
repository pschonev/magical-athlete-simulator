from typing import cast
from magical_athlete_simulator.racers.genius import AbilityGenius
from tests.test_utils import RacerConfig, GameScenario


def test_skipper_steals_next_turn_and_then_order_resumes(scenario: type[GameScenario]):
    """
    Scenario:
    - Racer 0 rolls a 1 -> Skipper should take the *next* turn.
    - After Skipper's stolen turn, play resumes to Skipper's left as usual.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Scoocher", start_pos=0),
            RacerConfig(3, "Skipper", start_pos=0),
        ],
        dice_rolls=[
            1,  # Magician's roll (triggers Skipper)
            2,
            1,
            3,  # Skipper's roll (doesn't matter, just advances)
        ],
    )

    assert game.engine.state.current_racer_idx == 0

    # Turn 0 (Magician rolls 1) -> next should be Skipper
    game.run_turn()
    assert game.engine.state.roll_state.base_value == 1
    assert game.engine.state.current_racer_idx == 3
    assert game.engine.state.next_turn_override is None  # consumed in advance_turn

    # Turn 1 (Skipper takes stolen turn) -> next should be Magician again, skipping Centaur
    game.run_turn()
    assert game.engine.state.current_racer_idx == 0
    assert game.engine.get_racer(3).position == 3

    # Check if Scoocher only got triggered twice for Magician reroll and once for Skipper
    assert game.engine.get_racer(2).position == 3


def test_genius_gets_back_to_back_turn_on_correct_prediction(scenario: type[GameScenario]):
    """
    Scenario:
    - Genius is current player (idx 0).
    - Genius predicts correctly -> Genius takes an additional full turn afterward.
    """
    game = scenario(
        [
            RacerConfig(0, "Genius", start_pos=0),
            RacerConfig(1, "Magician", start_pos=0),
        ],
        dice_rolls=[
            6,  # Genius roll: should match Genius's default/forced prediction in your implementation
            2,  # Genius extra turn roll (any number)
        ],
    )

    # Turn 0 (Genius) -> should still be Genius if extra turn is granted
    game.run_turn()
    assert game.engine.state.current_racer_idx == 0
    assert game.engine.state.next_turn_override is None  # consumed

    # Turn 1 (Genius again) -> now should proceed to Magician
    game.run_turn()
    assert game.engine.state.current_racer_idx == 1
    assert game.engine.get_racer(0).position == 8


def test_genius_predicts_1_but_skipper_steals_next_turn(scenario: type[GameScenario]):
    """
    Clarification case:
    If Genius predicts a 1 and rolls a 1, Skipper steals the next turn
    because Skipper triggers after Genius. (Last-write-wins override.)
    """
    game = scenario(
        [
            RacerConfig(0, "Genius", start_pos=0),
            RacerConfig(1, "Skipper", start_pos=0),
        ],
        dice_rolls=[
            1,  # Genius roll
            4,  # Skipper stolen turn roll (any number)
        ],
    )

    # Force Genius's prediction to 1 for this test (so we can hit the interaction deterministically).
    # Adjust the ability key/name here if your project uses a different AbilityName string.
    genius_ability = cast(AbilityGenius, game.engine.state.racers[0].active_abilities["GeniusPrediction"])
    genius_ability.prediction = 1

    # Turn 0: Genius rolls 1 -> Genius would "earn" extra turn, but Skipper steals it -> next is Skipper.
    game.run_turn()
    assert game.engine.state.current_racer_idx == 1
    assert game.engine.state.next_turn_override is None  # consumed

    # Turn 1: Skipper takes stolen turn -> then normal order resumes to Genius (only 2 racers).
    game.run_turn()
    assert game.engine.state.current_racer_idx == 0
