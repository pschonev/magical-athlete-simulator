import heapq
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Sequence, Type, Callable, Any

# ------------------------------
# IDs and static configuration
# ------------------------------

RacerName = Literal[
    "Centaur",
    "BigBaby",
    "Scoocher",
    "Banana",
    "Copycat",
    "Gunk",
    "PartyAnimal",
]

AbilityName = Literal[
    "Trample",
    "BigBabyPush",
    "BananaTrip",
    "ScoochStep",
    "CopyLead",
    "Slime",
    "PartyPull",
    "PartyBoost",
]

TRIP_SPACES: set[int] = {4, 10, 18}
FINISH_SPACE: int = 20
WIN_VP: int = 5

logger = logging.getLogger("magical_athlete")


# ------------------------------
# Core state
# ------------------------------


@dataclass(slots=True)
class RacerState:
    idx: int
    name: RacerName
    position: int = 0
    tripped: bool = False
    finished: bool = False
    victory_points: int = 0
    abilities: set[AbilityName] = field(default_factory=set)


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    finished_order: list[int] = field(default_factory=list)


# ------------------------------
# Events
# ------------------------------


class GameEvent:
    """Marker base class."""

    pass


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollAndMainMoveEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class CmdMoveEvent(GameEvent):
    racer_idx: int
    distance: int
    is_main_move: bool
    source_racer_idx: int | None
    source_ability: AbilityName | None


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class LandingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int
    ability_id: AbilityName


@dataclass(frozen=True)
class MoveDistanceQuery:
    """Used for synchronous modifier queries (Gunk, PartyBoost)."""

    racer_idx: int
    base_roll: int
    modifiers: list[int] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_roll + sum(self.modifiers))


@dataclass(order=True)
class ScheduledEvent:
    phase: int
    turn_distance: int
    serial: int
    event: GameEvent = field(compare=False)


class Phase:
    SYSTEM = 0
    BOARD = 10
    ABILITY = 20
    MOVE = 30
    CLEANUP = 100


# ------------------------------
# Pub/Sub Registry
# ------------------------------

AbilityCallback = Callable[[Any, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


# ------------------------------
# Ability Base Class
# ------------------------------


class Ability(ABC):
    """Base class for all abilities with auto-registration."""

    name: AbilityName
    triggers: tuple[Type[GameEvent], ...] = ()

    def register(self, engine: "GameEngine", owner_idx: int):
        """Default: auto-subscribe to events in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        """Wrapper that calls logic and auto-emits ability trigger."""
        self.execute(event, owner_idx, engine)
        engine.emit_ability_trigger(owner_idx, self.name)

    @abstractmethod
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        """The actual ability logic. Subclasses implement this."""
        pass


class Modifier(ABC):
    """Base class for synchronous modifiers (Gunk, PartyBoost)."""

    name: AbilityName

    @abstractmethod
    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        pass


# ------------------------------
# Concrete Abilities
# ------------------------------


class AbilityTrample(Ability):
    name: AbilityName = "Trample"
    triggers = (PassingEvent,)

    def execute(self, event: PassingEvent, owner_idx: int, engine: "GameEngine"):
        if event.mover_idx != owner_idx:
            return

        victims = [
            r
            for r in engine.state.racers
            if r.position == event.tile_idx and not r.finished and r.idx != owner_idx
        ]

        if not victims:
            return

        logger.info(
            "Centaur Trample: tramples racers %s on tile %d",
            [v.idx for v in victims],
            event.tile_idx,
        )

        for v in victims:
            engine.push_event(
                CmdMoveEvent(
                    racer_idx=v.idx,
                    distance=-2,
                    is_main_move=False,
                    source_racer_idx=owner_idx,
                    source_ability=self.name,
                ),
                phase=Phase.MOVE,
                reactor_idx=owner_idx,
            )


class AbilityBigBabyPush(Ability):
    name: AbilityName = "BigBabyPush"
    triggers = (LandingEvent,)

    def execute(self, event: LandingEvent, owner_idx: int, engine: "GameEngine"):
        owner = engine.get_racer(owner_idx)
        victim = engine.get_racer(event.mover_idx)

        if event.mover_idx == owner_idx or victim.finished:
            return

        if owner.position != event.tile_idx:
            return

        logger.info(
            "BigBabyPush: racer #%d pushes racer #%d back 1", owner_idx, event.mover_idx
        )

        engine.push_event(
            CmdMoveEvent(
                racer_idx=event.mover_idx,
                distance=-1,
                is_main_move=False,
                source_racer_idx=owner_idx,
                source_ability=self.name,
            ),
            phase=Phase.MOVE,
            reactor_idx=owner_idx,
        )


class AbilityBananaTrip(Ability):
    name: AbilityName = "BananaTrip"
    triggers = (PassingEvent,)

    def execute(self, event: PassingEvent, owner_idx: int, engine: "GameEngine"):
        owner = engine.get_racer(owner_idx)

        if event.mover_idx == owner_idx:
            return

        if owner.position != event.tile_idx:
            return

        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return

        logger.info("BananaTrip: racer #%d trips racer #%d", owner_idx, event.mover_idx)
        mover.tripped = True


class AbilityScoochStep(Ability):
    name: AbilityName = "ScoochStep"
    triggers = (AbilityTriggeredEvent,)

    def execute(
        self, event: AbilityTriggeredEvent, owner_idx: int, engine: "GameEngine"
    ):
        # Don't trigger on self to prevent simple loops
        if event.source_racer_idx == owner_idx:
            return

        logger.info(
            "ScoochStep: racer #%d moves 1 due to ability %s",
            owner_idx,
            event.ability_id,
        )

        engine.push_event(
            CmdMoveEvent(
                racer_idx=owner_idx,
                distance=1,
                is_main_move=False,
                source_racer_idx=owner_idx,
                source_ability=self.name,
            ),
            phase=Phase.MOVE,
            reactor_idx=owner_idx,
        )


class AbilityCopyLead(Ability):
    name: AbilityName = "CopyLead"
    triggers = (TurnStartEvent,)

    def execute(self, event: TurnStartEvent, owner_idx: int, engine: "GameEngine"):
        if event.racer_idx != owner_idx:
            return

        copycat = engine.get_racer(owner_idx)
        active = [
            r for r in engine.state.racers if not r.finished and r.idx != owner_idx
        ]

        if not active:
            return

        max_pos = max(r.position for r in active)
        leaders = [r for r in active if r.position == max_pos]
        leader = engine.rng.choice(leaders)

        # Copy abilities from the leader's definition
        new_abilities = set(RACER_ABILITIES.get(leader.name, set()))
        new_abilities.add(self.name)  # Keep CopyLead itself

        # Unregister old abilities and register new ones
        engine.update_racer_abilities(owner_idx, new_abilities)

        logger.info(
            "CopyLead: racer #%d copies abilities of racer #%d: %s",
            owner_idx,
            leader.idx,
            sorted(new_abilities),
        )


class AbilityPartyPull(Ability):
    name: AbilityName = "PartyPull"
    triggers = (TurnStartEvent,)

    def execute(self, event: TurnStartEvent, owner_idx: int, engine: "GameEngine"):
        if event.racer_idx != owner_idx:
            return

        party = engine.get_racer(owner_idx)
        if party.finished:
            return

        logger.info("PartyPull: racer #%d pulls everyone closer", owner_idx)

        for r in engine.state.racers:
            if r.idx == owner_idx or r.finished:
                continue

            if r.position < party.position:
                dist = 1
            elif r.position > party.position:
                dist = -1
            else:
                continue

            engine.push_event(
                CmdMoveEvent(
                    racer_idx=r.idx,
                    distance=dist,
                    is_main_move=False,
                    source_racer_idx=owner_idx,
                    source_ability=self.name,
                ),
                phase=Phase.MOVE,
                reactor_idx=owner_idx,
            )


# ------------------------------
# Modifiers
# ------------------------------


class ModifierSlime(Modifier):
    name: AbilityName = "Slime"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx == owner_idx:
            return

        logger.info("Gunk Slime: modifies racer #%d main move by -1", query.racer_idx)
        query.modifiers.append(-1)
        engine.emit_ability_trigger(owner_idx, self.name)


class ModifierPartyBoost(Modifier):
    name: AbilityName = "PartyBoost"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx != owner_idx:
            return

        party = engine.get_racer(owner_idx)
        same_tile = [
            r
            for r in engine.state.racers
            if r.idx != owner_idx and not r.finished and r.position == party.position
        ]
        bonus = len(same_tile)

        if bonus:
            logger.info(
                "PartyBoost: racer #%d gets +%d (co-occupants: %s)",
                owner_idx,
                bonus,
                [r.idx for r in same_tile],
            )
            query.modifiers.append(bonus)
            engine.emit_ability_trigger(owner_idx, self.name)


# ------------------------------
# Registry
# ------------------------------

ABILITY_CLASSES: dict[AbilityName, Type[Ability]] = {
    "Trample": AbilityTrample,
    "BigBabyPush": AbilityBigBabyPush,
    "BananaTrip": AbilityBananaTrip,
    "ScoochStep": AbilityScoochStep,
    "CopyLead": AbilityCopyLead,
    "PartyPull": AbilityPartyPull,
}

MODIFIER_CLASSES: dict[AbilityName, Type[Modifier]] = {
    "Slime": ModifierSlime,
    "PartyBoost": ModifierPartyBoost,
}

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "Centaur": {"Trample"},
    "BigBaby": {"BigBabyPush"},
    "Scoocher": {"ScoochStep"},
    "Banana": {"BananaTrip"},
    "Copycat": {"CopyLead"},
    "Gunk": {"Slime"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
}


# ------------------------------
# Engine
# ------------------------------


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    queue: list[ScheduledEvent] = field(default_factory=list)
    subscribers: dict[Type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    modifiers: list[tuple[Modifier, int]] = field(
        default_factory=list
    )  # (modifier, owner_idx)
    _serial: int = 0
    race_over: bool = False
    seen_signatures: set[int] = field(default_factory=set)

    # ---------- Pub/Sub ----------

    def subscribe(
        self, event_type: Type[GameEvent], callback: AbilityCallback, owner_idx: int
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def register_modifier(self, modifier: Modifier, owner_idx: int):
        self.modifiers.append((modifier, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        """Update a racer's abilities and re-register them (for Copycat)."""
        racer = self.get_racer(racer_idx)
        racer.abilities = new_abilities

        # Clear old subscriptions for this racer
        for event_type in self.subscribers:
            self.subscribers[event_type] = [
                sub
                for sub in self.subscribers[event_type]
                if sub.owner_idx != racer_idx
            ]

        # Clear old modifiers
        self.modifiers = [(mod, idx) for mod, idx in self.modifiers if idx != racer_idx]

        # Re-register new abilities
        for ability_name in new_abilities:
            if ability_name in ABILITY_CLASSES:
                ability = ABILITY_CLASSES[ability_name]()
                ability.register(self, racer_idx)
            if ability_name in MODIFIER_CLASSES:
                modifier = MODIFIER_CLASSES[ability_name]()
                self.register_modifier(modifier, racer_idx)

    def publish_to_subscribers(self, event: GameEvent):
        """Publish event to all subscribers, sorted by turn order."""
        if type(event) not in self.subscribers:
            return

        subs = self.subscribers[type(event)]

        # Sort by turn distance to ensure proper trigger order
        def sort_key(sub: Subscriber):
            current = self.state.current_racer_idx
            total = len(self.state.racers)
            return (sub.owner_idx - current) % total

        sorted_subs = sorted(subs, key=sort_key)

        for sub in sorted_subs:
            owner = self.get_racer(sub.owner_idx)
            if owner.finished:
                continue
            sub.callback(event, sub.owner_idx, self)

    # ---------- Scheduling ----------

    def push_event(
        self, event: GameEvent, *, phase: int, reactor_idx: int | None = None
    ):
        self._serial += 1
        current = self.state.current_racer_idx
        if reactor_idx is None or not self.state.racers:
            dist = 0
        else:
            n = len(self.state.racers)
            dist = (reactor_idx - current) % n

        sched = ScheduledEvent(
            phase=phase, turn_distance=dist, serial=self._serial, event=event
        )
        heapq.heappush(self.queue, sched)
        logger.debug(
            "Enqueued %s (phase=%s, dist=%s, serial=%s)",
            event,
            phase,
            dist,
            self._serial,
        )

    def emit_ability_trigger(self, source_idx: int, ability: AbilityName):
        r = self.get_racer(source_idx)
        if r.finished:
            return
        evt = AbilityTriggeredEvent(source_racer_idx=source_idx, ability_id=ability)
        self.push_event(evt, phase=Phase.ABILITY, reactor_idx=source_idx)

    # ---------- Main Loop ----------

    def run_race(self):
        while not self.race_over:
            self.start_turn()
            self.process_events_for_turn()
            self.advance_turn()

    def start_turn(self):
        self.seen_signatures.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        logger.info("=== Turn start: Racer %s (#%d) ===", racer.name, cr)
        self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM, reactor_idx=cr)

    def process_events_for_turn(self):
        while self.queue and not self.race_over:
            sched = heapq.heappop(self.queue)
            event = sched.event
            if self.is_loop(event):
                logger.warning("Loop detected for event %s – skipping", event)
                continue
            logger.info("Processing %s", event)
            self.handle_event(event)

    def advance_turn(self):
        if self.race_over:
            return
        n = len(self.state.racers)
        for _ in range(n):
            self.state.current_racer_idx = (self.state.current_racer_idx + 1) % n
            if not self.state.racers[self.state.current_racer_idx].finished:
                break

    # ---------- Loop Detection ----------

    def hash_state(self) -> int:
        positions = tuple(r.position for r in self.state.racers)
        tripped = tuple(r.tripped for r in self.state.racers)
        return hash((positions, tripped))

    def is_loop(self, event: GameEvent) -> bool:
        key = (type(event).__name__, self.hash_state())
        sig = hash(key)
        if sig in self.seen_signatures:
            return True
        self.seen_signatures.add(sig)
        return False

    # ---------- Event Handling ----------

    def handle_event(self, event: GameEvent):
        match event:
            case TurnStartEvent():
                self.on_turn_start(event)
            case RollAndMainMoveEvent():
                self.on_roll_and_main_move(event)
            case CmdMoveEvent():
                self.on_cmd_move(event)
            case PassingEvent():
                self.publish_to_subscribers(event)
            case LandingEvent():
                self.on_landing(event)
            case AbilityTriggeredEvent():
                self.publish_to_subscribers(event)
            case _:
                logger.warning("Unhandled event type: %s", event)

    # ---------- Helpers ----------

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    # ---------- Turn Start ----------

    def on_turn_start(self, event: TurnStartEvent):
        racer = self.get_racer(event.racer_idx)
        if racer.finished:
            logger.info(
                "Racer %s (#%d) already finished; skipping turn",
                racer.name,
                event.racer_idx,
            )
            return

        if racer.tripped:
            logger.info(
                "Racer %s (#%d) stands up from being tripped",
                racer.name,
                event.racer_idx,
            )
            racer.tripped = False
            return

        # Publish to subscribers (CopyLead, PartyPull)
        self.publish_to_subscribers(event)

        # Queue main move
        self.push_event(
            RollAndMainMoveEvent(event.racer_idx),
            phase=Phase.SYSTEM,
            reactor_idx=event.racer_idx,
        )

    # ---------- Main Move ----------

    def on_roll_and_main_move(self, event: RollAndMainMoveEvent):
        racer = self.get_racer(event.racer_idx)
        if racer.finished:
            return

        roll = self.rng.randint(1, 6)
        logger.info("Racer %s (#%d) rolls %d", racer.name, event.racer_idx, roll)

        distance = self.apply_move_modifiers(event.racer_idx, roll)
        logger.info(
            "Racer %s (#%d) main move distance: %d",
            racer.name,
            event.racer_idx,
            distance,
        )

        if distance != 0:
            move_evt = CmdMoveEvent(
                racer_idx=event.racer_idx,
                distance=distance,
                is_main_move=True,
                source_racer_idx=None,
                source_ability=None,
            )
            self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=event.racer_idx)

    def apply_move_modifiers(self, target_idx: int, base: int) -> int:
        query = MoveDistanceQuery(racer_idx=target_idx, base_roll=base)

        for modifier, owner_idx in self.modifiers:
            owner = self.get_racer(owner_idx)
            if owner.finished:
                continue
            modifier.modify(query, owner_idx, self)

        return query.final_value

    # ---------- Movement ----------

    def on_cmd_move(self, evt: CmdMoveEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        start = racer.position
        dist = evt.distance

        logger.info(
            "CmdMove: %s (#%d) moves from %d by %d (source_racer=%s, source_ability=%s)",
            racer.name,
            racer.idx,
            start,
            dist,
            evt.source_racer_idx,
            evt.source_ability,
        )

        if dist == 0:
            self.push_event(
                LandingEvent(mover_idx=evt.racer_idx, tile_idx=start),
                phase=Phase.SYSTEM,
                reactor_idx=evt.racer_idx,
            )
            return

        direction = 1 if dist > 0 else -1
        steps = abs(dist)

        for i in range(1, steps):
            tile = start + direction * i
            if tile > FINISH_SPACE:
                break
            self.push_event(
                PassingEvent(mover_idx=evt.racer_idx, tile_idx=tile),
                phase=Phase.SYSTEM,
                reactor_idx=evt.racer_idx,
            )

        final_tile = start + dist
        self.push_event(
            LandingEvent(mover_idx=evt.racer_idx, tile_idx=final_tile),
            phase=Phase.SYSTEM,
            reactor_idx=evt.racer_idx,
        )

    def on_landing(self, evt: LandingEvent):
        mover = self.get_racer(evt.mover_idx)
        if mover.finished:
            return

        logger.info(
            "LandingEvent: %s (#%d) lands on %d", mover.name, mover.idx, evt.tile_idx
        )
        mover.position = evt.tile_idx

        if mover.position > FINISH_SPACE:
            self.handle_finish(mover.idx)
            return

        if mover.position in TRIP_SPACES:
            logger.info(
                "Board: tile %d trips %s (#%d)", mover.position, mover.name, mover.idx
            )
            mover.tripped = True

        # Publish to subscribers (BigBabyPush)
        self.publish_to_subscribers(evt)

    def handle_finish(self, racer_idx: int):
        racer = self.get_racer(racer_idx)
        if racer.finished:
            return

        racer.finished = True
        racer.position = FINISH_SPACE + 1
        self.state.finished_order.append(racer_idx)
        order = len(self.state.finished_order)

        logger.info("Racer %s (#%d) finishes in place %d", racer.name, racer.idx, order)

        if order == 1:
            racer.victory_points += WIN_VP
            logger.info(
                "Racer %s (#%d) gains %d VP (total %d)",
                racer.name,
                racer.idx,
                WIN_VP,
                racer.victory_points,
            )

        if order >= 2:
            logger.info("Second finisher reached; race over.")
            self.race_over = True
            self.queue.clear()


# ------------------------------
# Factory
# ------------------------------


def build_engine(racers: Sequence[RacerName], seed: int = 0) -> GameEngine:
    state_racers: list[RacerState] = []
    for idx, name in enumerate(racers):
        abilities = set(RACER_ABILITIES.get(name, set()))
        state_racers.append(
            RacerState(
                idx=idx,
                name=name,
                position=0,
                tripped=False,
                finished=False,
                victory_points=0,
                abilities=abilities,
            )
        )

    state = GameState(racers=state_racers, current_racer_idx=0)
    rng = random.Random(seed)
    engine = GameEngine(state=state, rng=rng)

    # Register all abilities
    for racer in state_racers:
        for ability_name in racer.abilities:
            if ability_name in ABILITY_CLASSES:
                ability = ABILITY_CLASSES[ability_name]()
                ability.register(engine, racer.idx)
            if ability_name in MODIFIER_CLASSES:
                modifier = MODIFIER_CLASSES[ability_name]()
                engine.register_modifier(modifier, racer.idx)

    return engine


# ------------------------------
# Demo
# ------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    starting_racers: list[RacerName] = [
        "Centaur",
        "BigBaby",
        "Scoocher",
        "Banana",
        "Copycat",
        "Gunk",
        "PartyAnimal",
    ]

    engine = build_engine(starting_racers, seed=42)
    engine.run_race()

    logger.info(
        "Final positions: %s",
        [(r.idx, r.name, r.position) for r in engine.state.racers],
    )
    logger.info(
        "VP totals: %s",
        [(r.idx, r.name, r.victory_points) for r in engine.state.racers],
    )
