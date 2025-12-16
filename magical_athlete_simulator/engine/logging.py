import logging
import re
from typing import TYPE_CHECKING, get_args, override

from rich.logging import RichHandler

from magical_athlete_simulator.core.types import AbilityName, RacerName

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import LogContext
    from magical_athlete_simulator.engine.game_engine import GameEngine

RACER_NAMES = set(get_args(RacerName))
ABILITY_NAMES = set(get_args(AbilityName))


# Precompiled regex patterns for highlighting
ABILITY_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, ABILITY_NAMES))})\b")
RACER_PATTERN = re.compile(rf"(?<!\[)\b({'|'.join(map(re.escape, RACER_NAMES))})\b")


# Simple color theme for Rich
COLOR = {
    "move": "bold green",
    "warp": "bold magenta",
    "warning": "bold red",
    "ability": "bold blue",
    "racer": "yellow",
    "prefix": "dim",
    "level": "bold",
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
        styled = message

        # Movement
        styled = re.sub(r"\bMove\b", f"[{COLOR['move']}]Move[/{COLOR['move']}]", styled)
        styled = re.sub(
            r"\bMoving\b", f"[{COLOR['move']}]Moving[/{COLOR['move']}]", styled
        )
        styled = re.sub(
            r"\bPushing\b", f"[{COLOR['move']}]Pushing[/{COLOR['move']}]", styled
        )
        styled = re.sub(
            r"\bMainMove\b", f"[{COLOR['move']}]MainMove[/{COLOR['move']}]", styled
        )
        styled = re.sub(r"\bWarp\b", f"[{COLOR['warp']}]Warp[/{COLOR['warp']}]", styled)

        # Abilities
        styled = ABILITY_PATTERN.sub(
            rf"[{COLOR['ability']}]\1[/{COLOR['ability']}]", styled
        )

        # !!! and VP
        styled = re.sub(r"!!!", f"[{COLOR['warning']}]!!![/{COLOR['warning']}]", styled)
        styled = re.sub(r"\bVP:\b", "[bold yellow]VP:[/]", styled)
        styled = re.sub(r"\b\+1 VP\b", "[bold green]+1 VP[/]", styled)
        styled = re.sub(r"\b-1 VP\b", "[bold red]-1 VP[/]", styled)

        styled = RACER_PATTERN.sub(rf"[{COLOR['racer']}]\1[/{COLOR['racer']}]", styled)

        if record.levelno >= logging.WARNING:
            styled = f"[{COLOR['warning']}]{styled}[/{COLOR['warning']}]"

        return f"[{COLOR['prefix']}]{prefix}[/{COLOR['prefix']}]  {styled}"


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = RichHandler(markup=True, show_path=False, show_time=False)
    handler.setFormatter(RichMarkupFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
