import logging
import re
from typing import TYPE_CHECKING, get_args, override

from rich.highlighter import Highlighter
from rich.logging import RichHandler

from magical_athlete_simulator.core.types import AbilityName, ModifierName, RacerName

if TYPE_CHECKING:
    from rich.text import Text

    from magical_athlete_simulator.core.state import LogContext
    from magical_athlete_simulator.engine.game_engine import GameEngine

RACER_NAMES = set(get_args(RacerName))
ABILITY_NAMES = set(get_args(AbilityName))
MODIFIER_NAMES = set(get_args(ModifierName))

# Precompiled regex patterns for highlighting
ABILITY_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, ABILITY_NAMES))})\b")
MODIFIER_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, MODIFIER_NAMES))})\b")
RACER_PATTERN = re.compile(rf"(?<!\[)\b({'|'.join(map(re.escape, RACER_NAMES))})\b")


# Simple color theme for Rich
# Updated Color Theme for High Contrast Dark Mode
COLOR = {
    "move": "bold green",
    "warp": "bold spring_green1",  # Brighter green for warps
    "main_move": "bold magenta",
    "warning": "bold red",
    "ability": "bold cyan",  # CHANGED: Blue -> Cyan (much better on black)
    "racer": "bold yellow",  # CHANGED: Made bold for pop
    "prefix": "grey50",  # CHANGED: Dim -> Explicit grey color
    "level": "bold",
    "modifier": "bold orange1",  # CHANGED: Distinct from ability cyan
    "board": "bold white",
    "dice_roll": "bold plum1",  # Brighter purple
}


class ContextFilter(logging.Filter):
    """Inject per-engine runtime context into every log record."""

    def __init__(self, engine: GameEngine, name: str = "") -> None:
        super().__init__(name)  # name is for logger-name filtering; keep default
        self.engine: GameEngine = engine  # store the existing engine instance

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        logctx: LogContext = self.engine.log_context
        record.total_turn = logctx.total_turn
        record.turn_log_count = logctx.turn_log_count
        record.racer_repr = logctx.current_racer_repr
        record.engine_id = logctx.engine_id
        record.engine_level = logctx.engine_level
        record.parent_engine_id = logctx.parent_engine_id
        logctx.inc_log_count()
        return True


class RichMarkupFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        total_turn = getattr(record, "total_turn", 0)
        turn_log_count = getattr(record, "turn_log_count", 0)
        racer_repr = getattr(record, "racer_repr", "_")

        engine_level = getattr(record, "engine_level", 0)
        engine_id = getattr(record, "engine_id", 0)
        prefix = (
            f"{engine_level}:{engine_id} {total_turn}.{racer_repr}.{turn_log_count}"
        )

        message = record.getMessage()
        return f"[{COLOR['prefix']}]{prefix}[/{COLOR['prefix']}]  {message}"


class GameLogHighlighter(Highlighter):
    @override
    def highlight(self, text: Text) -> None:
        # Movement-related words
        text.highlight_regex(r"\bMove\b", COLOR["move"])
        text.highlight_regex(r"\bMoving\b", COLOR["move"])
        text.highlight_regex(r"\bPushing\b", COLOR["warp"])
        text.highlight_regex(r"\bMainMove\b", COLOR["main_move"])
        text.highlight_regex(r"\bWarp\b", COLOR["warp"])
        text.highlight_regex(r"\bBOARD\b", COLOR["board"])
        text.highlight_regex(r"\bDice Roll\b", COLOR["dice_roll"])

        # Abilities and racer names
        text.highlight_regex(ABILITY_PATTERN, COLOR["ability"])
        text.highlight_regex(MODIFIER_PATTERN, COLOR["modifier"])
        text.highlight_regex(RACER_PATTERN, COLOR["racer"])

        # Emphasis and VP
        text.highlight_regex(r"!!!", COLOR["warning"])
        text.highlight_regex(r"\bVP:\b", "bold yellow")
        text.highlight_regex(r"\b\+1 VP\b", "bold green")
        text.highlight_regex(r"\b-1 VP\b", "bold red")


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = RichHandler(
        markup=True,
        show_path=False,
        show_time=False,
        highlighter=GameLogHighlighter(),
    )
    handler.setFormatter(RichMarkupFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
