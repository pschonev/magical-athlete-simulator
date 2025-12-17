from magical_athlete_simulator.ai.sandbox import simulate_turn_for
from tests.test_utils import GameScenario, RacerConfig


def test_sandbox_turn_matches_real_turn(scenario: type[GameScenario]):
    """
    Same setup + same forced dice rolls:
    - Run 1 real turn
    - Run 1 sandbox-simulated turn
    Verify the sandbox outcome matches the real world end-of-turn state.
    """
    racer_cfgs = [
        RacerConfig(0, "Magician", start_pos=0),
        RacerConfig(1, "Centaur", start_pos=0),
    ]

    # Real game
    game_real = scenario(racer_cfgs, dice_rolls=[4])
    game_real.run_turn()

    real_positions = [game_real.get_racer(0).position, game_real.get_racer(1).position]
    real_tripped = [game_real.get_racer(0).tripped, game_real.get_racer(1).tripped]
    real_eliminated = [
        game_real.get_racer(0).eliminated,
        game_real.get_racer(1).eliminated,
    ]
    real_vp_after = [
        game_real.get_racer(0).victory_points,
        game_real.get_racer(1).victory_points,
    ]

    # Sandbox game (fresh instance, same starting config, same dice roll)
    game_sandbox = scenario(racer_cfgs, dice_rolls=[4])

    outcome = simulate_turn_for(
        racer_idx=game_sandbox.engine.state.current_racer_idx,
        engine=game_sandbox.engine
    )

    assert outcome.position == real_positions
    assert outcome.tripped == real_tripped
    assert outcome.eliminated == real_eliminated

    # vp_delta should match (after - before). Here "before" is always 0 unless you configure it.
    assert outcome.vp_delta == real_vp_after


def test_sandbox_does_not_mutate_original_state(scenario: type[GameScenario]):
    """
    Running simulate_turn_for must not change the actual game.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
        ],
        dice_rolls=[6],
    )

    orig_positions = [game.get_racer(0).position, game.get_racer(1).position]
    orig_vp = [game.get_racer(0).victory_points, game.get_racer(1).victory_points]
    orig_tripped = [game.get_racer(0).tripped, game.get_racer(1).tripped]
    orig_eliminated = [
        game.get_racer(0).eliminated,
        game.get_racer(1).eliminated,
    ]

    _ = simulate_turn_for(racer_idx=game.engine.state.current_racer_idx, engine=game.engine,)

    assert [game.get_racer(0).position, game.get_racer(1).position] == orig_positions
    assert [
        game.get_racer(0).victory_points,
        game.get_racer(1).victory_points,
    ] == orig_vp
    assert [game.get_racer(0).tripped, game.get_racer(1).tripped] == orig_tripped
    assert [
        game.get_racer(0).eliminated,
        game.get_racer(1).eliminated,
    ] == orig_eliminated


def test_turnoutcome_consistent_shapes(scenario: type[GameScenario]):
    """
    TurnOutcome should always have per-racer arrays of correct length.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Banana", start_pos=0),
        ],
        dice_rolls=[2, 4],
    )

    outcome = simulate_turn_for(racer_idx=0, engine=game.engine,)

    n = 3
    assert len(outcome.vp_delta) == n
    assert len(outcome.position) == n
    assert len(outcome.tripped) == n
    assert len(outcome.eliminated) == n
    assert len(outcome.start_position) == n
