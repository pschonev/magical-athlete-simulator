from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_leaptoad_jumps_occupied_spaces(scenario: type[GameScenario]):
    """Leaptoad skips occupied spaces without counting cost."""
    game = scenario(
        [
            RacerConfig(0, "Leaptoad", start_pos=0),
            RacerConfig(1, "Banana", start_pos=1), # Obstacle 1
            RacerConfig(2, "Mastermind", start_pos=2),   # Obstacle 2
        ],
        dice_rolls=[
            1,  # Leaptoad rolls 1.
                # Path: 0 -> 1(Occ) -> 2(Occ) -> 3(Empty).
                # 1 Step consumed. Lands on 3.
        ],
    )

    game.run_turn()
    leaptoad = game.get_racer(0)
    assert leaptoad.position == 3


def test_leaptoad_stickler_interaction(scenario: type[GameScenario]):
    """
    Leaptoad calculates path first, then Stickler validates result.
    If Leaptoad jumps past finish due to obstacles, Stickler should block it.
    """
    game = scenario(
        [
            RacerConfig(0, "Stickler", start_pos=0),
            RacerConfig(1, "Leaptoad", start_pos=28),
            RacerConfig(2, "Banana", start_pos=29), # Block space before finish
        ],
        dice_rolls=[
            1, # Stickler moves
            1, # Leaptoad rolls 1.
               # Start 28. Next is 29 (Occupied by Banana).
               # Jump to 30.
               # 1 Step consumed. Destination 30.
               # Stickler Validates: 30 <= 30? Yes.
        ],
    )

    # Stickler moves
    game.run_turn()

    # Leaptoad moves. 28 + 1 (jump over 29) = 30. Valid exact finish.
    game.run_turn()
    leaptoad = game.get_racer(1)
    assert leaptoad.position == 30
    assert leaptoad.finished


def test_leaptoad_stickler_interaction_failure(scenario: type[GameScenario]):
    """Leaptoad jumps TOO far because of obstacles and gets blocked by Stickler."""
    game = scenario(
        [
            RacerConfig(0, "Stickler", start_pos=0),
            RacerConfig(1, "Leaptoad", start_pos=28),
            RacerConfig(2, "Banana", start_pos=29), # Occupied
        ],
        dice_rolls=[
            1, # Stickler
            2, # Leaptoad rolls 2.
               # Start 28.
               # Step 1: 29 is occupied. Jump to 30. Cost 1.
               # Step 2: From 30 -> 31. Cost 2.
               # Result: 31.
               # Stickler Veto: 31 > 30. Blocked.
        ],
    )
    
    game.run_turn() # Stickler
    
    game.run_turn() # Leaptoad
    leaptoad = game.get_racer(1)
    
    # Should stay at 28 because 31 is invalid according to Stickler
    assert leaptoad.position == 28
    assert not leaptoad.finished

def test_leaptoad_backward_jump_chain(scenario: type[GameScenario]):
    """
    Leaptoad moves backward (due to Centaur Trample), jumps an obstacle (Mastermind),
    and lands on HugeBaby.
    
    Since Leaptoad usually skips ACTIVE racers, we mark HugeBaby as FINISHED.
    This causes Leaptoad to see the tile as 'valid' to land on, triggering
    HugeBaby's modifier which pushes him back further.

    Setup:
    - Centaur @ 0 (Current Player)
    - HugeBaby @ 7 (Finished/Inactive, but Blocker Active)
    - Mastermind @ 9 (Active Obstacle)
    - Leaptoad @ 10 (Victim)
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=8),
            RacerConfig(1, "HugeBaby", start_pos=7),
            RacerConfig(2, "Mastermind", start_pos=8),
            RacerConfig(3, "Leaptoad", start_pos=10),
        ],
        dice_rolls=[
            3, # Centaur moves (8 -> 11), passing Leaptoad.
        ],
    )

    # Run Centaur's turn
    game.run_turn()
    
    leaptoad = game.get_racer(3)
    
    # move back 2, jumping over Mastermind for 3, landing on HugeBaby for 4 (10->6)
    assert leaptoad.position == 6
