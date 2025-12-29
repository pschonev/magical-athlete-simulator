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
        ContextFilter
    )
    from magical_athlete_simulator.core.types import RacerName
    from magical_athlete_simulator.core.events import (
        MoveCmdEvent,
        WarpCmdEvent,
        TripCmdEvent,
        PerformMainRollEvent,
        TurnStartEvent
    )
    return (
        BOARD_DEFINITIONS,
        Console,
        GameLogHighlighter,
        GameScenario,
        MoveCmdEvent,
        PerformMainRollEvent,
        RacerConfig,
        RacerName,
        RichHandler,
        RichMarkupFormatter,
        TripCmdEvent,
        TurnStartEvent,
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
        "Banana": "#FFD700", "Centaur": "#8B4513", "Magician": "#9370DB", 
        "Scoocher": "#FF6347", "Gunk": "#228B22", "HugeBaby": "#FF69B4", 
        "Copycat": "#4682B4", "Mermaid": "#00CED1", "Amazon": "#DC143C", 
        "Ninja": "#2F4F4F",
    }

    FALLBACK_PALETTE = ["#8A2BE2", "#5F9EA0", "#D2691E", "#FF8C00", "#2E8B57", "#1E90FF"]

    def get_racer_color(name):
        if name in racer_colors: return racer_colors[name]
        try: return FALLBACK_PALETTE[(hash(name) % len(FALLBACK_PALETTE))]
        except: return "#888888"

    def generate_racetrack_positions(num_spaces, start_x, start_y, straight_len, radius):
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
                x, y, angle = (start_x + straight_len) - top_dist, start_y - (2 * radius), 180
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
        if not turn_data: return "<p>No Data</p>"

        svg_elements = []
        rw, rh = 50, 30

        # Track spaces
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

        # Racers
        occupancy = {}
        for idx, pos in enumerate(turn_data["positions"]):
            draw_pos = min(pos, len(positions_map)-1)
            name = turn_data["names"][idx]
            occupancy.setdefault(draw_pos, []).append({
                "name": name, 
                "color": get_racer_color(name),
                "is_current": (idx == turn_data["current_racer"]),
                "tripped": turn_data["tripped"][idx]
            })

        for space_idx, racers_here in occupancy.items():
            bx, by, brot = positions_map[space_idx]
            count = len(racers_here)
            if count == 1: offsets = [(0, 0)]
            elif count == 2: offsets = [(-15, 0), (15, 0)]
            elif count == 3: offsets = [(-15, -8), (15, -8), (0, 8)]
            else: offsets = [(-15, -8), (15, -8), (-15, 8), (15, 8)]

            for i, racer in enumerate(racers_here):
                if i >= len(offsets): break
                ox, oy = offsets[i]
                rad = math.radians(brot)
                cx = bx + (ox * math.cos(rad) - oy * math.sin(rad))
                cy = by + (ox * math.sin(rad) + oy * math.cos(rad))

                stroke = "yellow" if racer["is_current"] else "white"
                width = "3" if racer["is_current"] else "1.5"

                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="8" fill="{racer["color"]}" stroke="{stroke}" stroke-width="{width}" />'
                )
                if racer["tripped"]:
                    svg_elements.append(f'<text x="{cx}" y="{cy}" dy="4" fill="red" font-weight="bold" text-anchor="middle">X</text>')

        return f"""<svg width="700" height="520" style="background:#eef; border:2px solid #ccc; border-radius:8px;">
            <ellipse cx="350" cy="260" rx="150" ry="70" fill="#C8E6C9" stroke="none"/>
            {"".join(svg_elements)}
        </svg>"""

    return (render_game_track,)


@app.cell
def _(mo):
    # --- CONFIG STATE ---
    # allow_self_loops needed for UI interaction
    get_selected_racers, set_selected_racers = mo.state(["Banana", "Centaur", "Magician", "Scoocher"], allow_self_loops=True)
    get_racer_to_add, set_racer_to_add = mo.state(None, allow_self_loops=True)
    get_start_positions, set_start_positions = mo.state(
        {"Banana": 0, "Centaur": 0, "Magician": 0, "Scoocher": 0}, allow_self_loops=True
    )
    get_use_scripted_dice, set_use_scripted_dice = mo.state(False, allow_self_loops=True)
    get_dice_rolls_text, set_dice_rolls_text = mo.state("", allow_self_loops=True)
    return (
        get_dice_rolls_text,
        get_racer_to_add,
        get_selected_racers,
        get_start_positions,
        get_use_scripted_dice,
        set_dice_rolls_text,
        set_racer_to_add,
        set_selected_racers,
        set_start_positions,
        set_use_scripted_dice,
    )


@app.cell
def _(
    RacerName,
    get_args,
    get_dice_rolls_text,
    get_racer_to_add,
    get_selected_racers,
    get_start_positions,
    get_use_scripted_dice,
    mo,
    set_dice_rolls_text,
    set_racer_to_add,
    set_selected_racers,
    set_start_positions,
    set_use_scripted_dice,
):
    # --- CONFIG UI DEFINITION ---
    AVAILABLE_RACERS = sorted(list(get_args(RacerName)))

    reset_button = mo.ui.button(label="🔄 Reset Simulation")
    scenario_seed = mo.ui.number(start=1, stop=10000, value=42, label="Random Seed")

    use_scripted_dice_ui = mo.ui.checkbox(
        value=get_use_scripted_dice(), on_change=set_use_scripted_dice, 
        label="Use scripted dice"
    )
    dice_rolls_text_ui = mo.ui.text(
        value=get_dice_rolls_text(), on_change=set_dice_rolls_text, 
        label="Dice rolls", placeholder="e.g. 4,5,6"
    )

    # Racer Selection Logic
    current_roster = get_selected_racers()
    available_options = [r for r in AVAILABLE_RACERS if r not in current_roster]

    add_racer_dropdown = mo.ui.dropdown(
        options=available_options,
        value=get_racer_to_add(), on_change=set_racer_to_add, label="Add racer"
    )

    def _add_racer(v):
        r = get_racer_to_add()
        if r and r not in get_selected_racers():
            new_roster = get_selected_racers() + [r]
            set_selected_racers(new_roster)
            cur_pos = get_start_positions()
            set_start_positions({n: int(cur_pos.get(n, 0)) for n in new_roster})
            set_racer_to_add(None)
        return v

    add_button = mo.ui.button(label="➕", on_click=_add_racer)

    # We need to define closure factories to properly capture the loop variable 'r'
    def _remover_factory(name):
        def _remover(_):
            new_list = [x for x in get_selected_racers() if x != name]
            set_selected_racers(new_list)
        return _remover

    def _pos_setter_factory(name):
        def _pos_setter(v):
            current_map = get_start_positions().copy()
            current_map[name] = int(v)
            set_start_positions(current_map)
        return _pos_setter

    racer_list_items = []
    for i, r in enumerate(current_roster):
        pos_val = int(get_start_positions().get(r, 0))
        pos_input = mo.ui.number(
            start=0, value=pos_val, label="Pos", 
            on_change=_pos_setter_factory(r)
        )
        rem_btn = mo.ui.button(
            label="✖", 
            on_click=_remover_factory(r),
            disabled=(len(current_roster) <= 1) # Prevent empty roster
        )
        racer_list_items.append(
            mo.hstack([mo.md(f"**{i+1}.** {r}"), pos_input, rem_btn], justify="space-between")
        )
    return (
        add_button,
        add_racer_dropdown,
        dice_rolls_text_ui,
        racer_list_items,
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
    racer_list_items,
    reset_button,
    scenario_seed,
    use_scripted_dice_ui,
):
    # --- CONFIG LAYOUT ---
    dice_input = dice_rolls_text_ui if use_scripted_dice_ui.value else mo.Html("")

    config_ui = mo.vstack([
        mo.md("## Configure"),
        mo.hstack([scenario_seed, reset_button]),
        mo.hstack([use_scripted_dice_ui, dice_input]),
        mo.md("### Racers"),
        mo.vstack(racer_list_items),
        mo.hstack([add_racer_dropdown, add_button])
    ], gap=1)

    config_ui
    return


@app.cell
def _(
    BOARD_DEFINITIONS,
    Console,
    GameLogHighlighter,
    GameScenario,
    MoveCmdEvent,
    PerformMainRollEvent,
    RacerConfig,
    RichHandler,
    RichMarkupFormatter,
    TripCmdEvent,
    TurnStartEvent,
    WarpCmdEvent,
    get_dice_rolls_text,
    get_selected_racers,
    get_start_positions,
    get_use_scripted_dice,
    logging,
    mo,
    re,
    reset_button,
    scenario_seed,
):
    # --- SIMULATION BACKEND ---
    reset_button.value 

    log_console = Console(record=True, width=120, force_terminal=True, color_system="truecolor")
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]: root_logger.removeHandler(h)

    log_handler = RichHandler(console=log_console, markup=True, show_path=False, show_time=False, highlighter=GameLogHighlighter())
    log_handler.setFormatter(RichMarkupFormatter())
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)

    sel_racers = get_selected_racers()
    start_pos = get_start_positions()
    dice_rolls = None

    if get_use_scripted_dice():
        raw = get_dice_rolls_text().strip()
        if raw:
            try: dice_rolls = [int(t) for t in re.split(r"[,\s]+", raw) if t]
            except: pass

    scenario = GameScenario(
        racers_config=[RacerConfig(i, n, int(start_pos.get(n, 0))) for i, n in enumerate(sel_racers)],
        dice_rolls=dice_rolls,
        seed=None if dice_rolls else scenario_seed.value,
        board=BOARD_DEFINITIONS["standard"]()
    )

    step_history = []
    turn_map = {} 

    VISUAL_EVENTS = (MoveCmdEvent, WarpCmdEvent, TripCmdEvent, PerformMainRollEvent, TurnStartEvent)

    sim_turn_counter = {"current": 0}

    def capture_snapshot(engine, event_name, is_turn_end=False):
        current_logs_text = log_console.export_text(clear=False)
        log_line_index = max(0, current_logs_text.count('\n') - 1)
        current_logs_html = log_console.export_html(clear=False, inline_styles=True, code_format="{code}")

        t_idx = sim_turn_counter["current"]

        last_roll = 0
        if hasattr(engine.state, 'roll_state') and engine.state.roll_state:
             last_roll = getattr(engine.state.roll_state, 'base_value', 0)
        elif hasattr(engine.state, 'last_dice_roll'):
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
            "log_html": current_logs_html,
            "log_line_index": log_line_index,
        }

        step_history.append(snapshot)
        if t_idx not in turn_map: turn_map[t_idx] = []
        turn_map[t_idx].append(snapshot["global_step_index"])

    def on_event(engine, event):
        if isinstance(event, VISUAL_EVENTS):
            capture_snapshot(engine, event.__class__.__name__)

    if hasattr(scenario.engine, 'on_event_processed'):
        scenario.engine.on_event_processed = on_event

    engine = scenario.engine
    with mo.status.spinner(title="Simulating..."):
        while not engine.state.race_over:
            log_console.clear() 
            scenario.run_turn()

            capture_snapshot(engine, "TurnEnd", is_turn_end=True)
            scenario.engine._advance_turn()

            sim_turn_counter["current"] += 1

            if len(step_history) > 1000: break

    # --- INFO BOX ---
    info_md = mo.md(f"""
    ✅ **Simulation complete!**
    - **Racers:** {len(sel_racers)}
    - **Turns:** {sim_turn_counter["current"]}
    - **Total Steps:** {len(step_history)}
    """)
    return info_md, step_history, turn_map


@app.cell
def _(info_md):
    # Display simulation summary
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
        label="⏪ Turn", 
        on_click=lambda _: set_step_idx(prev_turn_step_val),
        disabled=(current_turn_idx <= 0)
    )
    btn_next_turn = mo.ui.button(
        label="Turn ⏩", 
        on_click=lambda _: set_step_idx(next_turn_step_val),
        disabled=(next_turn_target not in turn_map)
    )

    btn_prev_step = mo.ui.button(
        label="◀ Step", 
        on_click=lambda _: set_step_idx(prev_step_val),
        disabled=(current_step_idx <= 0)
    )
    btn_next_step = mo.ui.button(
        label="Step ▶", 
        on_click=lambda _: set_step_idx(next_step_val),
        disabled=(current_step_idx >= max_s)
    )

    def on_slider_change(v):
        if v in turn_map:
            set_step_idx(turn_map[v][0])

    nav_max_turn = max(turn_map.keys()) if turn_map else 0
    turn_slider = mo.ui.slider(
        start=0, stop=nav_max_turn, value=current_turn_idx, step=1, 
        label="Turn Timeline", on_change=on_slider_change, full_width=True
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

    status_text = mo.md(f"**Turn {current_turn_idx}** (Step {curr_step+1}/{tot_steps})")

    nav_ui = mo.vstack([
        mo.hstack([btn_prev_turn, turn_slider, btn_next_turn], justify="center", gap=1),
        mo.hstack([btn_prev_step, status_text, btn_next_step], justify="center", gap=1)
    ])

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
            if t not in turn_map: continue

            is_active = (t == current_turn_idx)
            if is_active:
                raw_html = current_data["log_html"]
                bg, border, opacity = "#000000", "#00FF00", "1.0"
                marker = '<div style="color:red; font-size:10px; border-top:1px dashed red; margin-top:4px;">▲ CURRENT STATE</div>'

                # FIX: explicit replace of newline char with <br> tag
                content_html = raw_html.replace("\n", "<br>") + marker
            else:
                end_idx = turn_map[t][-1]
                raw_html = step_history[end_idx]["log_html"]
                bg, border, opacity = "#1e1e1e", "#333", "0.5"
                content_html = raw_html.replace("\n", "<br>")

            segments.append(f'''
            <div id="turn-log-{t}" style="padding:4px; border-left:4px solid {border}; background:{bg}; opacity:{opacity}; border-bottom:1px solid #333;">
                <div style="font-size:9px; color:#666; font-weight:bold;">TURN {t}</div>
                <div class="rich-wrapper">{content_html}</div>
            </div>
            ''')

        full_html = "".join(segments)

        scroll_script = f"""
        <script>
            try {{
                const p = window.parent.document;
                const c = p.getElementById("{container_id}");
                const t = p.getElementById("turn-log-{current_turn_idx}");
                if(c && t) c.scrollTo({{top: t.offsetTop - c.offsetTop - 20, behavior: 'smooth'}});
            }} catch(e) {{}}
        </script>
        """

        log_ui = mo.vstack([
            mo.Html(f'''
            <div id="{container_id}" style="height:600px; overflow-y:auto; background:#1e1e1e; font-family:monospace;">
                <style>
                    #{container_id} pre {{ margin:0 !important; white-space:normal !important; }}
                    #{container_id} .r1 {{ display:inline; }}
                </style>
                {full_html}
            </div>
            '''),
            mo.iframe(scroll_script, width="0", height="0")
        ])
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
        roll = current_data.get("last_roll", "-")
        dice_ui = mo.md(f"""
        <div style="text-align:center; padding:10px; background:#f0f0f0; border-radius:8px; margin-bottom:10px;">
            <span style="font-size:20px;">🎲 Roll: <strong>{roll}</strong></span>
        </div>
        """)

        track_svg = mo.Html(render_game_track(current_data, board_positions, space_colors))

        layout = mo.hstack([
            mo.vstack([nav_ui, dice_ui, track_svg], align="center"),
            log_ui
        ], gap=2, align="start")

    layout
    return


if __name__ == "__main__":
    app.run()
