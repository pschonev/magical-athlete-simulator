import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import math
    from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
    from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
    return BOARD_DEFINITIONS, GameScenario, RacerConfig, math, mo


@app.cell
def _(math):
    # Space colors: Green start, alternating grey/white, red finish
    space_colors = ["#4CAF50"] + ["#F5F5F5", "#E0E0E0"] * 14 + ["#F44336"]
    space_colors = space_colors[:30]

    # Fixed colors for specific known names
    racer_colors = {
        "Banana": "#FFD700",  # Gold
        "Centaur": "#8B4513",  # Brown
        "Magician": "#9370DB",  # Purple
        "Scoocher": "#FF6347",  # Tomato
        "Gunk": "#228B22",  # Forest Green
        "HugeBaby": "#FF69B4",  # Hot Pink
        "Copycat": "#4682B4",  # Steel Blue
        "Mermaid": "#00CED1",  # Dark Turquoise
        "Amazon": "#DC143C",  # Crimson
        "Ninja": "#2F4F4F",  # Dark Slate Gray
    }

    # Extended palette for generated/unknown racers
    FALLBACK_PALETTE = [
        "#8A2BE2",
        "#5F9EA0",
        "#D2691E",
        "#FF8C00",
        "#2E8B57",
        "#1E90FF",
        "#FF1493",
        "#9ACD32",
        "#A0522D",
        "#00BFFF",
        "#8B008B",
        "#4B0082",
        "#2F4F4F",
        "#556B2F",
        "#B8860B",
    ]


    def get_racer_color(name):
        if name in racer_colors:
            return racer_colors[name]
        # Deterministic color based on name hash
        try:
            h = hash(name)
            return FALLBACK_PALETTE[(h % len(FALLBACK_PALETTE))]
        except Exception:
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
                x = start_x + dist
                y = start_y
                angle = 0
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (math.pi / 2) - (fraction * math.pi)
                x = right_circle_cx + radius * math.cos(theta_rad)
                y = right_circle_cy + radius * math.sin(theta_rad)
                angle = math.degrees(theta_rad) + 90
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x = (start_x + straight_len) - top_dist
                y = start_y - (2 * radius)
                angle = 180
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (-math.pi / 2) - (fraction * math.pi)
                x = left_circle_cx + radius * math.cos(theta_rad)
                y = left_circle_cy + radius * math.sin(theta_rad)
                angle = math.degrees(theta_rad) + 90

            positions.append((x, y, angle))
        return positions


    board_positions = generate_racetrack_positions(
        num_spaces=30, start_x=120, start_y=350, straight_len=350, radius=100
    )
    return board_positions, get_racer_color, space_colors


@app.cell
def _(mo):
    # Selected racers (drives UI + simulation)
    get_selected_racers, set_selected_racers = mo.state(
        ["Banana", "Centaur", "Magician", "Scoocher"],
        allow_self_loops=True,
    )

    # Dropdown selection state
    get_racer_to_add, set_racer_to_add = mo.state(None, allow_self_loops=True)

    # Start positions
    get_start_positions, set_start_positions = mo.state(
        {
            "Banana": 0,
            "Centaur": 0,
            "Magician": 0,
            "Scoocher": 0,
        },
        allow_self_loops=True,
    )

    # Scripted dice
    get_use_scripted_dice, set_use_scripted_dice = mo.state(
        False, allow_self_loops=True
    )
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
    from typing import get_args
    from magical_athlete_simulator.core.types import RacerName

    AVAILABLE_RACERS = sorted(list(get_args(RacerName)))

    selected_racer_names = get_selected_racers()
    start_positions = get_start_positions()

    reset_button = mo.ui.button(label="🔄 Reset Simulation")
    scenario_seed = mo.ui.number(
        start=1, stop=10000, value=42, label="Random Seed"
    )

    use_scripted_dice = mo.ui.checkbox(
        value=get_use_scripted_dice(),
        on_change=set_use_scripted_dice,
        label="Use scripted dice rolls (overrides seed)",
    )

    dice_rolls_text = mo.ui.text(
        value=get_dice_rolls_text(),
        on_change=set_dice_rolls_text,
        label="Dice rolls:",
        placeholder="e.g. 4,5,6,3,2,4",
    )

    add_racer_dropdown = mo.ui.dropdown(
        options=[r for r in AVAILABLE_RACERS if r not in selected_racer_names],
        value=get_racer_to_add(),
        on_change=set_racer_to_add,
        label="Select racer to add",
        searchable=True,
        allow_select_none=True,
    )


    def _sync_start_positions_for_roster(roster: list[str]):
        def _update(cur: dict[str, int]):
            return {name: int(cur.get(name, 0)) for name in roster}

        set_start_positions(_update)


    def _add_racer(_btn_value):
        racer = get_racer_to_add()
        if racer is None:
            return _btn_value

        def _update_roster(cur: list[str]):
            if racer in cur:
                return cur
            return cur + [racer]

        set_selected_racers(_update_roster)
        _sync_start_positions_for_roster(get_selected_racers())
        set_racer_to_add(None)
        return _btn_value


    add_button = mo.ui.button(label="➕ Add", value=0, on_click=_add_racer)


    def _make_remove_handler(racer_name: str):
        def _remove(_btn_value):
            def _update_roster(cur: list[str]):
                if len(cur) <= 1:
                    return cur
                return [r for r in cur if r != racer_name]

            set_selected_racers(_update_roster)
            _sync_start_positions_for_roster(get_selected_racers())
            return _btn_value

        return _remove


    remove_buttons = {
        racer: mo.ui.button(
            label="✖",
            disabled=len(selected_racer_names) <= 1,
            value=0,
            on_click=_make_remove_handler(racer),
        )
        for racer in selected_racer_names
    }


    def _make_start_pos_handler(racer_name: str):
        def _set_pos(new_value):
            try:
                v = int(new_value)
            except Exception:
                v = 0
            set_start_positions(lambda cur: {**cur, racer_name: v})

        return _set_pos


    start_pos_inputs = {
        racer: mo.ui.number(
            start=0,
            stop=1000,
            step=1,
            value=int(start_positions.get(racer, 0)),
            label="Start pos",
            on_change=_make_start_pos_handler(racer),
        )
        for racer in selected_racer_names
    }
    return (
        add_button,
        add_racer_dropdown,
        dice_rolls_text,
        remove_buttons,
        reset_button,
        scenario_seed,
        selected_racer_names,
        start_pos_inputs,
        use_scripted_dice,
    )


@app.cell
def _(
    add_button,
    add_racer_dropdown,
    dice_rolls_text,
    mo,
    remove_buttons,
    reset_button,
    scenario_seed,
    selected_racer_names,
    start_pos_inputs,
    use_scripted_dice,
):
    racer_list_items = [
        mo.hstack(
            [
                mo.md(f"**{i+1}.** {racer}"),
                mo.hstack([mo.md("Start:"), start_pos_inputs[racer]], gap=1),
                remove_buttons[racer],
            ],
            justify="space-between",
            widths=[7, 5, 1],
        )
        for i, racer in enumerate(selected_racer_names)
    ]

    dice_input = dice_rolls_text if use_scripted_dice.value else mo.Html("")

    mo.vstack(
        [
            mo.md("## Configure Race"),
            mo.hstack([scenario_seed, reset_button], justify="start", gap=2),
            mo.md("### Scripted dice"),
            mo.hstack([use_scripted_dice, dice_input], justify="start", gap=2),
            mo.md("### Selected Racers"),
            mo.vstack(racer_list_items, gap=0.5),
            mo.hstack([add_racer_dropdown, add_button], justify="start", gap=1),
        ],
        gap=1.25,
    )
    return


@app.cell
def _(
    BOARD_DEFINITIONS,
    GameScenario,
    RacerConfig,
    get_dice_rolls_text,
    get_selected_racers,
    get_start_positions,
    get_use_scripted_dice,
    mo,
    reset_button,
    scenario_seed,
):
    import logging
    import re
    from rich.console import Console
    from rich.logging import RichHandler
    from magical_athlete_simulator.engine.logging import (
        RichMarkupFormatter,
        GameLogHighlighter,
    )

    reset_button.value

    # --- LOGGING SETUP FIX ---
    # We attach to the ROOT logger to ensure we catch all library logs.
    log_console = Console(
        record=True, width=120, force_terminal=True, color_system="truecolor"
    )

    # Clear existing handlers to prevent duplicates
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

    _selected_racer_names = get_selected_racers()
    _start_positions = get_start_positions()

    dice_rolls = None
    dice_error = None
    if get_use_scripted_dice():
        raw = (get_dice_rolls_text() or "").strip()
        if raw == "":
            dice_error = "Scripted dice enabled, but no dice rolls provided."
        else:
            try:
                tokens = [t for t in re.split(r"[,\s]+", raw) if t]
                parsed = [int(t) for t in tokens]
                if any(r < 1 or r > 6 for r in parsed):
                    dice_error = "Dice rolls must be integers between 1 and 6."
                else:
                    dice_rolls = parsed
            except Exception:
                dice_error = "Could not parse dice rolls. Use integers separated by commas/spaces/newlines."

    if dice_error is not None:
        mo.md(
            f"⚠️ **Dice-roll input error:** {dice_error}\n\nFalling back to seed-based randomness."
        )

    scenario = GameScenario(
        racers_config=[
            RacerConfig(
                idx=i,
                name=name,
                start_pos=int(_start_positions.get(name, 0)),
            )
            for i, name in enumerate(_selected_racer_names)
        ],
        dice_rolls=dice_rolls,
        seed=None if dice_rolls is not None else scenario_seed.value,
        board=BOARD_DEFINITIONS["standard"](),
    )

    engine = scenario.engine
    game_history = []

    with mo.status.spinner(
        title="Simulating game...", subtitle="Running turns", remove_on_exit=True
    ):
        while not engine.state.race_over:
            snapshot = {
                "turn": len(game_history),
                "positions": [r.position for r in engine.state.racers],
                "names": [r.name for r in engine.state.racers],
                "tripped": [r.tripped for r in engine.state.racers],
                "current_racer": engine.state.current_racer_idx,
                "victory_points": [r.victory_points for r in engine.state.racers],
                "main_move_consumed": [
                    r.main_move_consumed for r in engine.state.racers
                ],
                "reroll_count": [r.reroll_count for r in engine.state.racers],
                "finish_position": [
                    r.finish_position for r in engine.state.racers
                ],
                "eliminated": [r.eliminated for r in engine.state.racers],
                "modifiers": [
                    list(getattr(r, "modifiers", [])) for r in engine.state.racers
                ],
                "abilities": [
                    sorted(list(getattr(r, "abilities", set())))
                    for r in engine.state.racers
                ],
            }

            # Clear buffer before running turn so we only capture NEW logs
            log_console.clear()

            scenario.run_turn()

            # Export HTML and CLEAR the buffer so the next turn starts empty
            snapshot["log_html"] = log_console.export_html(
                clear=True,  # <--- CHANGED: Set this to True to empty the buffer
                inline_styles=True,
                code_format="{code}",
            )

            game_history.append(snapshot)


            if len(game_history) > 200:
                break

    total_turns = len(game_history)
    mo.md(
        f"✅ **Simulation complete!** {len(_selected_racer_names)} racers, {total_turns} turns"
    )
    return (game_history,)


@app.cell
def _(game_history, mo):
    turn_slider = mo.ui.slider(
        start=0,
        stop=max(0, len(game_history) - 1),
        step=1,
        label="Turn to View",
        value=0,
    )
    return (turn_slider,)


@app.cell
def _(game_history, turn_slider):
    current_turn_data = (
        game_history[turn_slider.value]
        if turn_slider.value < len(game_history)
        else None
    )
    return (current_turn_data,)


@app.cell
def _(turn_slider):
    turn_slider
    return


@app.cell
def _(get_racer_color, math):
    def render_game_track(turn_data, positions_map, colors_map):
        import html as _html
        import json as _json

        if not turn_data:
            return "<p>No game data yet. Move the slider.</p>"

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

        # --- LEGEND FIX: Grid Layout expanding to the RIGHT ---
        legend_start_x = 20
        legend_start_y = 20
        legend_col_width = 110
        legend_row_height = 20
        items_per_col = 4  # Keep columns short so they don't hit the track

        # Calculate total width needed
        num_items = len(turn_data["names"])
        num_cols = math.ceil(num_items / items_per_col)
        legend_bg_width = num_cols * legend_col_width + 10
        legend_bg_height = (items_per_col * legend_row_height) + 30

        # Legend Background
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

            # Grid math
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

        # Group racers
        occupancy = {}
        max_space = len(positions_map) - 1

        for idx, pos in enumerate(turn_data["positions"]):
            draw_pos = min(pos, max_space)
            name = turn_data["names"][idx]
            occupancy.setdefault(draw_pos, []).append(
                {
                    "idx": idx,
                    "name": name,
                    "color": get_racer_color(name),
                    "pos": pos,
                    "tripped": turn_data["tripped"][idx],
                    "is_current": idx == turn_data["current_racer"],
                    "victory_points": turn_data["victory_points"][idx],
                    "main_move_consumed": turn_data["main_move_consumed"][idx],
                    "reroll_count": turn_data["reroll_count"][idx],
                    "finish_position": turn_data["finish_position"][idx],
                    "eliminated": turn_data["eliminated"][idx],
                    "modifiers": [
                        str(m) for m in (turn_data["modifiers"][idx] or [])
                    ],
                    "abilities": [
                        str(a) for a in (turn_data["abilities"][idx] or [])
                    ],
                }
            )

        # Draw racers
        for space_idx, racers_here in occupancy.items():
            bx, by, brot = positions_map[space_idx]
            count = len(racers_here)

            if count == 1:
                offsets = [(0, 0)]
            elif count == 2:
                offsets = [(-15, 0), (15, 0)]
            elif count == 3:
                offsets = [(-15, -8), (15, -8), (0, 8)]
            elif count == 4:
                offsets = [(-15, -8), (15, -8), (-15, 8), (15, 8)]
            else:
                offsets = [(-18, -8), (18, -8), (0, 0), (-18, 8), (18, 8)]

            for i, racer in enumerate(racers_here):
                if i >= len(offsets):
                    break
                ox, oy = offsets[i]

                rad = math.radians(brot)
                rot_ox = ox * math.cos(rad) - oy * math.sin(rad)
                rot_oy = ox * math.sin(rad) + oy * math.cos(rad)

                cx = bx + rot_ox
                cy = by + rot_oy

                is_current = racer["is_current"]
                stroke_color = "yellow" if is_current else "white"
                stroke_width = "2.5" if is_current else "1.5"

                # --- TOOLTIP FIX: Standard SVG <title> ---
                tooltip_text = (
                    f"{racer['name']} (ID: {racer['idx']})\n"
                    f"Pos: {racer['pos']} | Finish: {racer['finish_position']}\n"
                    f"VP: {racer['victory_points']} | Rerolls: {racer['reroll_count']}\n"
                    f"Tripped: {racer['tripped']} | Elim: {racer['eliminated']}\n"
                    f"Abilities: {racer['abilities']}\n"
                    f"Modifiers: {racer['modifiers']}"
                )

                svg_elements.append(
                    f'<g>'
                    f'<title>{_html.escape(tooltip_text)}</title>'  # Native tooltip
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" '
                    f'fill="{racer["color"]}" stroke="{stroke_color}" stroke-width="{stroke_width}" />'
                    f'<text x="{cx:.1f}" y="{cy + 20:.1f}" font-family="sans-serif" font-size="13" '
                    f'font-weight="900" text-anchor="middle" fill="{racer["color"]}" '
                    f'style="paint-order: stroke; stroke: rgba(255,255,255,0.9); stroke-width: 4px;">'
                    f'{_html.escape(racer["name"])}</text>'
                    f'</g>'
                )

                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" '
                        f'font-size="16" font-weight="bold" fill="red" text-anchor="middle">X</text>'
                    )

        return f"""
        <div style="position: relative; width: 700px;">
          <svg class="track-svg" width="700" height="520"
               style="background:#eef; border:2px solid #ccc; border-radius:8px;">
              <ellipse cx="350" cy="260" rx="150" ry="70" fill="#C8E6C9" stroke="none" />
              {"".join(svg_elements)}
          </svg>
        </div>
        """
    return (render_game_track,)


@app.cell
def _(
    board_positions,
    current_turn_data,
    log_ui,
    mo,
    render_game_track,
    space_colors,
):
    mo.hstack(
        [
            mo.Html(
                render_game_track(current_turn_data, board_positions, space_colors)
            ),
            log_ui,
        ],
        gap=3
    )
    return


@app.cell
def _(game_history, mo, turn_slider):
    # --- FULL LOG VIEWER ---
    if not game_history:
        log_ui = mo.md("_No logs available yet._")
    else:
        current_idx = turn_slider.value

        container_id = "full-log-container-stable"
        target_id_prefix = "turn-log-"

        # 1. Build Segments
        log_segments = []
        for i, _snapshot in enumerate(game_history):
            raw_html = _snapshot.get("log_html", "").strip()
            if not raw_html: continue

            # --- CRITICAL FIX ---
            # Rich outputs newlines (\n) which browsers treat as whitespace.
            # We replace them with <br> to FORCE a visual line break.
            # We also ensure we don't break the container's pre-wrap logic.
            html_content = raw_html.replace("\n", "<br>")

            is_active = (i == current_idx)

            # --- HIGHLIGHT LOGIC ---
            if is_active:
                bg_color = "#000000"  # Pure black for active
                border_color = "#00FF00" 
                text_color = "#ffffff"
                opacity = "1.0"
            else:
                bg_color = "#1e1e1e"
                border_color = "#333"
                text_color = "#888888" 
                opacity = "0.6" 

            segment_id = f"{target_id_prefix}{i}"

            segment = f"""
            <div id="{segment_id}" class="log-segment" style="
                padding: 4px 8px;
                border-left: 4px solid {border_color};
                background: {bg_color};
                color: {text_color};
                opacity: {opacity};
                border-bottom: 1px solid #333;
                transition: background 0.2s, border-color 0.2s, opacity 0.2s;
            ">
                <div style="
                    font-size: 9px;
                    color: #666;
                    font-family: sans-serif;
                    text-transform: uppercase;
                    font-weight: bold;
                    margin-bottom: 2px;
                ">
                    Turn {i} • {_snapshot['names'][_snapshot['current_racer']]}
                </div>

                <div class="rich-wrapper">
                    {html_content}
                </div>
            </div>
            """
            log_segments.append(segment)

        full_log_html = "".join(log_segments)

        # 2. Render Container
        visual_log = mo.Html(f'''
            <div id="{container_id}" style="
                height: 800px; 
                overflow-y: auto; 
                background: #1e1e1e; 
                border-radius: 6px; 
                border: 1px solid #444; 
                font-family: monospace; 
                font-size: 13px;
                scroll-behavior: smooth; 
            ">
                <style>
                    /* Kill default PRE margins to fix the "huge gap" */
                    #{container_id} pre {{
                        margin: 0 !important;
                        padding: 0 !important;
                        white-space: normal !important; /* Allow <br> to work, don't rely on \n */
                        font-family: inherit !important;
                    }}

                    /* Ensure spans behave like inline text so <br> works naturally */
                    #{container_id} .r1 {{
                        display: inline;
                    }}

                    /* Zero out code block margins too */
                    #{container_id} code {{
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                </style>
                {full_log_html}
            </div>
        ''')

        # 3. Scroll Controller (Unchanged)
        scroll_script = f"""
        <script>
            try {{
                const parentDoc = window.parent.document;
                const container = parentDoc.getElementById("{container_id}");
                const target = parentDoc.getElementById("{target_id_prefix}{current_idx}");

                if (container && target) {{
                    const topPos = target.offsetTop - container.offsetTop;
                    container.scrollTo({{
                        top: topPos - 40,
                        behavior: 'smooth'
                    }});
                }}
            }} catch (e) {{
                console.error("Scroll script error:", e);
            }}
        </script>
        """

        controller = mo.iframe(scroll_script, width="0px", height="0px")
        log_ui = mo.vstack([visual_log, controller])
    return (log_ui,)


@app.cell
def _(current_turn_data, mo):
    if current_turn_data:
        status_md = f"""
        ## Turn {current_turn_data['turn']} Summary
        **Current Racer:** {current_turn_data['names'][current_turn_data['current_racer']]}
        | Racer | Position | Status |
        |-------|----------|--------|
        """
        for idx, name in enumerate(current_turn_data["names"]):
            status = (
                "🔴 Tripped" if current_turn_data["tripped"][idx] else "✅ Active"
            )
            status_md += (
                f"| {name} | {current_turn_data['positions'][idx]} | {status} |\n"
            )

        mo.md(status_md)
    else:
        mo.md("_Start the game by moving the slider._")
    return


if __name__ == "__main__":
    app.run()
