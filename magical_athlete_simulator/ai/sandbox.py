import copy

from magical_athlete_simulator.core.state import LogContext, TurnOutcome
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.game_engine import GameEngine


class SandboxEngine:
    def __init__(self, engine: GameEngine):
        self.engine: GameEngine = engine

    @classmethod
    def from_engine(cls, src: GameEngine) -> "SandboxEngine":  # noqa: UP037
        state_copy = copy.deepcopy(src.state)
        queue_copy = copy.deepcopy(src.state.queue)

        engine_id = next(ENGINE_ID_COUNTER)
        log_ctx = LogContext(
            engine_id=engine_id,
            engine_level=src.log_context.engine_level + 1,
            parent_engine_id=src.log_context.engine_id,
        )

        eng = GameEngine(
            state=state_copy,
            rng=src.rng,
            agents=src.agents,  # keep original agents
            verbose=False,
            log_context=log_ctx,
        )
        eng.state.queue = queue_copy

        # Make sure serial is safe if sandbox pushes new events
        eng.state.serial = max(
            (se.serial for se in eng.state.queue),
            default=eng.state.serial,
        )

        # Re-register abilities to rebuild subscribers (no separate subscriber logic needed)
        cls._rebuild_subscribers_via_update_abilities(eng)

        return cls(eng)

    @staticmethod
    def _rebuild_subscribers_via_update_abilities(eng: GameEngine) -> None:
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


def simulate_turn_for(racer_idx: int, engine: GameEngine) -> TurnOutcome:
    """Public helper: deep-copy current state into a SandboxEngine
    and simulate one turn for `racer_idx`.
    """
    sandbox = SandboxEngine.from_engine(engine)
    return sandbox.run_turn_for(racer_idx)
