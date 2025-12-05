import heapq
import logging
import random
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Callable, Any

# ------------------------------
# 1. Logging & Context
# ------------------------------


class GlobalLogState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalLogState, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.total_turn = 0
        self.turn_log_count = 0
        self.current_racer_repr = "_"

    def new_round(self):
        self.total_turn += 1

    def start_turn_log(self, racer_repr: str):
        self.turn_log_count = 0
        self.current_racer_repr = racer_repr

    def inc_log_count(self):
        self.turn_log_count += 1


log_context = GlobalLogState()


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.total_turn = log_context.total_turn
        record.turn_log_count = log_context.turn_log_count
        record.racer_repr = log_context.current_racer_repr
        log_context.inc_log_count()
        return True


class CustomFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = f"{record.total_turn}.{record.racer_repr}.{record.turn_log_count}"
        msg = record.getMessage()
        return f"{prefix} - {record.levelname} - {msg}"


logger = logging.getLogger("magical_athlete")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CustomFormatter())
handler.addFilter(ContextFilter())
logger.addHandler(handler)
logger.propagate = False

# ------------------------------
# 2. Config
# ------------------------------

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

FINISH_SPACE: int = 20

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
    tripped: bool = False
    finished: bool = False
    abilities: set[AbilityName] = field(default_factory=set)

    # Temp state for re-roll logic (e.g. Magician can only use power once per turn)
    reroll_used_this_turn: bool = False

    @property
    def repr(self) -> str:
        return f"{self.idx}:{self.name}"


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    roll_state: RollState = field(default_factory=RollState)
    finished_order: list[int] = field(default_factory=list)

    def get_state_hash(self) -> int:
        # We hash the roll serial so loops within a specific roll attempt are detected,
        # but re-rolling (which changes serial) breaks the loop history.
        data = tuple((r.position, r.tripped, r.finished) for r in self.racers)
        return hash(data + (self.roll_state.serial_id,))


# ------------------------------
# 4. Events
# ------------------------------


class GameEvent:
    pass


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
class MoveCmdEvent(GameEvent):
    racer_idx: int
    distance: int
    source: str


@dataclass(frozen=True)
class WarpCmdEvent(GameEvent):
    racer_idx: int
    target_tile: int
    source: str


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    victim_idx: int
    tile_idx: int


@dataclass(frozen=True)
class LandingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int
    ability_name: AbilityName
    # Human-readable context for logs
    log_context: str


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)

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
# 5. Engine Core
# ------------------------------

AbilityCallback = Callable[[Any, int, "GameEngine"], None]


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
    modifiers: list[tuple["Modifier", int]] = field(default_factory=list)

    _serial: int = 0
    race_over: bool = False
    history: set[tuple[int, int]] = field(default_factory=set)

    def subscribe(
        self, event_type: type[GameEvent], callback: AbilityCallback, owner_idx: int
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def register_modifier(self, modifier: "Modifier", owner_idx: int):
        self.modifiers.append((modifier, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        racer = self.get_racer(racer_idx)
        racer.abilities = new_abilities
        # Unsubscribe old
        for et in self.subscribers:
            self.subscribers[et] = [
                s for s in self.subscribers[et] if s.owner_idx != racer_idx
            ]
        self.modifiers = [m for m in self.modifiers if m[1] != racer_idx]
        # Register new
        for an in new_abilities:
            if an in ABILITY_CLASSES:
                ABILITY_CLASSES[an]().register(self, racer_idx)
            if an in MODIFIER_CLASSES:
                self.register_modifier(MODIFIER_CLASSES[an](), racer_idx)

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    # --- Action Queuing ---

    def push_event(self, event: GameEvent, *, phase: int):
        self._serial += 1
        sched = ScheduledEvent(phase, 0, self._serial, event)
        heapq.heappush(self.queue, sched)

    def push_move(self, racer_idx: int, distance: int, source: str, phase: int):
        if distance == 0:
            return  # Explicit NO-OP
        self.push_event(MoveCmdEvent(racer_idx, distance, source), phase=phase)

    def push_warp(self, racer_idx: int, target: int, source: str, phase: int):
        if self.get_racer(racer_idx).position == target:
            return
        self.push_event(WarpCmdEvent(racer_idx, target, source), phase=phase)

    def emit_ability_trigger(
        self, source_idx: int, ability: AbilityName, log_context: str
    ):
        self.push_event(
            AbilityTriggeredEvent(source_idx, ability, log_context),
            phase=Phase.REACTION,
        )

    def trigger_reroll(self, source_idx: int, reason: str):
        """
        Cancels the current roll resolution and schedules a new roll immediately.
        """
        logger.info(
            f"!!! RE-ROLL TRIGGERED by {self.get_racer(source_idx).name} ({reason}) !!!"
        )
        # Increment serial to kill any pending ResolveMainMove events
        self.state.roll_state.serial_id += 1
        # Queue a new roll immediately
        self.push_event(
            PerformRollEvent(self.state.current_racer_idx), phase=Phase.ROLL_DICE
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
        log_context.reset()
        while not self.race_over:
            self.run_turn()
            self.advance_turn()

    def run_turn(self):
        self.history.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        racer.reroll_used_this_turn = False  # Reset turn-based flags

        log_context.start_turn_log(racer.repr)
        logger.info(f"=== START TURN: {racer.repr} ===")

        if racer.tripped:
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
                | LandingEvent()
                | AbilityTriggeredEvent()
                | RollModificationWindowEvent()
            ):
                self.publish_to_subscribers(event)
            case PerformRollEvent():
                self._handle_perform_roll(event)
            case ResolveMainMoveEvent():
                self._resolve_main_move(event)
            case MoveCmdEvent():
                self._handle_move(event)
            case WarpCmdEvent():
                self._handle_warp(event)

    def _handle_perform_roll(self, event: PerformRollEvent):
        # 1. New Serial for this specific roll attempt
        self.state.roll_state.serial_id += 1
        current_serial = self.state.roll_state.serial_id

        # 2. Roll & Modifiers
        base = self.rng.randint(1, 6)
        query = MoveDistanceQuery(event.racer_idx, base)

        # Apply modifiers (logs triggers internally)
        for mod, owner_idx in self.modifiers:
            if not self.get_racer(owner_idx).finished:
                mod.modify(query, owner_idx, self)

        final = query.final_value
        self.state.roll_state.base_value = base
        self.state.roll_state.final_value = final

        logger.info(
            f"Dice Roll: {base} (Mods: {sum(query.modifiers)}) -> Result: {final}"
        )

        # 3. Fire the 'Window' event. Listeners can call trigger_reroll() here.
        self.push_event(
            RollModificationWindowEvent(event.racer_idx, final, current_serial),
            phase=Phase.ROLL_WINDOW,
        )

        # 4. Schedule the resolution. If trigger_reroll() was called in step 3,
        # serial_id will increment, and this event will be ignored in _resolve_main_move.
        self.push_event(
            ResolveMainMoveEvent(event.racer_idx, current_serial), phase=Phase.MAIN_ACT
        )

    def _resolve_main_move(self, event: ResolveMainMoveEvent):
        # If serial doesn't match, it means a re-roll happened.
        if event.roll_serial != self.state.roll_state.serial_id:
            logger.debug("Ignoring stale roll resolution (Re-roll occurred).")
            return

        dist = self.state.roll_state.final_value
        if dist > 0:
            self.push_move(event.racer_idx, dist, "MainMove", phase=Phase.MOVE_EXEC)

    def _handle_move(self, evt: MoveCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        start = racer.position
        end = start + evt.distance

        logger.info(f"Move: {racer.repr} {start}->{end} ({evt.source})")

        # Passing logic
        if evt.distance > 0:
            for tile in range(start + 1, min(end, FINISH_SPACE) + 1):
                if tile < end:  # Must pass completely
                    victims = [
                        r
                        for r in self.state.racers
                        if r.position == tile and r.idx != racer.idx and not r.finished
                    ]
                    for v in victims:
                        self.push_event(
                            PassingEvent(racer.idx, v.idx, tile), phase=Phase.MOVE_EXEC
                        )

        racer.position = end
        if self._check_finish(racer):
            return
        self.push_event(LandingEvent(racer.idx, end), phase=Phase.BOARD)

    def _handle_warp(self, evt: WarpCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return
        logger.info(f"Warp: {racer.repr} -> {evt.target_tile} ({evt.source})")
        racer.position = evt.target_tile
        if self._check_finish(racer):
            return
        self.push_event(LandingEvent(racer.idx, evt.target_tile), phase=Phase.BOARD)

    def _check_finish(self, racer: RacerState) -> bool:
        if not racer.finished and racer.position > FINISH_SPACE:
            racer.finished = True
            self.state.finished_order.append(racer.idx)
            logger.info(
                f"!!! {racer.repr} FINISHED rank {len(self.state.finished_order)} !!!"
            )
            if len(self.state.finished_order) >= 2:
                self.race_over = True
                self.queue.clear()
            return True
        return False

    def advance_turn(self):
        if self.race_over:
            return
        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n
        while self.state.racers[next_idx].finished:
            next_idx = (next_idx + 1) % n
            if next_idx == curr:
                break
        if next_idx < curr:
            log_context.new_round()
        self.state.current_racer_idx = next_idx


# ------------------------------
# 6. Abilities
# ------------------------------


class Ability(ABC):
    """
    Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    triggers: tuple[type[GameEvent], ...] = ()

    @property
    @abstractmethod
    def name(self) -> AbilityName:
        """The unique name of the ability (e.g. 'Trample', 'ScoochStep')."""
        pass

    def register(self, engine: "GameEngine", owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        """
        The internal handler that wraps the user logic.
        It checks liveness, executes logic, and automatically emits the trigger event.
        """
        # 1. Dead racers tell no tales (usually)
        if engine.state.racers[owner_idx].finished:
            return

        # 2. execute() returns True if the ability actually "did something"
        #    or we can assume if it didn't return explicitly False, it ran.
        #    For now, let's assume if execute runs without returning early, it happened.
        #    To support "conditional" emission, execute could return a bool.
        #    Let's implement a 'did_trigger' return expectation for better logging accuracy.

        did_trigger = self.execute(event, owner_idx, engine)

        # 3. Automatic Emission
        if did_trigger:
            # We construct a generic context string. Subclasses can be more specific
            # if we refactor execute to return a context string, but for now,
            # the Event type is a good enough default context.
            ctx = f"Reacting to {event.__class__.__name__}"
            engine.emit_ability_trigger(owner_idx, self.name, ctx)

    @abstractmethod
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        """
        Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        pass


class Modifier(ABC):
    @property
    @abstractmethod
    def name(self) -> AbilityName:
        """The unique name of the ability (e.g. 'Trample', 'ScoochStep')."""
        pass

    @abstractmethod
    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        pass


# --- Implementations ---


class AbilityTrample(Ability):
    name = "Trample"
    triggers = (PassingEvent,)

    def execute(
        self, event: PassingEvent, owner_idx: int, engine: "GameEngine"
    ) -> bool:
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
    name = "BananaTrip"
    triggers = (PassingEvent,)

    def execute(
        self, event: PassingEvent, owner_idx: int, engine: "GameEngine"
    ) -> bool:
        # Logic: Only trigger if *I* am the victim
        if event.victim_idx != owner_idx:
            return False

        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return False

        logger.info(f"{self.name}: {mover.repr} passed Banana! Tripping mover.")
        mover.tripped = True
        return True


class AbilityHugeBabyPush(Ability):
    name = "HugeBabyPush"
    triggers = (LandingEvent,)

    def execute(
        self, event: LandingEvent, owner_idx: int, engine: "GameEngine"
    ) -> bool:
        # Logic: Trigger if someone lands on me
        if event.mover_idx == owner_idx:
            return False

        owner = engine.get_racer(owner_idx)

        # Rule: Cannot push if I am on Start
        if owner.position == 0:
            return False

        if owner.position != event.tile_idx:
            return False

        victim = engine.get_racer(event.mover_idx)
        target = max(0, owner.position - 1)

        logger.info(
            f"{self.name}: {victim.repr} landed on HugeBaby. Pushing back to {target}."
        )
        engine.push_warp(victim.idx, target, self.name, phase=Phase.REACTION)
        return True


class AbilityScoochStep(Ability):
    name = "ScoochStep"
    triggers = (AbilityTriggeredEvent,)

    def execute(
        self, event: AbilityTriggeredEvent, owner_idx: int, engine: "GameEngine"
    ) -> bool:
        # Logic: Trigger on ANY ability, except my own
        if event.source_racer_idx == owner_idx:
            return False

        # Logging context
        source_racer = engine.get_racer(event.source_racer_idx)
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
    name = "PartyPull"
    triggers = (TurnStartEvent,)

    def execute(
        self, event: TurnStartEvent, owner_idx: int, engine: "GameEngine"
    ) -> bool:
        if event.racer_idx != owner_idx:
            return False

        party_animal = engine.get_racer(owner_idx)
        logger.info(f"{self.name}: Pulling everyone closer!")

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

        return True


class AbilityCopyLead(Ability):
    name = "CopyLead"
    triggers = (LandingEvent, TurnStartEvent)

    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine") -> bool:
        me = engine.get_racer(owner_idx)
        active = [
            r for r in engine.state.racers if not r.finished and r.idx != owner_idx
        ]
        if not active:
            return False

        max_pos = max(r.position for r in active)
        leaders = [r for r in active if r.position == max_pos]
        leader = min(leaders, key=lambda r: r.idx)

        current_abilities = me.abilities
        # We rely on global RACER_ABILITIES here, could be injected
        target_abilities = RACER_ABILITIES.get(leader.name, set()) | {self.name}

        if current_abilities != target_abilities:
            logger.info(f"{self.name}: Switching to copy {leader.name}")
            engine.update_racer_abilities(owner_idx, target_abilities)
            # Does changing abilities count as "Triggering" the power?
            # Usually yes, it's a visible effect.
            return True

        return False


class ModifierSlime(Modifier):
    name = "Slime"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx != owner_idx:
            query.modifiers.append(-1)
            engine.emit_ability_trigger(
                owner_idx,
                self.name,
                f"Sliming {engine.get_racer(query.racer_idx).name}",
            )


class ModifierPartyBoost(Modifier):
    name = "PartyBoost"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx != owner_idx:
            return
        owner = engine.get_racer(owner_idx)
        guests = [
            r
            for r in engine.state.racers
            if r.idx != owner_idx and not r.finished and r.position == owner.position
        ]
        if guests:
            query.modifiers.append(len(guests))
            # Note: We emit trigger here because the rules say "When power happens".
            # Static modifiers applying counts as the power 'happening' for that roll.
            engine.emit_ability_trigger(
                owner_idx, self.name, f"Boosted by {len(guests)} guests"
            )


# --- New Re-roll Ability Example (Magician) ---


class AbilityMagicalReroll(Ability):
    """Example: Can reroll any die once per turn."""

    name = "MagicalReroll"
    triggers = (RollModificationWindowEvent,)

    def execute(
        self, event: RollModificationWindowEvent, owner_idx: int, engine: "GameEngine"
    ):
        me = engine.get_racer(owner_idx)

        # Logic: Reroll if I rolled a 1 or 2
        if (
            event.racer_idx == owner_idx
            and event.current_roll_val <= 2
            and not me.reroll_used_this_turn
        ):
            me.reroll_used_this_turn = True
            engine.emit_ability_trigger(
                owner_idx, self.name, f"Disliked roll of {event.current_roll_val}"
            )
            engine.trigger_reroll(owner_idx, "MagicalReroll")


# ------------------------------
# 7. Setup
# ------------------------------

ABILITY_CLASSES = {
    "Trample": AbilityTrample,
    "HugeBabyPush": AbilityHugeBabyPush,
    "BananaTrip": AbilityBananaTrip,
    "ScoochStep": AbilityScoochStep,
    "PartyPull": AbilityPartyPull,
    "CopyLead": AbilityCopyLead,
    "MagicalReroll": AbilityMagicalReroll,
}
MODIFIER_CLASSES = {"PartyBoost": ModifierPartyBoost, "Slime": ModifierSlime}

RACER_ABILITIES = {
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
    roster: list[RacerName] = ["PartyAnimal", "Scoocher", "Magician", "HugeBaby"]
    racers = [RacerState(i, n) for i, n in enumerate(roster)]
    eng = GameEngine(GameState(racers), random.Random(42))

    for r in racers:
        eng.update_racer_abilities(r.idx, RACER_ABILITIES.get(r.name, set()))

    eng.run_race()
