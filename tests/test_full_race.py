import itertools

from tests.test_utils import GameScenario, RacerConfig

def test_full_race_6_racers_finishes_correctly(scenario: type[GameScenario]):
    """
    Scenario: A full 6-racer race using a variety of racers.
    Verify: 
    1. The race completes and is flagged as 'race_over'.
    2. At least two racers finish the race.
    3. Finished racers are correctly marked as inactive and have a finishing position.
    4. Finishing positions are assigned correctly (1st, 2nd, etc.).
    """
    racers = [
        RacerConfig(0, "Centaur"),
        RacerConfig(1, "HugeBaby"),
        RacerConfig(2, "Scoocher"),
        RacerConfig(3, "Banana"),
        RacerConfig(4, "Copycat"),
        RacerConfig(5, "Gunk"),
    ]
    
    # Use an infinite cycle of dice rolls to ensure the race can complete.
    infinite_dice = itertools.cycle([4, 5, 6, 3, 2, 4])
    game = scenario(racers, dice_rolls=list(itertools.islice(infinite_dice, 100))) 
    game.engine.rng.randint.side_effect = infinite_dice 

    # Run the entire race to completion
    game.engine.run_race()
    
    state = game.engine.state
    
    # 1. Verify the race is over
    assert state.race_over is True, "The 'race_over' flag should be set to True."
    
    # 2. Verify finishers
    finished_racers = [r for r in state.racers if r.finished]
    assert len(finished_racers) >= 2, f"Expected at least 2 finishers, but found {len(finished_racers)}."
    
    # 3. Verify status of finished racers
    for racer in finished_racers:
        assert racer.active is False, f"Racer {racer.name} finished and should be inactive."
        assert racer.finish_position is not None, f"Racer {racer.name} finished and needs a finish_position."

    # 4. Verify standings are logical
    # We filter for only racers with a finish_position, and use 'or 999' to satisfy 
    # basedpyright that the key will strictly return an int, never None.
    valid_finishers = [r for r in finished_racers if r.finish_position is not None]
    
    standings = sorted(
        valid_finishers, 
        key=lambda r: r.finish_position if r.finish_position is not None else 999
    )
    
    assert standings[0].finish_position == 1, "The first place racer should have finish_position == 1."
    assert standings[1].finish_position == 2, "The second place racer should have finish_position == 2."

    # Winners (deterministic)
    assert state.racers[2].finish_position == 1 # 2:Scoocher comes first
    assert state.racers[4].finish_position == 4 # 4:Copycat comes second

    # VP
    assert state.racers[2].victory_points == 1 # 2:Scoocher comes first
    assert state.racers[4].finish_position == 4 # 4:Copycat comes second
