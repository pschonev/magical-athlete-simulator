from tests.test_utils import GameScenario, RacerConfig

def test_flip_flop_vs_baba_yaga_simultaneous(scenario: type[GameScenario]):
    """
    Flip Flop swaps with Baba Yaga. 
    Sequential warp would place Flip Flop on Baba Yaga's space momentarily (or vice versa), triggering trip.
    Simultaneous warp should avoid this sharing state.
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "BabaYaga", start_pos=10),
        ],
        dice_rolls=[1] # Unused
    )
    
    # Flip Flop (0) is >6 behind Baba Yaga (10). Swap is valid.
    game.run_turn()
    
    ff = game.get_racer(0)
    baba = game.get_racer(1)
    
    assert ff.position == 10, "Flip Flop should be at 10"
    assert baba.position == 0, "Baba Yaga should be at 0"
    
    # This assertion will fail until simultaneous warp logic is implemented
    assert ff.tripped is False, "Flip Flop should not be tripped by Baba Yaga during swap"

def test_romantic_party_animal_simultaneous_arrival(scenario: type[GameScenario]):
    """
    Scenario:
    - Party Animal at 10.
    - Romantic at 5.
    - Other at 5.
    
    Party Animal Pulls (-1? No, towards PA). Everyone moves +1 towards 10.
    Romantic -> 6. Other -> 6.
    
    Sequential Execution (Current):
    1. Romantic moves 5->6. Lands. "Exactly one other?" No (Other is still at 5). No trigger.
    2. Other moves 5->6. Lands. "Exactly one other?" Yes (Romantic is at 6). Trigger.
    Result: Romantic triggers ONCE.
    
    Simultaneous Execution (Desired):
    1. Both move to 6 atomically.
    2. Romantic Arrival: Sees Other at 6. Trigger.
    3. Other Arrival: Sees Romantic at 6. Trigger.
    Result: Romantic triggers TWICE (once for self-arrival, once for other-arrival).
    
    (Note: Rules Clarification say "Romantic’s ability can trigger twice from a single shared arrival")
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=10),
            RacerConfig(1, "Romantic", start_pos=5),
            RacerConfig(2, "FlipFlop", start_pos=5),
        ],
        dice_rolls=[1] # PA moves normally after
    )
    
    game.run_turn()
    
    romantic = game.get_racer(1)
    
    # Initial 5 -> Pull to 6.
    # If Triggered Twice: 6 + 2 + 2 = 10.
    # If Triggered Once: 6 + 2 = 8.
    
    assert romantic.position == 10, f"Romantic should trigger twice (simultaneous arrival), ended at {romantic.position}"
