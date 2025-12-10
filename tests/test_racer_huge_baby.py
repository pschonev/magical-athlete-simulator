from tests.test_utils import GameScenario, RacerConfig


def test_huge_baby_push_timing_and_subsequent_move(scenario: type[GameScenario]):
    """
    Verify Huge Baby pushes victims immediately upon arrival, affecting
    their subsequent start position for the Main Move.
    """
    # Setup: PartyAnimal (5) pulls HugeBaby (4) onto same square.
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=5),
            RacerConfig(1, "HugeBaby", start_pos=4),
        ],
        dice_rolls=[4],  # PartyAnimal rolls 4
    )

    game.run_turn()

    # 1. Baby pulled to 5
    assert game.get_racer(1).position == 5

    # 2. PartyAnimal Logic:
    # Start (5) -> Pulled Baby lands -> Pushed to (4) -> Roll 4 -> End (8)
    assert game.get_racer(0).position == 8, (
        f"Expected pos 8 (Pushed 5->4, then moved 4). Got {game.get_racer(0).position}."
    )


def test_huge_baby_safe_at_start(scenario: type[GameScenario]):
    """
    Scenario: Baby and others are at Start (0).
    Verify: No pushing occurs.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[0],  # Dummy roll
    )

    game.run_turn()  # Baby turn
    assert game.get_racer(1).position == 0  # Scoocher stays


def test_huge_baby_bulldozes_crowd(scenario: type[GameScenario]):
    """
    Scenario: 3 Racers at pos 10. Baby moves 6->10.
    Verify: All 3 existing racers pushed to 9.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Banana", start_pos=10),
            RacerConfig(2, "Centaur", start_pos=10),
            RacerConfig(3, "Magician", start_pos=10),
        ],
        dice_rolls=[4],  # 6->10
    )

    game.run_turn()

    assert game.get_racer(0).position == 10  # Baby lands
    assert game.get_racer(1).position == 9
    assert game.get_racer(2).position == 9
    assert game.get_racer(3).position == 9


def test_huge_baby_victim_lands_on_baby(scenario: type[GameScenario]):
    """
    Scenario: Baby is at 5. Racer lands on 5.
    Verify: Racer pushed to 4. Baby stays at 5.
    """
    game = scenario(
        [
            RacerConfig(0, "Gunk", start_pos=2),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[3],  # 2->5
    )

    game.run_turn()

    assert game.get_racer(0).position == 4, game.engine.board.dump_state()
    assert game.get_racer(1).position == 5
