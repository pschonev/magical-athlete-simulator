from test_utils import GameScenario, RacerConfig

def test_baba_yaga_trips_multiple_arrivals(scenario: type[GameScenario]):
    """Baba Yaga arriving on a space with others should trip them."""
    game = scenario(
        [
            RacerConfig(0, "BabaYaga", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=4),
            RacerConfig(2, "Banana", start_pos=4),
        ],
        dice_rolls=[4] # Baba Yaga moves 0 -> 4
    )
    
    game.run_turn()
    
    baba_yaga = game.get_racer(0)
    centaur = game.get_racer(1)
    banana = game.get_racer(2)
    
    assert centaur.tripped is True, "Centaur should be tripped"
    assert banana.tripped is True, "Banana should be tripped"
    assert baba_yaga.tripped is False, "Baba Yaga should not be tripped"

def test_others_trip_arriving_on_baba_yaga(scenario: type[GameScenario]):
    """Racers arriving on Baba Yaga's space should be tripped."""
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=0),
            RacerConfig(1, "BabaYaga", start_pos=4),
        ],
        dice_rolls=[4] # Victim moves 0 -> 4
    )
    
    game.run_turn()
    
    banana = game.get_racer(0)
    baba_yaga = game.get_racer(1)
    assert banana.tripped is True, "Banana should be tripped by landing on Baba Yaga"
    assert baba_yaga.tripped is False, "Baba Yaga should not be tripped"
