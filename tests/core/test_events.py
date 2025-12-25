from magical_athlete_simulator.engine.board import Board, MoveDeltaTile
from tests.test_utils import GameScenario, RacerConfig

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

def test_chaos_chain_reaction(scenario: type[GameScenario]):
    """
    Recreates the specific chain reaction from the provided graphic.
    
    Initial State:
    - Centaur: 0
    - Huge Baby: 2
    - Scoocher: 3
    - Banana: 4
    
    Events:
    1. Centaur rolls 6 -> Lands on 6.
    2. Tile 6 (-4) triggers -> Centaur moves to 2.
    3. Huge Baby (at 2) pushes Centaur -> Centaur moves to 1.
    4. Centaur's Trample triggers on everyone he passed (0->6 implies passing 2,3,4).
       - Baby (2) -> Trampled to 0.
       - Scoocher (3) -> Trampled to 1.
       - Banana (4) -> Trampled to 2.
    
    5. Secondary Effects (as implied by outcome):
       - Why does Scoocher end at 10? 
         - Maybe "Scooch Step" triggers when someone ends their move near him?
         - If Centaur ended at 1, Scoocher (at 1) is adjacent. Scooch moves +3?
         - If Scooch lands on 4 (from 1+3), maybe Tile 3 (+3) isn't hit?
         - If Scooch lands on 4, Banana is there?
       
    Let's assert the FINAL state defined in the image text.
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
        board=build_graphic_board() # Use our custom board
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
    
    # 3. Banana: Starts 4 -> Ends 0
    # (This implies Banana was trampled 4->2, then moved back 2->4? Or never moved?)
    assert banana.position == 0, f"Banana should be at 0, but is at {banana.position}"

    # 1. Centaur: Starts 0 -> Ends 4, Tripped=True
    assert centaur.position == 4, f"Centaur should be at 4, but is at {centaur.position}"
    assert centaur.tripped is True, "Centaur should be tripped"
    
    # 2. Scoocher: Moves a whole lot in a cycle between DeltaTiles
    # misses two triggers of Trample because HugeBaby is already at 0
    assert scoocher.position == 3, f"Scoocher should be at 3, but is at {scoocher.position}"
    assert scoocher.tripped is False, "Scoocher should not be tripped"

