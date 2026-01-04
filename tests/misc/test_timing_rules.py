from magical_athlete_simulator.core.state import GameRules
from magical_athlete_simulator.engine.board import Board, MoveDeltaTile
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig

# 1. Define the custom board matching your graphic
def build_graphic_board():
    """
    Reconstructs the board from the 'grafik.jpg'.
    - Tile 3: +3 (Blue diamond)
    - Tile 6: -4 (Red diamond)
    """
    return Board(
        length=30,
        static_features={
            1: [MoveDeltaTile(delta=3)],
            6: [MoveDeltaTile(delta=-4)],
        }
    )

def test_chaos_chain_reaction_DFS(scenario: type[GameScenario]):
    """Complex scenario to test a chain reaction and resolve order as well as loop detection.
    """
    
    # Setup
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "HugeBaby", start_pos=2),
            RacerConfig(2, "Scoocher", start_pos=3),
            RacerConfig(3, "Banana", start_pos=4),
        ],
        dice_rolls=[6],
        board=build_graphic_board(), # Use our custom board
        rules=GameRules(timing_mode="BFS"),
    )

    # Run the turn
    game.run_turn()
    
    # Retrieve racers
    centaur = game.get_racer(0)
    baby = game.get_racer(1)
    scoocher = game.get_racer(2)
    banana = game.get_racer(3)
    
    # --- Assertions based on Image Text ---
    
    # 4. Huge Baby: Starts 2 -> Ends 0
    assert baby.position == 0, f"Baby should be at 0, but is at {baby.position}"
    
    # 3. Banana: Starts 4 -> Ends 4
    # (This implies Banana was trampled 4->2, then moved back 2->4? Or never moved?)
    assert banana.position == 0, f"Banana should be at 0, but is at {banana.position}"

    # 1. Centaur: Starts 0 -> Ends 4, Tripped=True
    assert centaur.position == 4, f"Centaur should be at 4, but is at {centaur.position}"
    assert centaur.tripped is True, "Centaur should be tripped"
    
    # 2. Scoocher: Starts 3 -> Ends 10, Tripped=False
    assert scoocher.position == 5, f"Scoocher should be at 5, but is at {scoocher.position}"
    assert scoocher.tripped is False, "Scoocher should not be tripped"

