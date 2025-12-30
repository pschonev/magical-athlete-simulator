import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import math
    import logging
    import re
    from rich.console import Console
    from rich.logging import RichHandler
    from typing import get_args

    # Imports
    from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
    from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
    from magical_athlete_simulator.engine.logging import (
        RichMarkupFormatter,
        GameLogHighlighter,
        ContextFilter,
    )
    from magical_athlete_simulator.core.types import RacerName
    from magical_athlete_simulator.core.events import (
        MoveCmdEvent,
        WarpCmdEvent,
        TripCmdEvent,
        PerformMainRollEvent,
        TurnStartEvent,
    )
    return (
        BOARD_DEFINITIONS,
        Console,
        GameLogHighlighter,
        GameScenario,
        MoveCmdEvent,
        RacerConfig,
        RacerName,
        RichHandler,
        RichMarkupFormatter,
        TripCmdEvent,
        WarpCmdEvent,
        get_args,
        logging,
        math,
        mo,
        re,
    )


@app.cell
def _(math):
    # --- CONSTANTS ---
    space_colors = ["#4CAF50"] + ["#F5F5F5", "#E0E0E0"] * 14 + ["#F44336"]
    space_colors = space_colors[:30]

    racer_colors = {
        "Banana": "#FFD700",
        "Centaur": "#8B4513",
        "Magician": "#9370DB",
        "Scoocher": "#FF6347",
        "Gunk": "#228B22",
        "HugeBaby": "#FF69B4",
        "Copycat": "#4682B4",
        "Mermaid": "#00CED1",
        "Amazon": "#DC143C",
        "Ninja": "#2F4F4F",
    }

    FALLBACK_PALETTE = [
        "#8A2BE2",
        "#5F9EA0",
        "#D2691E",
        "#FF8C00",
        "#2E8B57",
        "#1E90FF",
    ]


    def get_racer_color(name):
        if name in racer_colors:
            return racer_colors[name]
        try:
            return FALLBACK_PALETTE[(hash(name) % len(FALLBACK_PALETTE))]
        except:
            return "#888888"


    def generate_racetrack_positions(
        num_spaces, start_x, start_y, straight_len, radius
    ):
        positions = []
        perimeter = (2 * straight_len) + (2 * math.pi * radius)
        step_distance = perimeter / num_spaces
        right_circle_cx = start_x + straight_len
        right_circle_cy = start_y - radius
        left_circle_cx = start_x
        left_circle_cy = start_y - radius

        for i in range(num_spaces):
            dist = i * step_distance
            if dist < straight_len:
                x, y, angle = start_x + dist, start_y, 0
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                fraction = arc_dist / (math.pi * radius)
                theta = (math.pi / 2) - (fraction * math.pi)
                x = right_circle_cx + radius * math.cos(theta)
                y = right_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x, y, angle = (
                    (start_x + straight_len) - top_dist,
                    start_y - (2 * radius),
                    180,
                )
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                fraction = arc_dist / (math.pi * radius)
                theta = (-math.pi / 2) - (fraction * math.pi)
                x = left_circle_cx + radius * math.cos(theta)
                y = left_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90
            positions.append((x, y, angle))
        return positions


    board_positions = generate_racetrack_positions(30, 120, 350, 350, 100)
    return board_positions, get_racer_color, space_colors


@app.cell
def _(get_racer_color, math):
    # --- RENDERER ---
    def render_game_track(turn_data, positions_map, colors_map):
        import html as _html

        if not turn_data:
            return "<p>No Data</p>"

        svg_elements = []
        rw, rh = 50, 30

        # 1. Track spaces
        for i, (cx, cy, rot) in enumerate(positions_map):
            transform = f"rotate({rot}, {cx}, {cy})"
            svg_elements.append(
                f'<rect x="{cx - rw / 2:.1f}" y="{cy - rh / 2:.1f}" width="{rw}" height="{rh}" '
                f'fill="{colors_map[i]}" stroke="#555" stroke-width="1" transform="{transform}" rx="4" />'
            )
            svg_elements.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" font-family="sans-serif" font-size="10" font-weight="bold" '
                f'text-anchor="middle" fill="#333" transform="{transform}">{i}</text>'
            )

        # 2. Legend
        legend_start_x = 20
        legend_start_y = 20
        legend_col_width = 110
        legend_row_height = 20
        items_per_col = 4

        num_items = len(turn_data["names"])
        num_cols = math.ceil(num_items / items_per_col)
        legend_bg_width = num_cols * legend_col_width + 10
        legend_bg_height = (items_per_col * legend_row_height) + 30

        svg_elements.append(
            f'<g opacity="0.95">'
            f'<rect x="{legend_start_x - 5}" y="{legend_start_y - 5}" width="{legend_bg_width}" height="{legend_bg_height}" rx="6" '
            f'fill="white" stroke="#bbb" stroke-width="1" />'
            f'<text x="{legend_start_x}" y="{legend_start_y + 10}" font-family="sans-serif" font-size="12" '
            f'font-weight="700" fill="#333">Legend</text>'
            f"</g>"
        )

        for i, name in enumerate(turn_data["names"]):
            c = get_racer_color(name)
            col_idx = i // items_per_col
            row_idx = i % items_per_col
            x = legend_start_x + (col_idx * legend_col_width)
            y = legend_start_y + 30 + (row_idx * legend_row_height)

            svg_elements.append(
                f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{c}" stroke="#555" stroke-width="1" />'
            )
            svg_elements.append(
                f'<text x="{x + 18}" y="{y}" font-family="sans-serif" font-size="12" '
                f'font-weight="600" fill="#333">{_html.escape(name)}</text>'
            )

        # 3. Racers
        occupancy = {}
        for idx, pos in enumerate(turn_data["positions"]):
            draw_pos = min(pos, len(positions_map) - 1)
            name = turn_data["names"][idx]

            # --- Tooltip ---
            mods = turn_data.get("modifiers", [])
            abils = turn_data.get("abilities", [])
            mod_str = str(mods[idx]) if idx < len(mods) else "[]"
            abil_str = str(abils[idx]) if idx < len(abils) else "[]"

            tooltip_text = (
                f"{name} (ID: {idx})\n"
                f"Pos: {pos} | Tripped: {turn_data['tripped'][idx]}\n"
                f"Abilities: {abil_str}\n"
                f"Modifiers: {mod_str}"
            )

            occupancy.setdefault(draw_pos, []).append(
                {
                    "name": name,
                    "color": get_racer_color(name),
                    "is_current": (idx == turn_data["current_racer"]),
                    "tripped": turn_data["tripped"][idx],
                    "tooltip": tooltip_text,
                }
            )

        for space_idx, racers_here in occupancy.items():
            bx, by, brot = positions_map[space_idx]
            count = len(racers_here)
            if count == 1:
                offsets = [(0, 0)]
            elif count == 2:
                offsets = [(-15, 0), (15, 0)]
            elif count == 3:
                offsets = [(-15, -8), (15, -8), (0, 8)]
            else:
                offsets = [(-15, -8), (15, -8), (-15, 8), (15, 8)]

            for i, racer in enumerate(racers_here):
                if i >= len(offsets):
                    break
                ox, oy = offsets[i]
                rad = math.radians(brot)
                cx = bx + (ox * math.cos(rad) - oy * math.sin(rad))
                cy = by + (ox * math.sin(rad) + oy * math.cos(rad))

                stroke = "yellow" if racer["is_current"] else "white"
                width = "3" if racer["is_current"] else "1.5"

                svg_elements.append(f"<g>")
                svg_elements.append(
                    f'<title>{_html.escape(racer["tooltip"])}</title>'
                )

                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="8" fill="{racer["color"]}" stroke="{stroke}" stroke-width="{width}" />'
                )

                # Add racer name below the circle
                svg_elements.append(
                    f'<text x="{cx}" y="{cy + 20}" font-family="sans-serif" font-size="13" '
                    f'font-weight="900" text-anchor="middle" fill="{racer["color"]}" '
                    f'style="paint-order: stroke; stroke: rgba(255,255,255,0.9); stroke-width: 4px;">'
                    f'{_html.escape(racer["name"])}</text>'
                )

                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{cx}" y="{cy}" dy="4" fill="red" font-weight="bold" text-anchor="middle">X</text>'
                    )

                svg_elements.append(f"</g>")

        # 4. Dice Roll Overlay (TOP RIGHT, Tight layout)
        roll = turn_data.get("last_roll", "-")
        svg_elements.append(
            f'<text x="680" y="50" font-size="40" text-anchor="end" fill="#333">🎲 {roll}</text>'
        )

        return f"""<svg width="700" height="400" style="background:#eef; border:2px solid #ccc; border-radius:8px;">
            <ellipse cx="350" cy="260" rx="150" ry="70" fill="#C8E6C9" stroke="none"/>
            {"".join(svg_elements)}
        </svg>"""
    return (render_game_track,)


@app.cell
def _(mo):
    # --- PERSISTENCE STATE ---
    # We only use this to remember values when the UI refreshes (Add/Remove).
    # We do NOT use this to drive the simulation.
    get_selected_racers, set_selected_racers = mo.state(
        ["Banana", "Centaur", "Magician", "Scoocher"], allow_self_loops=True
    )
    get_racer_to_add, set_racer_to_add = mo.state(None, allow_self_loops=True)

    # Stores the "Last Known" positions to prevent reset on Add/Remove
    get_saved_positions, set_saved_positions = mo.state(
        {"Banana": 0, "Centaur": 0, "Magician": 0, "Scoocher": 0},
        allow_self_loops=True,
    )

    get_use_scripted_dice, set_use_scripted_dice = mo.state(
        False, allow_self_loops=True
    )
    get_dice_rolls_text, set_dice_rolls_text = mo.state("", allow_self_loops=True)
    return (
        get_dice_rolls_text,
        get_racer_to_add,
        get_saved_positions,
        get_selected_racers,
        get_use_scripted_dice,
        set_dice_rolls_text,
        set_racer_to_add,
        set_saved_positions,
        set_selected_racers,
        set_use_scripted_dice,
    )


@app.cell
def _(
    RacerName,
    get_args,
    get_dice_rolls_text,
    get_racer_to_add,
    get_saved_positions,
    get_selected_racers,
    get_use_scripted_dice,
    mo,
    set_dice_rolls_text,
    set_racer_to_add,
    set_saved_positions,
    set_selected_racers,
    set_step_idx,
    set_use_scripted_dice,
):
    # --- UI DEFINITION ---
    AVAILABLE_RACERS = sorted(list(get_args(RacerName)))
    current_roster = get_selected_racers()
    saved_positions = get_saved_positions()

    # 1. Main Controls
    reset_button = mo.ui.button(label="🔄 Reset Simulation", on_click=lambda _: set_step_idx(0),)
    scenario_seed = mo.ui.number(
        start=1, stop=10000, value=42, label="Random Seed", on_change=lambda v: (set_step_idx(0), v)[1],
    )

    use_scripted_dice_ui = mo.ui.checkbox(
        value=get_use_scripted_dice(),
        on_change=lambda v: (set_use_scripted_dice(v), set_step_idx(0))[1],
        label="Use scripted dice",

    )
    dice_rolls_text_ui = mo.ui.text(
        value=get_dice_rolls_text(),
        on_change=lambda v: (set_dice_rolls_text(v), set_step_idx(0))[1],
        label="Dice rolls",
        placeholder="e.g. 4,5,6",
    )

    # 2. Position Inputs — with on_change handlers that update state (reactive)
    # NOTE: this cell should accept `set_step_idx` in its argument list so we can
    # reset the timeline to turn 0 when positions change.


    def _make_pos_on_change(racer_name):
        def _on_change(new_val):
            try:
                v = int(new_val)
            except Exception:
                v = 0
            # update the saved positions state (this will be read by the simulator)
            set_saved_positions(lambda cur: {**cur, racer_name: v})
            # reset the timeline to start (turn 0 / first step)
            try:
                set_step_idx(0)
            except Exception:
                raise ValueError("Attempted to reset turn to 0 but failed.")
            return new_val

        return _on_change


    pos_widget_map = {
        ui_racer: mo.ui.number(
            start=0,
            stop=29,
            value=int(saved_positions.get(ui_racer, 0)),
            label="",
            on_change=_make_pos_on_change(ui_racer),
        )
        for ui_racer in current_roster
    }

    # Keep the dictionary (optional) but we no longer rely on its .value for
    # reactivity — the authoritative source is get_saved_positions()
    all_positions_ui = mo.ui.dictionary(pos_widget_map)


    # 3. Snapshot Logic (The "Glue" for Add/Remove)
    # When we add/remove, we first grab the *current* widget values
    # and save them to state.
    def _snapshot_values(exclude=None):
        return {r: w.value for r, w in pos_widget_map.items() if r != exclude}


    # 4. Remove Buttons
    def _remove_factory(racer_to_remove):
        def _remover(_):
            new_pos = _snapshot_values(exclude=racer_to_remove)
            set_saved_positions(new_pos)
            set_selected_racers(
                lambda cur: [x for x in cur if x != racer_to_remove]
            )
            try:
                set_step_idx(0)
            except Exception:
                raise ValueError("Attempted to reset turn to 0 but failed.")


        return _remover


    rem_buttons = {
        ui_racer: mo.ui.button(
            label="✖",
            on_click=_remove_factory(ui_racer),
            disabled=(len(current_roster) <= 1),
        )
        for ui_racer in current_roster
    }

    # 5. Add Racer Logic
    available_options = [r for r in AVAILABLE_RACERS if r not in current_roster]
    add_racer_dropdown = mo.ui.dropdown(
        options=available_options,
        value=get_racer_to_add(),
        on_change=set_racer_to_add,
        label="Add racer",
    )


    def _add_racer(v):
        r = get_racer_to_add()
        if r and r not in get_selected_racers():
            new_pos = _snapshot_values()
            new_pos[r] = 0  # Default for new racer
            set_saved_positions(new_pos)
            set_selected_racers(lambda cur: cur + [r])
            set_racer_to_add(None)
            try:
                set_step_idx(0)
            except Exception:
                raise ValueError("Attempted to reset turn to 0 but failed.")
        return v


    add_button = mo.ui.button(label="➕ Add", on_click=_add_racer)

    # 6. Layout
    table_rows = []
    for i, ui_racer in enumerate(current_roster):
        w_pos = pos_widget_map[ui_racer]
        w_rem = rem_buttons[ui_racer]
        table_rows.append(f"| {i+1}. {ui_racer} | {w_pos} | {w_rem} |")

    racer_table = mo.md(
        "| Racer | Start Pos | Remove |\n"
        "| :--- | :--- | :---: |\n" + "\n".join(table_rows)
    )
    return (
        add_button,
        add_racer_dropdown,
        all_positions_ui,
        current_roster,
        dice_rolls_text_ui,
        racer_table,
        reset_button,
        scenario_seed,
        use_scripted_dice_ui,
    )


@app.cell
def _(
    add_button,
    add_racer_dropdown,
    dice_rolls_text_ui,
    mo,
    racer_table,
    reset_button,
    scenario_seed,
    use_scripted_dice_ui,
):
    # --- CONFIG DISPLAY ---
    dice_input = dice_rolls_text_ui if use_scripted_dice_ui.value else mo.Html("")

    mo.vstack(
        [
            mo.md("## Configure"),
            mo.hstack([scenario_seed, reset_button], justify="start", gap=2),
            mo.hstack([use_scripted_dice_ui, dice_input], justify="start", gap=2),
            mo.md("### Racers"),
            racer_table,
            mo.hstack([add_racer_dropdown, add_button], justify="start", gap=1),
        ],
        gap=1.25,
    )
    return


@app.cell
def _(
    BOARD_DEFINITIONS,
    Console,
    GameLogHighlighter,
    GameScenario,
    MoveCmdEvent,
    RacerConfig,
    RichHandler,
    RichMarkupFormatter,
    TripCmdEvent,
    WarpCmdEvent,
    all_positions_ui,
    current_roster,
    get_dice_rolls_text,
    get_saved_positions,
    get_use_scripted_dice,
    logging,
    mo,
    re,
    reset_button,
    scenario_seed,
):
    # --- SIMULATION ---
    # Dependencies:
    # 1. all_positions_ui.value -> DIRECT CONNECTION. No state bridge.
    # 2. scenario_seed.value
    # 3. reset_button.value
    # --- REACTIVITY ANCHORS (DO NOT REMOVE) ---
    reset_button.value
    scenario_seed.value
    get_saved_positions()
    get_use_scripted_dice()
    get_dice_rolls_text()


    log_console = Console(
        record=True, width=120, force_terminal=True, color_system="truecolor"
    )
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    log_handler = RichHandler(
        console=log_console,
        markup=True,
        show_path=False,
        show_time=False,
        highlighter=GameLogHighlighter(),
    )
    log_handler.setFormatter(RichMarkupFormatter())
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)

    # DIRECT READ: The .value here is a dictionary of {racer_name: int_value}
    # It updates instantly because 'all_positions_ui' is a mo.ui.dictionary.
    current_pos_values = all_positions_ui.value

    dice_rolls = None
    if get_use_scripted_dice():
        raw = get_dice_rolls_text().strip()
        if raw:
            try:
                dice_rolls = [int(t) for t in re.split(r"[,\s]+", raw) if t]
            except:
                pass

    scenario = GameScenario(
        racers_config=[
            RacerConfig(i, n, start_pos=int(current_pos_values.get(n, 0)))
            for i, n in enumerate(current_roster)
        ],
        dice_rolls=dice_rolls,
        seed=None if dice_rolls else scenario_seed.value,
        board=BOARD_DEFINITIONS["standard"](),
    )

    step_history = []
    turn_map = {}

    VISUAL_EVENTS = (MoveCmdEvent, WarpCmdEvent, TripCmdEvent)
    sim_turn_counter = {"current": 0}


    def capture_snapshot(engine, event_name, is_turn_end=False):
        current_logs_text = log_console.export_text(clear=False)
        log_line_index = max(0, current_logs_text.count("\n") - 1)
        current_logs_html = log_console.export_html(
            clear=False, inline_styles=True, code_format="{code}"
        )

        t_idx = sim_turn_counter["current"]
        last_roll = 0
        if hasattr(engine.state, "roll_state") and engine.state.roll_state:
            last_roll = getattr(engine.state.roll_state, "base_value", 0)
        elif hasattr(engine.state, "last_dice_roll"):
            last_roll = engine.state.last_dice_roll

        snapshot = {
            "global_step_index": len(step_history),
            "turn_index": t_idx,
            "event_name": event_name,
            "positions": [r.position for r in engine.state.racers],
            "tripped": [r.tripped for r in engine.state.racers],
            "last_roll": last_roll,
            "current_racer": engine.state.current_racer_idx,
            "names": [r.name for r in engine.state.racers],
            "modifiers": [
                list(getattr(r, "modifiers", [])) for r in engine.state.racers
            ],
            "abilities": [
                sorted(list(getattr(r, "abilities", set())))
                for r in engine.state.racers
            ],
            "log_html": current_logs_html,
            "log_line_index": log_line_index,
        }

        step_history.append(snapshot)
        if t_idx not in turn_map:
            turn_map[t_idx] = []
        turn_map[t_idx].append(snapshot["global_step_index"])


    def on_event(engine, event):
        if isinstance(event, VISUAL_EVENTS):
            capture_snapshot(engine, event.__class__.__name__)


    if hasattr(scenario.engine, "on_event_processed"):
        scenario.engine.on_event_processed = on_event

    engine = scenario.engine

    capture_snapshot(engine, "InitialState", is_turn_end=False)

    with mo.status.spinner(title="Simulating..."):
        while not engine.state.race_over:
            log_console.export_html(clear=True)
            scenario.run_turn()
            capture_snapshot(engine, "TurnEnd", is_turn_end=True)
            sim_turn_counter["current"] += 1
            if len(step_history) > 1000:
                break

    info_md = mo.md(
        f"✅ **Simulation complete!** {len(current_roster)} racers, {sim_turn_counter['current']} turns"
    )
    return info_md, step_history, turn_map


@app.cell
def _(info_md):
    info_md
    return


@app.cell
def _(mo):
    get_step_idx, set_step_idx = mo.state(0, allow_self_loops=True)
    return get_step_idx, set_step_idx


@app.cell
def _(get_step_idx, mo, set_step_idx, step_history, turn_map):
    # --- NAVIGATION LOGIC ---
    current_step_idx = get_step_idx()

    if not step_history:
        current_data, current_turn_idx, max_s = None, 0, 0
    else:
        current_step_idx = min(max(0, current_step_idx), len(step_history) - 1)
        current_data = step_history[current_step_idx]
        current_data = step_history[current_step_idx]
        current_turn_idx = current_data["turn_index"]
        max_s = len(step_history) - 1

    next_step_val = min(max_s, current_step_idx + 1)
    prev_step_val = max(0, current_step_idx - 1)

    next_turn_target = current_turn_idx + 1
    prev_turn_target = current_turn_idx - 1

    if next_turn_target in turn_map:
        next_turn_step_val = turn_map[next_turn_target][0]
    else:
        next_turn_step_val = current_step_idx

    if prev_turn_target in turn_map:
        prev_turn_step_val = turn_map[prev_turn_target][0]
    else:
        prev_turn_step_val = 0

    btn_prev_turn = mo.ui.button(
        label="◀◀Turn",
        on_click=lambda _: set_step_idx(prev_turn_step_val),
        disabled=(current_turn_idx <= 0),
    )
    btn_next_turn = mo.ui.button(
        label="Turn▶▶",
        on_click=lambda _: set_step_idx(next_turn_step_val),
        disabled=(next_turn_target not in turn_map),
    )
    btn_prev_step = mo.ui.button(
        label="◀ Step",
        on_click=lambda _: set_step_idx(prev_step_val),
        disabled=(current_step_idx <= 0),
    )
    btn_next_step = mo.ui.button(
        label="Step ▶",
        on_click=lambda _: set_step_idx(next_step_val),
        disabled=(current_step_idx >= max_s),
    )


    def on_slider_change(v):
        if v in turn_map:
            set_step_idx(turn_map[v][0])


    nav_max_turn = max(turn_map.keys()) if turn_map else 0
    turn_slider = mo.ui.slider(
        start=0,
        stop=nav_max_turn,
        value=current_turn_idx,
        step=1,
        label="Turn Timeline",
        on_change=on_slider_change,
        full_width=True,
    )
    return (
        btn_next_step,
        btn_next_turn,
        btn_prev_step,
        btn_prev_turn,
        current_data,
        current_turn_idx,
        turn_slider,
    )


@app.cell
def _(
    btn_next_step,
    btn_next_turn,
    btn_prev_step,
    btn_prev_turn,
    current_data,
    current_turn_idx,
    mo,
    step_history,
    turn_slider,
):
    # --- NAV LAYOUT ---
    curr_step = current_data["global_step_index"] if current_data else 0
    tot_steps = len(step_history) if step_history else 0

    status_text = mo.md(
        f"**Turn {current_turn_idx}** (Step {curr_step+1}/{tot_steps})"
    )

    nav_ui = mo.vstack(
        [
            mo.hstack(
                [btn_prev_turn, turn_slider, btn_next_turn],
                justify="center",
                gap=1,
            ),
            mo.hstack(
                [btn_prev_step, status_text, btn_next_step],
                justify="center",
                gap=1,
            ),
        ]
    )
    return (nav_ui,)


@app.cell
def _(current_data, current_turn_idx, mo, step_history, turn_map):
    # --- LOG VIEWER ---
    if not current_data:
        log_ui = mo.md("No logs")
    else:
        container_id = "log-container-main"
        segments = []
        log_max_turn = max(turn_map.keys())

        for t in range(log_max_turn + 1):
            if t not in turn_map:
                continue
            is_active = t == current_turn_idx
            end_of_turn_idx = turn_map[t][-1]
            full_turn_log = step_history[end_of_turn_idx]["log_html"]

            if is_active:
                bg, border, opacity = "#000000", "#00FF00", "1.0"
                lines = full_turn_log.split("\n")
                target_line = current_data["log_line_index"]
                safe_idx = min(len(lines), target_line + 1)
                lines.insert(
                    safe_idx,
                    '<div style="color:red; font-size:10px; border-top:1px dashed red; margin-top:2px; margin-bottom:2px;">▲ CURRENT STEP</div>',
                )
                content_html = "<br>".join(lines)
            else:
                bg, border, opacity = "#1e1e1e", "#333", "0.5"
                content_html = full_turn_log.replace("\n", "<br>")

            segments.append(f"""
            <div id="turn-log-{t}" style="padding:4px; border-left:4px solid {border}; background:{bg}; opacity:{opacity}; border-bottom:1px solid #333;">
                <div style="font-size:9px; color:#666; font-weight:bold;">TURN {t}</div>
                <div class="rich-wrapper">{content_html}</div>
            </div>
            """)

        full_html = "".join(segments)
        scroll_script = f"""<script>try {{const p = window.parent.document; const c = p.getElementById("{container_id}"); const t = p.getElementById("turn-log-{current_turn_idx}"); if(c && t) c.scrollTo({{top: t.offsetTop - c.offsetTop - 20, behavior: 'smooth'}});}} catch(e) {{}}</script>"""

        log_ui = mo.vstack(
            [
                mo.Html(
                    f"""<div id="{container_id}" style="height:600px; overflow-y:auto; background:#1e1e1e; font-family:monospace;">{full_html}</div>"""
                ),
                mo.iframe(scroll_script, width="0", height="0"),
            ]
        )
    return (log_ui,)


@app.cell
def _(
    board_positions,
    current_data,
    log_ui,
    mo,
    nav_ui,
    render_game_track,
    space_colors,
):
    # --- COMPOSITION ---
    if not current_data:
        layout = mo.md("Waiting for simulation...")
    else:
        track_svg = mo.Html(
            render_game_track(current_data, board_positions, space_colors)
        )
        layout = mo.hstack(
            [mo.vstack([nav_ui, track_svg], align="center"), log_ui],
            gap=2,
            align="start",
        )
    layout
    return


@app.cell
def _(all_positions_ui, current_roster, get_saved_positions, mo):
    # --- DEBUG OUTPUT ---
    import json

    debug_info = mo.md(f"""
    ## 🔍 Debug Info

    **Current Roster:** {current_roster}

    **all_positions_ui.value:** 
    ```
    {json.dumps(all_positions_ui.value, indent=2)}
    ```

    **get_saved_positions():**
    ```
    {json.dumps(get_saved_positions(), indent=2)}
    ```

    **Type of all_positions_ui:** {type(all_positions_ui)}

    **Type of all_positions_ui.value:** {type(all_positions_ui.value)}
    """)

    debug_info
    return


if __name__ == "__main__":
    app.run()
