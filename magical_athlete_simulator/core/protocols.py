import random
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import ClassVar, Protocol, override

from magical_athlete_simulator.core.events import GameEvent, MoveDistanceQuery
from magical_athlete_simulator.core.types import AbilityName, ModifierName, RacerName

AbilityCallback = Callable[[GameEvent, int, "GameEngineLike"], None]


class GameEngineLike(Protocol):
    """
    Defines the public interface of the GameEngine that core modules
    like Abilities and Modifiers can depend on.
    """

    # --- Attributes ---
    # Core modules need to read the game state.
    state: "GameState"
    rng: random.Random
    log_context: "LogContext"

    # --- Methods for Information ---
    def get_racer(self, idx: int) -> "RacerState": ...

    def get_racer_pos(self, idx: int) -> int: ...

    def get_agent(self, racer_idx: int) -> "Agent": ...

    # --- Methods for Modifying State / Queueing Actions ---
    def add_racer_modifier(
        self,
        target_idx: int,
        modifier: "RacerModifier",
    ) -> None: ...

    def remove_racer_modifier(
        self,
        target_idx: int,
        modifier: "RacerModifier",
    ) -> None: ...

    def update_racer_abilities(
        self,
        racer_idx: int,
        new_abilities: set[AbilityName],
    ) -> None: ...

    def push_move(
        self,
        racer_idx: int,
        distance: int,
        source: str,
        phase: int,
    ) -> None: ...

    def push_warp(
        self,
        racer_idx: int,
        target: int,
        source: str,
        phase: int,
    ) -> None: ...

    def trigger_reroll(self, source_idx: int, reason: str) -> None: ...

    # --- Methods for Event Handling ---
    def subscribe(
        self,
        event_type: type[GameEvent],
        callback: AbilityCallback,
        owner_idx: int,
    ) -> None: ...

    def emit_ability_trigger(
        self,
        source_idx: int | None,
        ability: AbilityName | ModifierName | str,
        log_context: str,
    ) -> None: ...

    # --- Methods for Simulation ---
    def simulate_turn_for(self, racer_idx: int) -> "TurnOutcome": ...


class BoardLike(Protocol):
    # --- Data shape ---
    length: int
    static_features: dict[int, list["SpaceModifier"]]
    dynamic_modifiers: defaultdict[int, set["SpaceModifier"]]

    @property
    def finish_space(self) -> int:  # mirrors your property
        ...

    # --- Modifier access ---
    def register_modifier(self, tile: int, modifier: "SpaceModifier") -> None: ...

    def unregister_modifier(self, tile: int, modifier: "SpaceModifier") -> None: ...

    def get_modifiers_at(self, tile: int) -> list["SpaceModifier"]: ...

    # --- Engine interaction hooks ---
    def resolve_position(
        self,
        target: int,
        mover_idx: int,
        engine: GameEngineLike,
    ) -> int: ...

    def trigger_on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: GameEngineLike,
    ) -> None: ...

    # --- Debug helpers (optional but cheap to include) ---
    def dump_state(self) -> None: ...


# -----------------
# MixIns
# -----------------


class RollModificationMixin(ABC):
    """Mixin for modifiers that alter dice rolls."""

    @abstractmethod
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngineLike,
    ) -> None:
        pass


class ApproachHookMixin(ABC):
    """Allows a modifier to redirect incoming racers (e.g., Huge Baby blocking)."""

    @abstractmethod
    def on_approach(self, target: int, mover_idx: int, engine: GameEngineLike) -> int:
        pass


class LandingHookMixin(ABC):
    """Allows a modifier to react when a racer stops on the tile (e.g., Trip, VP)."""

    @abstractmethod
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: int,
        engine: GameEngineLike,
    ) -> None:
        pass


# -----------------
# Modifiers
# -----------------


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


@dataclass(eq=False)
class SpaceModifier(Modifier, ABC):
    """Base for board features. Can mix in Approach or Landing hooks."""

    priority: int = 5


@dataclass(eq=False)
class RacerModifier(Modifier, ABC):
    """Attached to Racers (e.g. SlimeDebuff)."""


# -----------------
# Abilities
# -----------------


class Ability(ABC):
    """Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    name: ClassVar[AbilityName]
    triggers: tuple[type[GameEvent], ...] = ()

    def register(self, engine: GameEngineLike, owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngineLike,
    ):
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

    def execute(self, event: GameEvent, owner_idx: int, engine: GameEngineLike) -> bool:
        """Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        _ = event, owner_idx, engine
        return False


class LifecycleManagedMixin(ABC):
    @staticmethod
    @abstractmethod
    def on_gain(engine: GameEngineLike, owner_idx: int) -> None:
        pass

    @staticmethod
    @abstractmethod
    def on_loss(engine: GameEngineLike, owner_idx: int) -> None:
        pass


# -----------------
# Agent and AI
# -----------------


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


@dataclass(frozen=True)
class TurnOutcome:
    """Result of simulating exactly one turn for a specific racer."""

    vp_delta: list[int]  # per racer: final_vp - start_vp
    position: list[int]  # per racer final positions
    tripped: list[bool]  # per racer tripped flags at end of turn
    eliminated: list[bool]  # per racer eliminated flags at end of turn
    start_position: list[int]  # per racer start positions


# -----------------
# State
# -----------------


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
    active_abilities: dict[AbilityName, Ability] = field(default_factory=dict)

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
    board: BoardLike
    current_racer_idx: int = 0
    roll_state: RollState = field(default_factory=RollState)

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
