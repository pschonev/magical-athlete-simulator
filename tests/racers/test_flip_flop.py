from tests.test_utils import GameScenario, RacerConfig

def test_flip_flop_swaps_with_best_target(scenario: type[GameScenario]):
    """Flip Flop should choose the target closest to start line among valid candidates (>=6 spaces ahead)."""
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "PartyAnimal", start_pos=20),
        ],
        dice_rolls=[1]  # Roll is unused if ability triggers
    )
    
    # 0: FlipFlop(0), 1: TargetNear(10), 2: TargetFar(20)
    # Both are >= 6 ahead. TargetNear is closer to start (pos 10 < 20).
    game.run_turn()
    
    ff = game.get_racer(0)
    partyanimal = game.get_racer(2)
    
    assert ff.position == 20, f"FlipFlop should swap to 20, is at {ff.position}"
    assert partyanimal.position == 0, f"PartyAnimal should swap to 0, is at {partyanimal.position}"
    assert ff.main_move_consumed is True, "Main move should be marked consumed"

def test_flip_flop_ignores_invalid_targets(scenario: type[GameScenario]):
    """Flip Flop should not swap if no target is >= 6 spaces ahead."""
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=10),
            RacerConfig(1, "Centaur", start_pos=13), # +3 ahead
            RacerConfig(2, "PartyAnimal", start_pos=5),         # -5 behind
        ],
        dice_rolls=[2]  # Should roll normally
    )
    
    game.run_turn()
    
    ff = game.get_racer(0)
    # Should move 10 + 2 = 12
    assert ff.position == 12, f"Flip Flop should move normally to 12, is at {ff.position}"
    assert ff.main_move_consumed is False
