from tests.test_utils import GameScenario, RacerConfig

def test_romantic_triggers_on_pair_formation(scenario: type[GameScenario]):
    """Romantic moves +2 when someone lands to create a pair (Romantic lands on someone)."""
    # 0: Romantic (Active), 1: Banana (Sitter at 4)
    game = scenario(
        [
            RacerConfig(0, "Romantic", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
        ],
        dice_rolls=[4] # Romantic 0 -> 4
    )
    
    game.run_turn() 
    # Romantic lands on 4. Pairs with Banana (Count=2). Trigger +2.
    # Romantic moves 4 -> 6.
    
    romantic = game.get_racer(0)
    assert romantic.position == 6, f"Romantic should land on 4, trigger ability, move +2 to 6. Pos: {romantic.position}"


def test_romantic_ignores_crowds(scenario: type[GameScenario]):
    """Romantic does not trigger if 3 racers end up on a tile."""
    # 0: Flip Flop (Active), 1: Banana (at 4), 2: Party Animal (at 4), 3: Romantic (Observer at 10)
    game = scenario(
        [
            RacerConfig(0, "Gunk", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
            RacerConfig(2, "PartyAnimal", start_pos=4),
            RacerConfig(3, "Romantic", start_pos=10),
        ],
        dice_rolls=[4] # Flip Flop 0 -> 4. Now 3 racers at 4 (Flip Flop, Banana, Party Animal).
    )
    
    game.run_turn()
    
    romantic = game.get_racer(3)
    # The arrival created a group of 3. Romantic condition (Exactly one other) fails.
    assert romantic.position == 10, "Romantic should not move (count is 3)"


def test_romantic_chain_reaction(scenario: type[GameScenario]):
    """Romantic lands on a singleton, moves +2, lands on another singleton, moves +2 again."""
    # 0: Romantic (Active), 1: Banana (at 4), 2: Flip Flop (at 6)
    game = scenario(
        [
            RacerConfig(0, "Romantic", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
            RacerConfig(2, "FlipFlop", start_pos=6),
        ],
        dice_rolls=[4] 
        # Romantic 0 -> 4 (Pair with Banana) -> Trigger +2.
        # Romantic 4 -> 6 (Pair with Flip Flop) -> Trigger +2.
        # Romantic 6 -> 8.
    )
    
    game.run_turn()
    
    romantic = game.get_racer(0)
    assert romantic.position == 8, f"Romantic should chain move 4->6->8. Pos: {romantic.position}"
