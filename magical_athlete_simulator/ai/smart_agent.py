from typing import override

from magical_athlete_simulator.core.protocols import (
    Agent,
    BoardLike,
    BooleanDecision,
    DecisionReason,
    GameState,
    RacerState,
    SelectionDecision,
)
from magical_athlete_simulator.engine.board import MoveDeltaTile, TripTile


class SmartAgent(Agent):
    """A concrete agent that uses deterministic functions to make decisions."""

    def __init__(self, board: BoardLike):
        self.board: BoardLike = board

    @override
    def make_boolean_decision(self, ctx: BooleanDecision) -> bool:
        if ctx.reason == DecisionReason.MAGICAL_REROLL:
            # Pass the board specifically for the reroll calculation
            return ai_should_reroll(ctx, self.board)

        return False  # Default safe option for unknown decisions

    @override
    def make_selection_decision(self, ctx: SelectionDecision) -> int:
        if ctx.reason == DecisionReason.COPY_LEAD_TARGET:
            return ai_choose_copy_target(ctx)
        return 0


def ai_should_reroll(ctx: BooleanDecision, board: BoardLike) -> bool:
    """Deterministic logic for MagicalReroll.

    Returns True (Reroll) if:
    1. The roll is very low (<= 2).
    2. The landing spot contains a 'Bad' modifier (Trip or negative MoveDelta).
    """
    state: GameState = ctx.game_state
    me: RacerState = state.racers[ctx.source_racer_idx]
    current_roll = state.roll_state.final_value

    # 1. Base Heuristic: Reroll 1s and 2s automatically
    if current_roll <= 2:
        return True

    # 2. Lookahead Logic
    # Calculate where we would land with the current roll
    landing_spot = me.position + current_roll

    # We can't look past the finish line (no modifiers there usually)
    if landing_spot >= board.length:
        return False

    # Check for hazards on the target tile
    modifiers = board.get_modifiers_at(landing_spot)
    for mod in modifiers:
        # Avoid TripTiles at all costs
        if isinstance(mod, TripTile):
            return True

        # Avoid tiles that send us backward
        if isinstance(mod, MoveDeltaTile) and mod.delta < 0:
            return True

    return False


def ai_choose_copy_target(ctx: SelectionDecision) -> int:
    """Deterministic logic for CopyLead.
    Simply picks the first available option.
    Since the options are sorted by racer index before being passed here,
    this is completely deterministic.
    """
    if not ctx.options:
        return 0

    # Simple, testable, deterministic: always pick the first valid leader.
    return 0
