import copy
import heapq
import logging
import random
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    ClassVar,
    Literal,
    assert_never,
    cast,
    final,
    get_args,
    override,
)

from rich.logging import RichHandler

RacerName = Literal[
    "Centaur",
    "HugeBaby",
    "Scoocher",
    "Banana",
    "Copycat",
    "Gunk",
    "PartyAnimal",
    "Magician",
]
AbilityName = Literal[
    "Trample",
    "HugeBabyPush",
    "BananaTrip",
    "ScoochStep",
    "CopyLead",
    "Slime",
    "PartyPull",
    "PartyBoost",
    "MagicalReroll",
]

ModifierName = Literal["PartySelfBoost"]


# ------------------------------
# 1. Logging & Context
# ------------------------------


# Derived name sets from Literals for dynamic regex creation
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

logger = logging.getLogger("magical_athlete")


@dataclass(slots=True)
class LogContext:
    """Per-game logging state. No longer global."""

    total_turn: int = 0
    turn_log_count: int = 0
    current_racer_repr: str = "_"

    def new_round(self):
        self.total_turn += 1

    def start_turn_log(self, racer_repr: str):
        self.turn_log_count = 0
        self.current_racer_repr = racer_repr

    def inc_log_count(self):
        self.turn_log_count += 1


class ContextFilter(logging.Filter):
    """Inject per-engine runtime context into every log record."""

    def __init__(self, engine: "GameEngine", name: str = "") -> None:
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
    totalturn: int
    turnlogcount: int
    racerrepr: str


class RichMarkupFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        r = record  # keep runtime object
        cr = cast("ContextLogRecord", r)
        prefix = f"{cr.totalturn}.{cr.racerrepr}.{cr.turnlogcount}"

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


# --- Final Logger Setup ---


@dataclass(frozen=True)
class TurnOutcome:
    """Result of simulating exactly one turn for a specific racer."""

    vp_delta: list[int]  # per racer: final_vp - start_vp
    position: list[int]  # per racer final positions
    tripped: list[bool]  # per racer tripped flags at end of turn
    eliminated: list[bool]  # per racer eliminated flags at end of turn
    start_position: list[int]  # per racer start positions


# ------------------------------
# 1b. AI Core & Decision Context
# ------------------------------


class DecisionReason(Enum):
    """Specific reasons an Agent is being asked to make a decision."""

    MAGICAL_REROLL = auto()
    COPY_LEAD_TARGET = auto()


@dataclass
class DecisionContext:
    """Base context containing the minimal state needed for a decision."""

    game_state: "GameState"
    source_racer_idx: int
    reason: DecisionReason


@dataclass
class BooleanDecision(DecisionContext):
    """A Yes/No decision (e.g., should I reroll?)."""


@dataclass
class SelectionDecision(DecisionContext):
    """A generic selection from a list of options."""

    options: list["RacerState"]


class Agent(ABC):
    """Base interface for decision making entities."""

    @abstractmethod
    def make_boolean_decision(self, ctx: BooleanDecision) -> bool:
        pass

    @abstractmethod
    def make_selection_decision(self, ctx: SelectionDecision) -> int:
        """Return the index of the selected option."""


# ------------------------------
# 2. Modifiers
# ------------------------------

# --- Base Definitions ---


@dataclass
class Modifier(ABC):
    """Base class for all persistent effects."""

    owner_idx: int | None
    name: ClassVar[AbilityName | str]

    @property
    def display_name(self) -> str:  # instance-level, can be dynamic
        return self.name

    # Equality check for safe add/remove
    @override
    def __eq__(self, other: object):
        if not isinstance(other, Modifier):
            return NotImplemented
        return self.name == other.name and self.owner_idx == other.owner_idx

    @override
    def __hash__(self):
        return hash((self.name, self.owner_idx))


class RollModificationMixin(ABC):
    """Mixin for modifiers that alter dice rolls."""

    @abstractmethod
    def modify_roll(
        self,
        query: "MoveDistanceQuery",
        owner_idx: int | None,
        engine: "GameEngine",
    ) -> None:
        pass


# --- Concrete Implementations ---


class ApproachHookMixin(ABC):
    """Allows a modifier to redirect incoming racers (e.g., Huge Baby blocking)."""

    @abstractmethod
    def on_approach(self, target: int, mover_idx: int, engine: "GameEngine") -> int:
        pass


class LandingHookMixin(ABC):
    """Allows a modifier to react when a racer stops on the tile (e.g., Trip, VP)."""

    @abstractmethod
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: "GameEngine",
    ) -> None:
        pass


@dataclass(eq=False)
class SpaceModifier(Modifier, ABC):
    """Base for board features. Can mix in Approach or Landing hooks."""

    priority: int = 5


@dataclass(eq=False)
class RacerModifier(Modifier, ABC):
    """Attached to Racers (e.g. SlimeDebuff)."""


@dataclass
class MoveDeltaTile(SpaceModifier, LandingHookMixin):
    """On landing, queue a move of +delta (forward) or -delta (backward)."""

    delta: int = 0
    priority: int = 5

    @property
    @override
    def display_name(self) -> str:
        sign = "+" if self.delta >= 0 else "-"
        return f"MoveDelta({sign}{self.delta})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: "GameEngine",
    ) -> None:
        if self.delta == 0:
            return
        racer: RacerState = engine.get_racer(
            racer_idx,
        )  # uses existing GameEngine API.[file:1]
        logger.info(f"{self.name}: Queuing {self.delta} move for {racer.repr}")
        # New move is a separate event, not part of the original main move.[file:1]
        engine.push_move(racer_idx, self.delta, source=self.name, phase=Phase.BOARD)


@dataclass
class TripTile(SpaceModifier, LandingHookMixin):
    """On landing, trip the racer (they skip their next main move)."""

    name: ClassVar[AbilityName | str] = "TripTile"
    priority: int = 5

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: "GameEngine",
    ) -> None:
        racer = engine.get_racer(racer_idx)
        if racer.tripped:
            return
        racer.tripped = True
        logger.info(f"{self.name}: {racer.repr} is now Tripped.")


@dataclass
class VictoryPointTile(SpaceModifier, LandingHookMixin):
    """On landing, grant +1 VP (or a configured amount)."""

    amount: int = 1
    priority: int = 5

    @property
    @override
    def display_name(self) -> str:
        return f"VP(+{self.amount})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: "GameEngine",
    ) -> None:
        racer = engine.get_racer(racer_idx)
        racer.victory_points += self.amount
        logger.info(
            f"{self.name}: {racer.repr} gains +{self.amount} VP ",
            f"(now {racer.victory_points}).",
        )


@dataclass(slots=True)
class Board:
    """Manages track topology and spatial modifiers (static and dynamic)."""

    length: int
    static_features: dict[int, list["SpaceModifier"]]
    dynamic_modifiers: defaultdict[int, set["SpaceModifier"]] = field(
        init=False,
        default_factory=lambda: defaultdict(set),
    )

    @property
    def finish_space(self) -> int:
        return self.length

    def register_modifier(self, tile: int, modifier: "SpaceModifier") -> None:
        modifiers = self.dynamic_modifiers[tile]
        if modifier not in modifiers:
            modifiers.add(modifier)
            logger.info(
                f"BOARD: Registered {modifier.name} (owner={modifier.owner_idx}) at tile {tile}",
            )

    def unregister_modifier(self, tile: int, modifier: "SpaceModifier") -> None:
        modifiers = self.dynamic_modifiers.get(tile)
        if not modifiers or modifier not in modifiers:
            logger.warning(
                f"BOARD: Failed to unregister {modifier.name} from {tile} - not found.",
            )
            return

        modifiers.remove(modifier)
        logger.info(
            f"BOARD: Unregistered {modifier.name} (owner={modifier.owner_idx}) from tile {tile}",
        )

        if not modifiers:
            _ = self.dynamic_modifiers.pop(tile, None)

    def get_modifiers_at(self, tile: int) -> list["SpaceModifier"]:
        static = self.static_features.get(tile, ())
        dynamic = self.dynamic_modifiers.get(tile, ())
        return sorted((*static, *dynamic), key=lambda m: m.priority)

    def resolve_position(
        self,
        target: int,
        mover_idx: int,
        engine: "GameEngine",
    ) -> int:
        visited: set[int] = set()
        current = target

        while current not in visited:
            visited.add(current)
            new_target = current

            for mod in (
                mod
                for mod in self.get_modifiers_at(current)
                if isinstance(mod, ApproachHookMixin)
            ):
                redirected = mod.on_approach(current, mover_idx, engine)
                if redirected != current:
                    logger.debug(
                        "%s redirected %s from %s -> %s",
                        mod.name,
                        mover_idx,
                        current,
                        redirected,
                    )
                    new_target = redirected
                    break

            if new_target == current:
                return current

            current = new_target

        logger.warning("resolve_position loop detected, settling on %s", current)
        return current

    def trigger_on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: "GameEngine",
    ) -> None:
        for mod in (
            mod
            for mod in self.get_modifiers_at(tile)
            if isinstance(mod, LandingHookMixin)
        ):
            current_pos = engine.get_racer_pos(racer_idx)
            if current_pos != tile:
                break
            mod.on_land(tile, racer_idx, phase, engine)

    def dump_state(self):
        """Log the location of all dynamic modifiers currently on the board.

        Useful for debugging test failures.
        """
        logger.info("=== BOARD STATE DUMP ===")
        if not self.dynamic_modifiers:
            logger.info("  (Board is empty of dynamic modifiers)")
            return

        # Sort by tile index for readability
        active_tiles = sorted(self.dynamic_modifiers.keys())
        for tile in active_tiles:
            mods = self.dynamic_modifiers[tile]
            if mods:
                # Format each modifier as "Name(owner=ID)"
                mod_strs = [f"{m.name}(owner={m.owner_idx})" for m in mods]
                logger.info(f"  Tile {tile:02d}: {', '.join(mod_strs)}")
        logger.info("========================")


def build_action_lane_board() -> Board:
    """Build example board using all three static tile types.

    - Tile 3: Move forward 2.
    - Tile 6: Move back 2.
    - Tile 9: Trip.
    - Tile 12: +1 VP.
    """
    return Board(
        length=30,
        static_features={
            3: [MoveDeltaTile(None, 2)],
            6: [MoveDeltaTile(None, -2)],
            9: [TripTile(None)],
            12: [VictoryPointTile(None, 1)],
        },
    )


BoardFactory = Callable[[], Board]

BOARD_DEFINITIONS: dict[str, BoardFactory] = {
    "standard": lambda: Board(
        length=30,
        static_features={},
    ),
    "wild_wilds": build_action_lane_board,
}


# ------------------------------
# 3. Game State
# ------------------------------


@dataclass(slots=True)
class RollState:
    serial_id: int = 0
    base_value: int = 0
    final_value: int = 0


@dataclass(slots=True)
class RacerState:
    idx: int
    name: RacerName
    position: int = 0
    victory_points: int = 0
    tripped: bool = False
    reroll_count: int = 0
    finish_position: int | None = None
    eliminated: bool = False

    modifiers: list[RacerModifier] = field(default_factory=list)
    active_abilities: dict[AbilityName, "Ability"] = field(default_factory=dict)

    @property
    def repr(self) -> str:
        return f"{self.idx}:{self.name}"

    @property
    def abilities(self) -> set[AbilityName]:
        """Derive from active instances."""
        return set(self.active_abilities.keys())

    @property
    def finished(self) -> bool:
        return self.finish_position is not None

    @property
    def active(self) -> bool:
        return not self.finished and not self.eliminated


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    roll_state: RollState = field(default_factory=RollState)
    board: Board = field(default_factory=BOARD_DEFINITIONS["standard"])

    def get_state_hash(self) -> int:
        """Hash entire game state including all racer data."""
        racer_data = tuple(
            (
                r.idx,
                r.position,
                r.tripped,
                r.finish_position,
                r.eliminated,
                r.victory_points,
                frozenset(r.abilities),
                frozenset(m.name for m in r.modifiers),
            )
            for r in self.racers
        )

        board_data = frozenset(
            (tile, frozenset(m.name for m in mods))
            for tile, mods in self.board.dynamic_modifiers.items()
        )

        return hash((racer_data, board_data))


# ------------------------------
# 4. Events
# ------------------------------


class GameEvent:
    pass


@final
class Phase:
    SYSTEM = 0
    PRE_MAIN = 10
    ROLL_DICE = 15
    ROLL_WINDOW = 18  # Hook for re-rolls
    MAIN_ACT = 20
    REACTION = 25
    MOVE_EXEC = 30
    BOARD = 40


@dataclass(frozen=True)
class RacerFinishedEvent(GameEvent):
    racer_idx: int
    finishing_position: int  # 1st, 2nd, etc.


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class PerformRollEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollModificationWindowEvent(GameEvent):
    """
    Fired after a roll is calculated but before it is finalized.
    Listeners can inspect `engine.state.roll_state` and call `engine.trigger_reroll()`.
    """

    racer_idx: int
    current_roll_val: int
    roll_serial: int


@dataclass(frozen=True)
class ResolveMainMoveEvent(GameEvent):
    racer_idx: int
    roll_serial: int


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    victim_idx: int
    tile_idx: int


@dataclass(frozen=True)
class MoveCmdEvent(GameEvent):
    racer_idx: int
    distance: int
    source: str
    phase: int


@dataclass(frozen=True)
class WarpCmdEvent(GameEvent):
    racer_idx: int
    target_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PreMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    distance: int
    source: str
    phase: int


@dataclass(frozen=True)
class PreWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    target_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int | None
    ability_name: AbilityName | ModifierName | str
    # Human-readable context for logs
    log_context: str


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)
    modifier_sources: list[tuple[str, int]] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_amount + sum(self.modifiers))


@dataclass(order=True)
class ScheduledEvent:
    phase: int
    priority: int
    serial: int
    event: GameEvent = field(compare=False)


# ------------------------------
# 6b. AI Implementation
# ------------------------------


def ai_should_reroll(ctx: BooleanDecision, board: "Board") -> bool:
    """Deterministic logic for MagicalReroll.

    Returns True (Reroll) if:
    1. The roll is very low (<= 2).
    2. The landing spot contains a 'Bad' modifier (Trip or negative MoveDelta).
    """
    state = ctx.game_state
    me = state.racers[ctx.source_racer_idx]
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


class SmartAgent(Agent):
    """A concrete agent that uses deterministic functions to make decisions."""

    def __init__(self, board: Board):
        # We MUST have the board to make smart lookahead decisions
        self.board: Board = board

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


# ------------------------------
# 5. Engine Core
# ------------------------------


AbilityCallback = Callable[[GameEvent, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    queue: list[ScheduledEvent] = field(default_factory=list)
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)

    logging_enabled: bool = True
    log_context: LogContext = field(default_factory=LogContext)

    serial: int = 0
    race_over: bool = False
    history: set[tuple[int, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Assigns starting abilities to all racers and fires on_gain hooks."""
        # Setup logging with this engine instance
        if self.logging_enabled:
            rich_handler = RichHandler(markup=True, show_path=False, show_time=False)
            rich_handler.setFormatter(RichMarkupFormatter())
            rich_handler.addFilter(ContextFilter(self))
            logger.handlers.clear()
            logger.addHandler(rich_handler)
            logger.propagate = False

        # Assign starting abilities
        for racer in self.state.racers:
            initial = RACER_ABILITIES.get(racer.name, set())
            self.update_racer_abilities(racer.idx, initial)

        # Rebuild subscribers
        self._rebuild_subscribers()

        for racer in self.state.racers:
            _ = self.agents.setdefault(racer.idx, SmartAgent(self.state.board))

    def _rebuild_subscribers(self):
        """Rebuild event subscriptions from each racer's active_abilities."""
        self.subscribers.clear()
        for racer in self.state.racers:
            for ability in racer.active_abilities.values():
                ability.register(self, racer.idx)

    def get_agent(self, racer_idx: int) -> Agent:
        return self.agents[racer_idx]

    def add_racer_modifier(self, target_idx: int, modifier: RacerModifier):
        racer = self.get_racer(target_idx)
        if modifier not in racer.modifiers:
            racer.modifiers.append(modifier)
            if self.logging_enabled:
                logger.info(f"ENGINE: Added {modifier.name} to {racer.repr}")

    def remove_racer_modifier(self, target_idx: int, modifier: RacerModifier):
        racer = self.get_racer(target_idx)
        if modifier in racer.modifiers:
            racer.modifiers.remove(modifier)
            if self.logging_enabled:
                logger.info(f"ENGINE: Removed {modifier.name} from {racer.repr}")

    def subscribe(
        self,
        event_type: type[GameEvent],
        callback: AbilityCallback,
        owner_idx: int,
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        racer = self.get_racer(racer_idx)
        current_instances = racer.active_abilities
        old_names = set(current_instances.keys())

        removed = old_names - new_abilities
        added = new_abilities - old_names

        # 1. Handle Removed
        for name in removed:
            instance = current_instances.pop(name)

            if isinstance(instance, LifecycleManagedMixin):
                instance.__class__.on_loss(self, racer_idx)

            # Selective Unsubscribe
            for event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub
                    for sub in self.subscribers[event_type]
                    if not (
                        sub.owner_idx == racer_idx
                        and getattr(sub.callback, "__self__", None) == instance
                    )
                ]

        # 2. Handle Added
        for name in added:
            ability_cls = ABILITY_CLASSES.get(name)
            if ability_cls:
                instance = ability_cls()

                instance.register(self, racer_idx)
                current_instances[name] = instance

                if isinstance(instance, LifecycleManagedMixin):
                    instance.__class__.on_gain(self, racer_idx)

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def get_racer_pos(self, idx: int) -> int:
        return self.state.racers[idx].position

    # --- Action Queuing ---

    def push_event(self, event: GameEvent, *, phase: int):
        self.serial += 1
        sched = ScheduledEvent(phase, 0, self.serial, event)
        heapq.heappush(self.queue, sched)

        # --- In GameEngine Class ---

    def push_move(self, racer_idx: int, distance: int, source: str, phase: int):
        if distance == 0:
            return
        # Pass phase into the event data
        self.push_event(MoveCmdEvent(racer_idx, distance, source, phase), phase=phase)

    def push_warp(self, racer_idx: int, target: int, source: str, phase: int):
        if self.get_racer(racer_idx).position == target:
            return
        # Pass phase into the event data
        self.push_event(WarpCmdEvent(racer_idx, target, source, phase), phase=phase)

    def emit_ability_trigger(
        self,
        source_idx: int | None,
        ability: AbilityName | ModifierName | str,
        log_context: str,
    ):
        self.push_event(
            AbilityTriggeredEvent(source_idx, ability, log_context),
            phase=Phase.REACTION,
        )

    def trigger_reroll(self, source_idx: int, reason: str):
        """Cancels the current roll resolution and schedules a new roll immediately."""
        logger.info(
            f"!!! RE-ROLL TRIGGERED by {self.get_racer(source_idx).name} ({reason}) !!!",
        )
        # Increment serial to kill any pending ResolveMainMove events
        self.state.roll_state.serial_id += 1

        # CHANGED: We schedule the new roll at Phase.REACTION + 1.
        # This guarantees that any AbilityTriggeredEvents (Phase 25) caused by the
        # act of triggering the reroll (e.g. Scoocher moving) are processed
        # BEFORE the dice are rolled again.
        self.push_event(
            PerformRollEvent(self.state.current_racer_idx),
            phase=Phase.REACTION + 1,
        )

    # --- Event Loop ---

    def publish_to_subscribers(self, event: GameEvent):
        if type(event) not in self.subscribers:
            return
        subs = self.subscribers[type(event)]
        curr = self.state.current_racer_idx
        count = len(self.state.racers)
        # Ordered iteration: Start from current player, go clockwise
        ordered_subs = sorted(subs, key=lambda s: (s.owner_idx - curr) % count)

        for sub in ordered_subs:
            # If a re-roll happened mid-loop during a Window event, we might want to abort
            # further listeners for this specific serial, but simplified here:
            sub.callback(event, sub.owner_idx, self)

    def run_race(self):
        while not self.race_over:
            self.run_turn()
            self.advance_turn()

    def run_turn(self):
        self.history.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        racer.reroll_count = 0

        self.log_context.start_turn_log(racer.repr)
        if self.logging_enabled:
            logger.info(f"=== START TURN: {racer.repr} ===")

        if racer.tripped:
            if self.logging_enabled:
                logger.info(f"{racer.repr} recovers from Trip.")
            racer.tripped = False
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
        else:
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
            self.push_event(PerformRollEvent(cr), phase=Phase.ROLL_DICE)

        while self.queue and not self.race_over:
            sched = heapq.heappop(self.queue)

            # Loop Detection
            state_hash = self.state.get_state_hash()
            event_sig = hash(repr(sched.event))
            if (state_hash, event_sig) in self.history:
                logger.warning(f"Loop detected for {sched.event}. Discarding.")
                continue
            self.history.add((state_hash, event_sig))

            self.handle_event(sched.event)

    def handle_event(self, event: GameEvent):
        match event:
            case (
                TurnStartEvent()
                | PassingEvent()
                | AbilityTriggeredEvent()
                | RollModificationWindowEvent()
            ):
                self.publish_to_subscribers(event)

            case MoveCmdEvent():
                self._handle_move_cmd(event)

            case WarpCmdEvent():
                self._handle_warp_cmd(event)

            case PerformRollEvent():
                self._handle_perform_roll(event)

            case ResolveMainMoveEvent():
                self._resolve_main_move(event)

            case _:
                pass

    def _handle_perform_roll(self, event: PerformRollEvent) -> None:
        self.state.roll_state.serial_id += 1
        current_serial = self.state.roll_state.serial_id

        base = self.rng.randint(1, 6)
        query = MoveDistanceQuery(event.racer_idx, base)

        # Apply ALL modifiers attached to this racer
        for mod in self.get_racer(event.racer_idx).modifiers:
            if isinstance(mod, RollModificationMixin):
                mod.modify_roll(query, mod.owner_idx, self)

        final = query.final_value
        self.state.roll_state.base_value = base
        self.state.roll_state.final_value = final

        # Logging with sources
        if query.modifier_sources:
            parts = [f"{name}:{delta:+d}" for (name, delta) in query.modifier_sources]
            mods_str = ", ".join(parts)
            total_delta = sum(delta for _, delta in query.modifier_sources)
            logger.info(
                f"Dice Roll: {base} (Mods: {total_delta} [{mods_str}]) -> Result: {final}",
            )
        else:
            logger.info(f"Dice Roll: {base} (Mods: 0) -> Result: {final}")

        # 3. Fire the 'Window' event. Listeners can call trigger_reroll() here.
        self.push_event(
            RollModificationWindowEvent(event.racer_idx, final, current_serial),
            phase=Phase.ROLL_WINDOW,
        )

        # 4. Schedule the resolution. If trigger_reroll() was called in step 3,
        # serial_id will increment, and this event will be ignored in _resolve_main_move.
        self.push_event(
            ResolveMainMoveEvent(event.racer_idx, current_serial),
            phase=Phase.MAIN_ACT,
        )

    def _resolve_main_move(self, event: ResolveMainMoveEvent):
        # If serial doesn't match, it means a re-roll happened.
        if event.roll_serial != self.state.roll_state.serial_id:
            logger.debug("Ignoring stale roll resolution (Re-roll occurred).")
            return

        dist = self.state.roll_state.final_value
        if dist > 0:
            self.push_move(event.racer_idx, dist, "MainMove", phase=Phase.MOVE_EXEC)

    def _handle_move_cmd(self, evt: MoveCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        # Moving 0 is not moving at all
        if evt.distance == 0:
            return

        start = racer.position
        distance = evt.distance

        # 1. Departure hook
        self.publish_to_subscribers(
            PreMoveEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                distance=distance,
                source=evt.source,
                phase=evt.phase,
            ),
        )

        # 2. Resolve spatial modifiers (Huge Baby etc.)
        intended = start + distance
        end = self.state.board.resolve_position(
            intended,
            evt.racer_idx,
            self,
        )  # [file:1]

        # If you get fully blocked back to your start, treat as “no movement”
        if end == start:
            return

        logger.info(f"Move: {racer.repr} {start}->{end} ({evt.source})")  # [file:1]

        # 3. Passing events (unchanged from your current logic)
        if distance > 0:
            for tile in range(start + 1, min(end, self.state.board.length)):
                if tile < end:
                    victims = [
                        r
                        for r in self.state.racers
                        if r.position == tile and r.idx != racer.idx and not r.finished
                    ]
                    for v in victims:
                        self.push_event(
                            PassingEvent(racer.idx, v.idx, tile),
                            phase=Phase.MOVE_EXEC,
                        )  # [file:1]

        # 4. Commit position
        racer.position = end

        # Finish check as in your current engine
        if self._check_finish(racer):  # may log finish + mark race_over, etc. [file:1]
            return

        # 5. Board “on land” hooks (Trip, VP, MoveDelta, etc.)
        self.state.board.trigger_on_land(end, racer.idx, evt.phase, self)  # [file:1]

        # 6. Arrival hook
        self.publish_to_subscribers(
            PostMoveEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                end_tile=end,
                source=evt.source,
                phase=evt.phase,
            ),
        )

    def _handle_warp_cmd(self, evt: WarpCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        start = racer.position

        # Warping to the same tile is not movement
        if start == evt.target_tile:
            return

        # 1. Departure hook
        self.publish_to_subscribers(
            PreWarpEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                target_tile=evt.target_tile,
                source=evt.source,
                phase=evt.phase,
            ),
        )

        # 2. Resolve spatial modifiers on the target
        resolved = self.state.board.resolve_position(
            evt.target_tile,
            evt.racer_idx,
            self,
        )  # [file:1]

        if resolved == start:
            return

        logger.info(f"Warp: {racer.repr} -> {resolved} ({evt.source})")  # [file:1]
        racer.position = resolved

        if self._check_finish(racer):
            return

        # 3. Board hooks on landing
        self.state.board.trigger_on_land(
            resolved,
            racer.idx,
            evt.phase,
            self,
        )  # [file:1]

        # 4. Arrival hook
        self.publish_to_subscribers(
            PostWarpEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                end_tile=resolved,
                source=evt.source,
                phase=evt.phase,
            ),
        )

    def _check_finish(self, racer: RacerState) -> bool:
        if racer.finished:
            return False

        if racer.position >= self.state.board.length:
            # Count how many finished before this one
            finishing_position = sum(1 for r in self.state.racers if r.finished) + 1
            racer.finish_position = finishing_position

            if self.logging_enabled:
                logger.info(f"!!! {racer.repr} FINISHED rank {finishing_position} !!!")

            # Emit finish event
            self.push_event(
                RacerFinishedEvent(racer.idx, finishing_position),
                phase=Phase.REACTION,
            )

            # Strip abilities
            self.update_racer_abilities(racer.idx, set())

            # Check if race is over (2 finishers)
            finished_count = sum(1 for r in self.state.racers if r.finished)
            if finished_count >= 2:
                self.race_over = True
                # Mark remaining as eliminated
                for r in self.state.racers:
                    if not r.finished:
                        r.eliminated = True
                self.queue.clear()
                self._log_final_standings()

            return True

        return False

    def _log_final_standings(self):
        if not self.logging_enabled:
            return
        logger.info("=== FINAL STANDINGS ===")
        for racer in sorted(
            self.state.racers,
            key=lambda r: r.finish_position if r.finish_position else 999,
        ):
            if racer.finish_position:
                status = f"Rank {racer.finish_position}"
            else:
                status = "Eliminated"
            logger.info(
                f"Result: {racer.repr} pos={racer.position} vp={racer.victory_points} {status}",
            )

    def advance_turn(self):
        if self.race_over:
            return
        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n
        while not self.state.racers[next_idx].active:  # Skip finished/eliminated
            next_idx = (next_idx + 1) % n
            if next_idx == curr:
                break
        if next_idx < curr:
            self.log_context.new_round()
        self.state.current_racer_idx = next_idx

    # simulation
    def simulate_turn_for(self, racer_idx: int) -> TurnOutcome:
        """Public helper: deep-copy current state into a SandboxEngine
        and simulate one turn for `racer_idx`.
        """
        sandbox = SandboxEngine.from_engine(self)
        return sandbox.run_turn_for(racer_idx)


# ------------------------------
# 6. Abilities
# ------------------------------


class Ability(ABC):
    """Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    name: ClassVar[AbilityName]
    triggers: tuple[type[GameEvent], ...] = ()

    def register(self, engine: "GameEngine", owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        """The internal handler that wraps the user logic.
        It checks liveness, executes logic, and automatically emits the trigger event.
        """
        # 1. Dead racers tell no tales (usually)
        if engine.state.racers[owner_idx].finished:
            return

        # 2. Execute
        did_trigger = self.execute(event, owner_idx, engine)

        # 3. Automatic Emission
        if did_trigger:
            ctx = f"Reacting to {event.__class__.__name__}"
            engine.emit_ability_trigger(owner_idx, self.name, ctx)

    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        """Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        _ = event, owner_idx, engine
        return False


class LifecycleManagedMixin(ABC):
    @staticmethod
    @abstractmethod
    def on_gain(engine: "GameEngine", owner_idx: int) -> None:
        pass

    @staticmethod
    @abstractmethod
    def on_loss(engine: "GameEngine", owner_idx: int) -> None:
        pass


# --- Implementations ---


class AbilityTrample(Ability):
    name: ClassVar[AbilityName] = "Trample"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Logic: Only trigger if *I* am the mover
        if event.mover_idx != owner_idx:
            return False

        victim = engine.get_racer(event.victim_idx)
        if victim.finished:
            return False

        logger.info(f"{self.name}: Centaur passed {victim.repr}. Queuing -2 move.")
        engine.push_move(victim.idx, -2, self.name, phase=Phase.REACTION)
        return True


class AbilityBananaTrip(Ability):
    name: ClassVar[AbilityName] = "BananaTrip"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        if not isinstance(event, PassingEvent):
            return False

        # Logic: Only trigger if *I* am the victim
        if event.victim_idx != owner_idx:
            return False

        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return False

        logger.info(f"{self.name}: {mover.repr} passed Banana! Tripping mover.")
        mover.tripped = True
        return True


@dataclass(eq=False)
class HugeBabyModifier(SpaceModifier, ApproachHookMixin):
    """The physical manifestation of the Huge Baby on the board.
    Blocks others from entering the tile by redirecting them backward.
    """

    name: ClassVar[AbilityName | str] = "HugeBabyBlocker"
    priority: int = 10

    @override
    def on_approach(self, target: int, mover_idx: int, engine: "GameEngine") -> int:
        # Prevent others from entering the tile
        if target == 0:
            return target

        logger.info(f"Huge Baby already occupies {target}!")
        # Redirect to the previous tile
        return max(0, target - 1)


class HugeBabyPush(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "HugeBabyPush"
    triggers: tuple[type[GameEvent], ...] = (
        PreMoveEvent,
        PreWarpEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    def _get_modifier(self, owner_idx: int) -> HugeBabyModifier:
        """Helper to create the modifier instance for this specific owner."""
        return HugeBabyModifier(owner_idx=owner_idx)

    # --- on_gain and on_loss remain unchanged ---
    @override
    @staticmethod
    def on_gain(engine: "GameEngine", owner_idx: int):
        racer = engine.get_racer(owner_idx)
        if racer.position > 0:
            mod = HugeBabyModifier(owner_idx=owner_idx)
            engine.state.board.register_modifier(racer.position, mod)

    @override
    @staticmethod
    def on_loss(engine: "GameEngine", owner_idx: int):
        racer = engine.get_racer(owner_idx)
        mod = HugeBabyModifier(owner_idx=owner_idx)
        engine.state.board.unregister_modifier(racer.position, mod)

    # --- REWRITTEN: The core logic is now split into clear phases ---
    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        # --- DEPARTURE LOGIC: Triggered BEFORE the move happens ---
        if isinstance(event, (PreMoveEvent, PreWarpEvent)):
            if event.racer_idx != owner_idx:
                return False

            start_tile = event.start_tile
            # No blocker to clean up at the start line
            if start_tile == 0:
                return False

            # Clean up the blocker from the tile we are leaving
            mod_to_remove = self._get_modifier(owner_idx)
            engine.state.board.unregister_modifier(start_tile, mod_to_remove)

            # This is a cleanup action, so it should not trigger other abilities
            return False

        # --- ARRIVAL LOGIC: Triggered AFTER the move is complete ---
        if isinstance(event, (PostMoveEvent, PostWarpEvent)):
            if event.racer_idx != owner_idx:
                return False

            end_tile = event.end_tile
            # Huge Baby does not place a blocker at the start line
            if end_tile == 0:
                return False

            # 1. Place a new blocker at the destination
            mod_to_add = self._get_modifier(owner_idx)
            engine.state.board.register_modifier(end_tile, mod_to_add)

            # 2. "Active Push": Eject any racers already on this tile
            victims = [
                r
                for r in engine.state.racers
                if r.position == end_tile and r.idx != owner_idx and not r.finished
            ]

            for v in victims:
                target = max(0, event.end_tile - 1)
                engine.push_warp(v.idx, target, source=self.name, phase=event.phase)
                logger.info(f"Huge Baby pushes {v.repr} to {target}")

                # Explicitly emit a trigger for THIS push.
                engine.emit_ability_trigger(owner_idx, self.name, f"Pushing {v.repr}")

            # Return False because we handled our own emissions.
            # This prevents the `_wrapped_handler` from firing a generic event.
            return False

        return False


class AbilityScoochStep(Ability):
    name: ClassVar[AbilityName] = "ScoochStep"
    triggers: tuple[type[GameEvent], ...] = (AbilityTriggeredEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        if not isinstance(event, AbilityTriggeredEvent):
            return False

        # Logic: Trigger on ANY ability, except my own
        if event.source_racer_idx == owner_idx:
            return False

        if event.source_racer_idx is None:
            _ = assert_never
            raise ValueError("AbilityTriggeredEvent should always have a source racer.")

        # Logging context
        source_racer: RacerState = engine.get_racer(event.source_racer_idx)
        cause_msg = f"Saw {source_racer.name} use {event.ability_name}"

        logger.info(f"{self.name}: {cause_msg} -> Moving 1")
        engine.push_move(owner_idx, 1, self.name, phase=Phase.REACTION)

        # Returns True, so ScoochStep will emit an AbilityTriggeredEvent.
        # This is fine, because the NEXT ScoochStep check will see source_idx == owner_idx
        # (assuming only one Scoocher exists).
        # If two Scoochers exist, they WILL infinite loop off each other.
        # That is actually consistent with the board game rules (infinite loop -> execute once -> stop).
        # Our Engine loop detector handles the "Stop" part.
        return True


class AbilityPartyPull(Ability):
    name: ClassVar[AbilityName] = "PartyPull"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        if not isinstance(event, TurnStartEvent):
            return False

        if event.racer_idx != owner_idx:
            return False

        party_animal = engine.get_racer(owner_idx)
        any_affected = False

        # CHANGED: We only log and return True if we actually queue a move.
        for r in engine.state.racers:
            if r.idx == owner_idx or r.finished:
                continue

            direction = 0
            if r.position < party_animal.position:
                direction = 1
            elif r.position > party_animal.position:
                direction = -1

            if direction != 0:
                engine.push_move(r.idx, direction, self.name, phase=Phase.PRE_MAIN)
                any_affected = True

        if any_affected:
            logger.info(f"{self.name}: Pulling everyone closer!")
            return True

        # If nobody moved (e.g. everyone is on the same tile), ability did not "happen".
        return False


class AbilityMagicalReroll(Ability):
    name: ClassVar[AbilityName] = "MagicalReroll"
    triggers: tuple[type[GameEvent], ...] = (RollModificationWindowEvent,)

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        if not isinstance(event, RollModificationWindowEvent):
            return False

        me = engine.get_racer(owner_idx)

        # 1. Eligibility Check
        if event.racer_idx != owner_idx:
            return False
        if me.reroll_count >= 2:
            return False

        # 2. Ask the Agent
        agent = engine.get_agent(owner_idx)
        decision_ctx = BooleanDecision(
            game_state=engine.state,
            source_racer_idx=owner_idx,
            reason=DecisionReason.MAGICAL_REROLL,
        )

        should_reroll = agent.make_boolean_decision(decision_ctx)

        if should_reroll:
            me.reroll_count += 1
            engine.emit_ability_trigger(
                owner_idx,
                self.name,
                f"Disliked roll of {event.current_roll_val}",
            )
            engine.trigger_reroll(owner_idx, "MagicalReroll")
            # Return False to prevent generic emission, as we handled it via emit_ability_trigger
            return False

        return False


class AbilityCopyLead(Ability):
    name: ClassVar[AbilityName] = "CopyLead"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    @override
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return False

        me = engine.get_racer(owner_idx)
        racers = engine.state.racers

        # 1. Find all racers who are strictly ahead of Copycat
        potential_targets = [
            r for r in racers if r.position > me.position and not r.finished
        ]

        if not potential_targets:
            logger.info(f"{self.name}: No one ahead to copy.")
            return False

        # 2. Find the highest position among those ahead
        max_pos = max(r.position for r in potential_targets)
        leaders = [r for r in potential_targets if r.position == max_pos]
        leaders.sort(key=lambda r: r.idx)

        # 3. Ask the Agent which leader to copy
        agent = engine.get_agent(owner_idx)
        decision_ctx = SelectionDecision(
            game_state=engine.state,
            source_racer_idx=owner_idx,
            reason=DecisionReason.COPY_LEAD_TARGET,
            options=leaders,
        )

        selected_index = agent.make_selection_decision(decision_ctx)
        target = leaders[selected_index]

        # Avoid redundant updates
        if me.abilities == target.abilities:
            return False

        logger.info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        engine.update_racer_abilities(owner_idx, target.abilities)
        return True


@dataclass(eq=False)
class ModifierSlime(RacerModifier, RollModificationMixin):
    """Applied TO a victim racer. Reduces their roll by 1.
    Owned by Gunk.
    """

    name: ClassVar[AbilityName | str] = "Slime"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: "GameEngine",
    ) -> None:
        # This modifier is attached to the VICTIM, and affects their roll
        # owner_idx is Gunk, query.racer_idx is the victim
        query.modifiers.append(-1)
        query.modifier_sources.append((self.name, -1))
        engine.emit_ability_trigger(
            owner_idx,
            self.name,
            f"Sliming {engine.get_racer(query.racer_idx).name}",
        )


class AbilitySlime(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "Slime"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    @staticmethod
    def on_gain(engine: GameEngine, owner_idx: int) -> None:
        # Apply debuff to ALL other active racers
        for r in engine.state.racers:
            if r.idx != owner_idx and not r.finished:
                engine.add_racer_modifier(r.idx, ModifierSlime(owner_idx=owner_idx))

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int) -> None:
        # Clean up debuff from everyone
        for r in engine.state.racers:
            engine.remove_racer_modifier(r.idx, ModifierSlime(owner_idx=owner_idx))


@dataclass(eq=False)
class ModifierPartySelfBoost(RacerModifier, RollModificationMixin):
    """Applied TO Party Animal. Boosts their own roll based on neighbors."""

    name: ClassVar[AbilityName | str] = "PartySelfBoost"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: "GameEngine",
    ) -> None:
        # This modifier is attached to Party Animal, affects their own roll
        # owner_idx is Party Animal, query.racer_idx is also Party Animal
        if query.racer_idx != owner_idx:
            return  # Safety check (should never happen)

        if owner_idx is None:
            _ = assert_never
            raise ValueError("owner_idx should never be None")

        owner = engine.get_racer(owner_idx)
        guests = [
            r
            for r in engine.state.racers
            if r.idx != owner_idx and not r.finished and r.position == owner.position
        ]
        if guests:
            bonus = len(guests)
            query.modifiers.append(bonus)
            query.modifier_sources.append((self.name, bonus))
            engine.emit_ability_trigger(
                owner_idx,
                self.name,
                f"Boosted by {bonus} guests",
            )


class AbilityPartyBoost(Ability, LifecycleManagedMixin):
    name: ClassVar[AbilityName] = "PartyBoost"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    @staticmethod
    def on_gain(engine: GameEngine, owner_idx: int):
        # Apply the "Check for Neighbors" modifier to MYSELF
        engine.add_racer_modifier(
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )

    @override
    @staticmethod
    def on_loss(engine: GameEngine, owner_idx: int):
        engine.remove_racer_modifier(
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )


# -----
# Simulation
# -----


class SandboxEngine:
    def __init__(self, engine: "GameEngine"):
        self.engine: GameEngine = engine

    @classmethod
    def from_engine(cls, src: "GameEngine") -> "SandboxEngine":
        state_copy = copy.deepcopy(src.state)
        queue_copy = copy.deepcopy(src.queue)

        eng = GameEngine(
            state=state_copy,
            rng=src.rng,
            agents=src.agents,  # keep original agents
            logging_enabled=False,
        )
        eng.queue = queue_copy

        # Make sure serial is safe if sandbox pushes new events
        eng.serial = max((se.serial for se in eng.queue), default=eng.serial)

        # Re-register abilities to rebuild subscribers (no separate subscriber logic needed)
        cls._rebuild_subscribers_via_update_abilities(eng)

        return cls(eng)

    @staticmethod
    def _rebuild_subscribers_via_update_abilities(eng: "GameEngine") -> None:
        # Clear whatever was there (fresh engine usually has empty subscribers anyway)
        eng.subscribers.clear()

        for racer in eng.state.racers:
            idx = racer.idx

            # Use whatever is the source of truth in your refactor:
            # - if you still store names: racer.abilities
            # - if you store instances: set(racer.active_abilities.keys())
            current_names = set(racer.abilities)

            # Force a full teardown + rebuild
            eng.update_racer_abilities(idx, set())
            eng.update_racer_abilities(idx, current_names)

    def run_turn_for(self, racer_idx: int) -> TurnOutcome:
        """Simulate exactly one turn for `racer_idx` inside this sandbox.
        - Does not mutate the real game (sandbox owns a copied state/queue).
        - Returns a TurnOutcome with per-racer deltas/snapshots.
        """
        eng = self.engine

        # Ensure we're simulating the intended racer
        eng.state.current_racer_idx = racer_idx

        # Snapshot BEFORE
        before_vp = [r.victory_points for r in eng.state.racers]
        before_pos = [r.position for r in eng.state.racers]

        # Run exactly one turn using the engine's normal logic
        eng.run_turn()

        # Snapshot AFTER
        after_vp = [r.victory_points for r in eng.state.racers]
        after_pos = [r.position for r in eng.state.racers]
        tripped = [r.tripped for r in eng.state.racers]

        # If you track eliminated explicitly, keep it; otherwise default to False.
        eliminated = [getattr(r, "eliminated", False) for r in eng.state.racers]

        vp_delta = [a - b for a, b in zip(after_vp, before_vp, strict=False)]

        return TurnOutcome(
            vp_delta=vp_delta,
            position=after_pos,
            tripped=tripped,
            eliminated=eliminated,
            start_position=before_pos,
        )


# ------------------------------
# 7. Setup
# ------------------------------

# Build these automatically at module load
ABILITY_CLASSES: dict[AbilityName, type[Ability]] = {
    cls.name: cls for cls in Ability.__subclasses__()
}
MODIFIER_CLASSES: dict[AbilityName | str, type[Modifier]] = {
    cls.name: cls for cls in Modifier.__subclasses__()
}

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "Centaur": {"Trample"},
    "HugeBaby": {"HugeBabyPush"},
    "Scoocher": {"ScoochStep"},
    "Banana": {"BananaTrip"},
    "Copycat": {"CopyLead"},
    "Gunk": {"Slime"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
    "Magician": {"MagicalReroll"},
}


if __name__ == "__main__":
    roster: list[RacerName] = [
        "PartyAnimal",
        "Scoocher",
        "Magician",
        "HugeBaby",
        "Centaur",
        "Banana",
    ]
    racers = [RacerState(i, n) for i, n in enumerate(roster)]
    eng = GameEngine(GameState(racers), random.Random(1))

    eng.run_race()
