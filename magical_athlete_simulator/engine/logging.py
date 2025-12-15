from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, get_args, override

from magical_athlete_simulator.core.types import AbilityName, RacerName

if TYPE_CHECKING:
    from magical_athlete_simulator.core.protocols import LogContext
    from magical_athlete_simulator.engine.game_engine import GameEngine

RACER_NAMES = set(get_args(RacerName))
ABILITY_NAMES = set(get_args(AbilityName))


# Precompiled regex patterns for highlighting
ABILITY_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, ABILITY_NAMES))})\b")
RACER_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, RACER_NAMES))})\b")


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
        logctx.inc_log_count()
        return True


@dataclass
class ContextLogRecord(logging.LogRecord):
    total_turn: int
    turn_log_count: int
    racer_repr: str


class RichMarkupFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        r = record  # keep runtime object
        cr = cast("ContextLogRecord", r)
        prefix = f"{cr.total_turn}.{cr.racer_repr}.{cr.turn_log_count}"

        message = record.getMessage()

        # --- movement highlighting (see next section) ---
        styled = message
        # Highlight all movement-related words
        styled = re.sub(r"\bMove\b", f"[{COLOR['move']}]Move[/{COLOR['move']}]", styled)
        styled = re.sub(
            r"\bMoving\b",
            f"[{COLOR['move']}]Moving[/{COLOR['move']}]",
            styled,
        )
        styled = re.sub(
            r"\bPushing\b",
            f"[{COLOR['move']}]Pushing[/{COLOR['move']}]",
            styled,
        )
        styled = re.sub(
            r"\bMainMove\b",
            f"[{COLOR['move']}]MainMove[/{COLOR['move']}]",
            styled,
        )
        styled = re.sub(r"\bWarp\b", f"[{COLOR['warp']}]Warp[/{COLOR['warp']}]", styled)

        # Abilities and racer names
        styled = ABILITY_PATTERN.sub(
            rf"[{COLOR['ability']}]\1[/{COLOR['ability']}]",
            styled,
        )
        styled = RACER_PATTERN.sub(rf"[{COLOR['racer']}]\1[/{COLOR['racer']}]", styled)

        # Emphasis for "!!!"
        styled = re.sub(r"!!!", f"[{COLOR['warning']}]!!![/{COLOR['warning']}]", styled)

        # VP
        styled = re.sub(r"\bVP:\b", "[bold yellow]VP:[/]", styled)
        styled = re.sub(r"\b\+1 VP\b", "[bold green]+1 VP[/]", styled)
        styled = re.sub(r"\b-1 VP\b", "[bold red]-1 VP[/]", styled)

        # If warning or higher, tint whole message
        if record.levelno >= logging.WARNING:
            styled = f"[{COLOR['warning']}]{styled}[/{COLOR['warning']}]"

        # Final string: prefix + message (no level, RichHandler already shows it)
        return f"[{COLOR['prefix']}]{prefix}[/{COLOR['prefix']}]  {styled}"
