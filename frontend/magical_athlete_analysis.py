import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
def _():
    import logging
    import math
    import re
    from typing import get_args

    import altair as alt
    import marimo as mo
    from rich.console import Console
    from rich.logging import RichHandler

    from magical_athlete_simulator.core.events import (
        MoveCmdEvent,
        TripCmdEvent,
        WarpCmdEvent,
    )
    from magical_athlete_simulator.core.types import RacerName
    from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
    from magical_athlete_simulator.engine.logging import (
        GameLogHighlighter,
        RichMarkupFormatter,
    )

    # Imports
    from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
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
        alt,
        get_args,
        logging,
        math,
        mo,
        re,
    )


@app.cell
def _(mo):
    import polars as pl
    from pathlib import Path

    reload_data_btn = mo.ui.button(label="⟳ Reload Data")

    results_folder_browser = mo.ui.file_browser(
        selection_mode="directory",
        label="Select Results Folder",
        initial_path="results",
    )
    return Path, pl, reload_data_btn, results_folder_browser


@app.cell
def _(Path, pl, reload_data_btn, results_folder_browser):
    reload_data_btn.value

    # 1. Determine the Base Folder as a Path object
    if results_folder_browser.value:
        base_folder = Path(results_folder_browser.value[0].path)
    else:
        base_folder = Path("results")

    # 2. Construct Paths using the slash operator
    path_races = base_folder / "races.parquet"
    path_res = base_folder / "racer_results.parquet"
    path_positions = base_folder / "race_positions.parquet"

    # 3. Load Data
    try:
        if not path_races.exists() or not path_res.exists():
            raise FileNotFoundError(
                f"Folder '{base_folder}' must contain 'races.parquet' and 'racer_results.parquet'"
            )

        df_racer_results = pl.read_parquet(path_res)
        df_races = pl.read_parquet(path_races)
        df_positions = pl.read_parquet(path_positions)
        load_status = f"✅ Loaded from: `{base_folder}`"
    except Exception as e:
        df_racer_results = pl.DataFrame()
        df_races = pl.DataFrame()
        df_positions = pl.DataFrame()
        load_status = f"❌ Error: {str(e)}"
    return df_positions, df_racer_results, df_races, load_status


@app.cell
def _(df_racer_results, df_races, mo, pl):
    HASH_COL = "config_hash"

    racer_results_table = mo.ui.table(
        df_racer_results.select(pl.all().exclude(HASH_COL), pl.col(HASH_COL)),
        selection="single",
        label="Racer Results",
    )

    races_table = mo.ui.table(
        df_races.select(pl.all().exclude(HASH_COL), pl.col(HASH_COL)),
        selection="single",
        label="Races",
    )
    return racer_results_table, races_table


@app.cell
def _(math):
    # --- CONSTANTS ---
    NUM_TILES = 31  # 0..30 (30 is the finish tile)

    space_colors = (
        ["#4CAF50"]
        + ["#F5F5F5", "#E0E0E0"] * ((NUM_TILES - 2) // 2)
        + ["#F5F5F5"] * (NUM_TILES % 2)
        + ["#F44336"]
    )
    space_colors = space_colors[:NUM_TILES]

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

    board_positions = generate_racetrack_positions(NUM_TILES, 120, 350, 350, 100)
    return board_positions, get_racer_color, space_colors


@app.cell
def _(StepSnapshot, get_racer_color, math):
    # --- RENDERER ---
    def render_game_track(turn_data: StepSnapshot, positions_map, colors_map):
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

        num_items = len(turn_data.names)
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

        for i, name in enumerate(turn_data.names):
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
        for idx, pos in enumerate(turn_data.positions):
            draw_pos = min(pos, len(positions_map) - 1)
            name = turn_data.names[idx]

            # --- Tooltip ---
            mods = turn_data.modifiers
            abils = turn_data.abilities
            mod_str = str(mods[idx]) if idx < len(mods) else "[]"
            abil_str = str(abils[idx]) if idx < len(abils) else "[]"

            tooltip_text = (
                f"{name} (ID: {idx}) - VP: {turn_data.vp[idx]}\n"
                f"Pos: {pos} | Tripped: {turn_data.tripped[idx]}\n"
                f"Abilities: {abil_str}\n"
                f"Modifiers: {mod_str}"
            )

            occupancy.setdefault(draw_pos, []).append(
                {
                    "name": name,
                    "color": get_racer_color(name),
                    "is_current": (idx == turn_data.current_racer),
                    "tripped": turn_data.tripped[idx],
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
                svg_elements.append(f"<title>{_html.escape(racer['tooltip'])}</title>")

                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="8" fill="{racer["color"]}" stroke="{stroke}" stroke-width="{width}" />'
                )

                # Add racer name below the circle
                svg_elements.append(
                    f'<text x="{cx}" y="{cy + 20}" font-family="sans-serif" font-size="13" '
                    f'font-weight="900" text-anchor="middle" fill="{racer["color"]}" '
                    f'style="paint-order: stroke; stroke: rgba(255,255,255,0.9); stroke-width: 4px;">'
                    f"{_html.escape(racer['name'])}</text>"
                )

                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{cx}" y="{cy}" dy="4" fill="red" font-weight="bold" text-anchor="middle">X</text>'
                    )

                svg_elements.append(f"</g>")

        # 4. Dice Roll Overlay (TOP RIGHT, Tight layout)
        roll = turn_data.last_roll
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
    get_selected_racers, set_selected_racers = mo.state(
        ["Banana", "Centaur", "Magician", "Scoocher"], allow_self_loops=True
    )
    get_racer_to_add, set_racer_to_add = mo.state(None, allow_self_loops=True)

    get_saved_positions, set_saved_positions = mo.state(
        {"Banana": 0, "Centaur": 0, "Magician": 0, "Scoocher": 0},
        allow_self_loops=True,
    )

    get_use_scripted_dice, set_use_scripted_dice = mo.state(
        False, allow_self_loops=False
    )
    get_dice_rolls_text, set_dice_rolls_text = mo.state("", allow_self_loops=False)

    get_debug_mode, set_debug_mode = mo.state(False, allow_self_loops=True)

    # --- NEW STATES FOR CONFIG LOADING ---
    get_seed, set_seed = mo.state(42, allow_self_loops=True)
    get_board, set_board = mo.state("standard", allow_self_loops=True)

    # Track the last seen selection for EACH table to prevent fighting/loops
    get_last_race_hash, set_last_race_hash = mo.state(None, allow_self_loops=True)
    get_last_result_hash, set_last_result_hash = mo.state(None, allow_self_loops=True)
    return (
        get_board,
        get_debug_mode,
        get_dice_rolls_text,
        get_last_race_hash,
        get_last_result_hash,
        get_racer_to_add,
        get_saved_positions,
        get_seed,
        get_selected_racers,
        get_use_scripted_dice,
        set_board,
        set_debug_mode,
        set_dice_rolls_text,
        set_last_race_hash,
        set_last_result_hash,
        set_racer_to_add,
        set_saved_positions,
        set_seed,
        set_selected_racers,
        set_use_scripted_dice,
    )


@app.cell
def _(
    BOARD_DEFINITIONS,
    RacerName,
    get_args,
    get_board,
    get_debug_mode,
    get_dice_rolls_text,
    get_racer_to_add,
    get_saved_positions,
    get_seed,
    get_selected_racers,
    get_use_scripted_dice,
    mo,
    set_board,
    set_debug_mode,
    set_dice_rolls_text,
    set_racer_to_add,
    set_saved_positions,
    set_seed,
    set_selected_racers,
    set_step_idx,
    set_use_scripted_dice,
):
    # --- UI DEFINITION ---
    AVAILABLE_RACERS = sorted(list(get_args(RacerName)))
    current_roster = get_selected_racers()
    saved_positions = get_saved_positions()

    # 1. Main Controls
    reset_button = mo.ui.button(
        label="⟳Reset",
        on_click=lambda _: set_step_idx(0),
    )

    def manual_change(setter, value):
        setter(value)
        set_step_idx(0)
        return value

    scenario_seed = mo.ui.number(
        start=0,
        stop=10000,
        value=get_seed(),
        label="Random Seed",
        on_change=lambda v: manual_change(set_seed, v),
    )

    board_selector = mo.ui.dropdown(
        options=sorted(list(BOARD_DEFINITIONS.keys())),
        value=get_board(),
        label="Board Map",
        on_change=lambda v: manual_change(set_board, v),
    )

    use_scripted_dice_ui = mo.ui.switch(
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
    debug_mode_ui = mo.ui.switch(
        value=get_debug_mode(), on_change=set_debug_mode, label="Debug logging"
    )

    # 2. Position Inputs & Logic
    def _make_pos_on_change(racer_name):
        def _on_change(new_val):
            try:
                v = int(new_val)
            except Exception:
                v = 0
            set_saved_positions(lambda cur: {**cur, racer_name: v})
            set_step_idx(0)

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

    # 3. Snapshot Logic
    def _snapshot_values(exclude=None):
        return {r: w.value for r, w in pos_widget_map.items() if r != exclude}

    # --- REORDERING LOGIC ---
    def move_racer(index, direction):
        # Direction: -1 for up, +1 for down
        def _move(_):
            roster = list(get_selected_racers())
            new_index = index + direction
            if 0 <= new_index < len(roster):
                roster[index], roster[new_index] = roster[new_index], roster[index]
                set_selected_racers(roster)
                set_step_idx(0)  # Reset sim

        return _move

    # 4. Action Buttons (Remove, Up, Down)
    action_buttons = {}
    for i, ui_racer in enumerate(current_roster):
        # Remove
        btn_remove = mo.ui.button(
            label="✖",
            on_click=lambda _, r=ui_racer: (
                set_saved_positions(_snapshot_values(exclude=r)),
                set_selected_racers(lambda cur: [x for x in cur if x != r]),
                set_step_idx(0),
            ),
            disabled=(len(current_roster) <= 1),
        )

        # Up (disabled for first item)
        btn_up = mo.ui.button(
            label="↑",
            on_click=move_racer(i, -1),
            disabled=(i == 0),
        )

        # Down (disabled for last item)
        btn_down = mo.ui.button(
            label="↓",
            on_click=move_racer(i, 1),
            disabled=(i == len(current_roster) - 1),
        )

        action_buttons[ui_racer] = (btn_remove, btn_up, btn_down)

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
            new_pos[r] = 0
            set_saved_positions(new_pos)
            set_selected_racers(lambda cur: cur + [r])
            set_racer_to_add(None)
            set_step_idx(0)
        return v

    add_button = mo.ui.button(label="Add", on_click=_add_racer)

    # 6. Layout Table
    table_rows = []
    for i, ui_racer in enumerate(current_roster):
        w_pos = pos_widget_map[ui_racer]
        b_rem, b_up, b_down = action_buttons[ui_racer]

        # Group Up/Down buttons tightly
        move_grp = mo.hstack([b_up, b_down], justify="center", gap=0)

        table_rows.append(f"| {i + 1}. {ui_racer} | {w_pos} | {move_grp} | {b_rem} |")

    racer_table = mo.md(
        "| Racer | Start Pos | Order | Remove |\n"
        "| :--- | :--- | :---: | :---: |\n" + "\n".join(table_rows)
    )
    return (
        add_button,
        add_racer_dropdown,
        board_selector,
        current_roster,
        debug_mode_ui,
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
    board_selector,
    debug_mode_ui,
    dice_input,
    mo,
    racer_table,
    reset_button,
    results_tabs,
    scenario_seed,
    use_scripted_dice_ui,
):
    # --- CONFIG DISPLAY ---
    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md("## Configure"),
                    mo.hstack(
                        [scenario_seed, board_selector, reset_button],
                        justify="start",
                        gap=2,
                    ),
                    mo.vstack(
                        [use_scripted_dice_ui, dice_input],
                    ),
                    mo.hstack([debug_mode_ui], justify="start", gap=2),
                    mo.md("### Racers"),
                    racer_table,
                    mo.hstack([add_racer_dropdown, add_button], justify="start", gap=1),
                ]
            ),
            results_tabs.style({"overflow-x": "auto", "max-width": "100%"}),
        ],
    )
    return


@app.cell
def _(
    df_races,
    get_last_race_hash,
    get_last_result_hash,
    pl,
    racer_results_table,
    races_table,
    set_board,
    set_last_race_hash,
    set_last_result_hash,
    set_saved_positions,
    set_seed,
    set_selected_racers,
    set_step_idx,
    set_use_scripted_dice,
):
    # --- CONFIGURATION LOADER (Stable Version) ---

    # 1. Capture Current Table Selections
    curr_race_hash = None
    curr_race_row = None
    if races_table.value is not None and races_table.value.height > 0:
        curr_race_hash = races_table.value.item(0, "config_hash")
        curr_race_row = races_table.value.row(0, named=True)

    curr_res_hash = None
    if racer_results_table.value is not None and racer_results_table.value.height > 0:
        curr_res_hash = racer_results_table.value.item(0, "config_hash")

    # 2. Get Last Known States
    last_race = get_last_race_hash()
    last_res = get_last_result_hash()

    # 3. Detect Changes (Delta Check)
    # We only react if the current selection differs from the last recorded selection for that specific table.
    race_changed = curr_race_hash is not None and curr_race_hash != last_race
    res_changed = curr_res_hash is not None and curr_res_hash != last_res

    target_config = None

    # Priority: Races Table > Results Table
    # But only if it actually changed!
    if race_changed:
        target_config = curr_race_row
    elif res_changed:
        # We need to fetch the row from df_races
        filtered = df_races.filter(pl.col("config_hash") == curr_res_hash)
        if filtered.height > 0:
            target_config = filtered.row(0, named=True)

    # 4. Apply Configuration (if any change detected)
    if target_config:
        racer_names_str = target_config.get("racer_names", "")
        new_roster = [n.strip() for n in racer_names_str.split(",") if n.strip()]
        new_seed = int(target_config.get("seed", 42))
        new_board = target_config.get("board", "standard")

        set_seed(new_seed)
        set_board(new_board)
        set_selected_racers(new_roster)
        set_saved_positions({n: 0 for n in new_roster})
        set_use_scripted_dice(False)
        set_step_idx(0)

    # 5. SYNC STATE (CRITICAL)
    # Always update the "last seen" hashes to match the current table values.
    # This prevents the "other" table from triggering a change in the next cycle
    # just because we ignored it this time.
    if curr_race_hash != last_race:
        set_last_race_hash(curr_race_hash)

    if curr_res_hash != last_res:
        set_last_result_hash(curr_res_hash)
    return


@app.cell
def _(dice_rolls_text_ui, mo, use_scripted_dice_ui):
    dice_input = dice_rolls_text_ui if use_scripted_dice_ui.value else mo.Html("")
    return (dice_input,)


@app.cell
def _(
    load_status,
    mo,
    racer_results_table,
    races_table,
    reload_data_btn,
    results_folder_browser,
):
    def _header():
        return mo.hstack([mo.md(load_status), reload_data_btn], justify="space-between")

    results_tabs = mo.ui.tabs(
        {
            "Racer Results": mo.vstack([_header(), racer_results_table]),
            "Races": mo.vstack([_header(), races_table]),
            "Source": mo.vstack(
                [
                    mo.md("### Data Directory"),
                    mo.md(
                        "Select the folder containing `races.parquet` and `racer_results.parquet`."
                    ),
                    mo.hstack(
                        [results_folder_browser, reload_data_btn], align="center"
                    ),
                    mo.callout(mo.md(f"Current Status: {load_status}"), kind="neutral"),
                ]
            ).style({"width": "100%", "min-height": "400px"}),
        }
    )
    return (results_tabs,)


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
    StepSnapshot,
    TripCmdEvent,
    WarpCmdEvent,
    current_roster,
    get_board,
    get_debug_mode,
    get_dice_rolls_text,
    get_saved_positions,
    get_seed,
    get_use_scripted_dice,
    logging,
    mo,
    re,
    reset_button,
):
    from magical_athlete_simulator.simulation.telemetry import (
        SnapshotPolicy,
        SnapshotRecorder,
        MetricsAggregator,  # <--- CHANGED THIS IMPORT
    )
    from magical_athlete_simulator.core.events import AbilityTriggeredEvent

    # Reactivity triggers
    reset_button.value
    # Use state getters
    current_seed_val = get_seed()
    current_board_val = get_board()

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
    log_level = logging.DEBUG if get_debug_mode() else logging.INFO
    root_logger.setLevel(log_level)

    dice_rolls = None
    if get_use_scripted_dice():
        raw = get_dice_rolls_text().strip()
        if raw:
            try:
                dice_rolls = [int(t) for t in re.split(r"[,\s]+", raw) if t]
            except:
                pass

    # Updated: Use dynamic board and seed
    scenario = GameScenario(
        racers_config=[
            RacerConfig(i, n, start_pos=int(get_saved_positions().get(n, 0)))
            for i, n in enumerate(current_roster)
        ],
        dice_rolls=dice_rolls,
        seed=None if dice_rolls else current_seed_val,
        board=BOARD_DEFINITIONS.get(current_board_val, BOARD_DEFINITIONS["standard"])(),
    )

    step_history = []
    turn_map = {}
    SNAPSHOT_EVENTS = (MoveCmdEvent, WarpCmdEvent, TripCmdEvent)

    class RichLogSource:
        def __init__(self, console):
            self._console = console

        def export_text(self) -> str:
            return self._console.export_text(clear=False)

        def export_html(self) -> str:
            return self._console.export_html(
                clear=False, inline_styles=True, code_format="{code}"
            )

    policy = SnapshotPolicy(
        snapshot_event_types=SNAPSHOT_EVENTS,
        ensure_snapshot_each_turn=True,
        fallback_event_name="TurnSkipped/Recovery",
        snapshot_on_turn_end=False,
    )

    snapshot_recorder = SnapshotRecorder(
        policy=policy,
        log_source=RichLogSource(log_console),
    )

    # --- CHANGED BLOCK START ---
    # We use the new Aggregator. We need a dummy hash since we aren't saving to DB here.
    metrics_aggregator = MetricsAggregator(config_hash="interactive-session")
    metrics_aggregator.initialize_racers(scenario.engine)

    sim_turn_counter = {"current": 0}

    def on_event(engine, event):
        t_idx = sim_turn_counter["current"]
        snapshot_recorder.on_event(engine, event, turn_index=t_idx)
        metrics_aggregator.on_event(event)  # <--- UPDATED CALL

    if hasattr(scenario.engine, "on_event_processed"):
        scenario.engine.on_event_processed = on_event
    # --- CHANGED BLOCK END ---

    engine = scenario.engine
    snapshot_recorder.capture(engine, "InitialState", turn_index=0)

    with mo.status.spinner(title="Simulating..."):
        while not engine.state.race_over:
            log_console.export_html(clear=True)
            t_idx = sim_turn_counter["current"]
            scenario.run_turn()

            # Note: We don't strictly NEED to call on_turn_end for the aggregator
            # if we only care about ability counts, but it's good practice:
            metrics_aggregator.on_turn_end(engine, turn_index=t_idx)

            snapshot_recorder.on_turn_end(engine, turn_index=t_idx)
            sim_turn_counter["current"] += 1
            if len(snapshot_recorder.step_history) > 1000:
                break

    step_history: list[StepSnapshot] = snapshot_recorder.step_history
    turn_map = snapshot_recorder.turn_map

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
        current_turn_idx = current_data.turn_index
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
    Any,
    Literal,
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
    curr_step: Any | Literal[0] = current_data.global_step_index if current_data else 0
    tot_steps = len(step_history) if step_history else 0

    status_text = mo.md(
        f"**Turn {current_turn_idx}** (Step {curr_step + 1}/{tot_steps})"
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
            full_turn_log = step_history[end_of_turn_idx].log_html

            if is_active:
                bg, border, opacity = "#000000", "#00FF00", "1.0"
                lines = full_turn_log.split("\n")
                target_line = current_data.log_line_index
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
def _(df_racer_results, df_races, mo):
    # --- UI CREATION CELL ---

    header = mo.md(
        """
        <hr style="margin: 1.25rem 0;" />
        <h2 style="margin: 0 0 0.5rem 0;">Aggregated Dashboard</h2>
        <div style="color: #aaa; margin-bottom: 0.75rem;">
          Filter races by roster, board, and player count (applies to all aggregated charts/tables below).
        </div>
        """
    )

    all_racers = sorted(df_racer_results.get_column("racer_name").unique().to_list())
    all_boards = sorted(df_races.get_column("board").unique().to_list())
    all_counts = sorted(df_races.get_column("racer_count").unique().to_list())

    ui_racers = mo.ui.multiselect(
        options=all_racers,
        value=all_racers,
        label="Racers (roster pool)",
    )
    ui_counts = mo.ui.multiselect(
        options=all_counts,
        value=all_counts,
        label="Racer count(s)",
    )
    ui_boards = mo.ui.multiselect(
        options=all_boards,
        value=all_boards,
        label="Board(s)",
    )

    # Just display the UI here
    mo.vstack(
        [header, mo.hstack([ui_racers, ui_counts, ui_boards], justify="space-between")]
    )
    return ui_boards, ui_counts, ui_racers


@app.cell
def _(
    df_positions,
    df_racer_results,
    df_races,
    mo,
    pl,
    ui_boards,
    ui_counts,
    ui_racers,
):
    # --- LOGIC & FILTERING CELL ---

    selected_racers = list(ui_racers.value)
    selected_counts = list(ui_counts.value)
    selected_boards = list(ui_boards.value)

    # --- Validation ---
    error_msg = None
    if len(selected_boards) == 0:
        error_msg = "Select at least one board."
    elif len(selected_counts) == 0:
        error_msg = "Select at least one racer count."
    else:
        min_required = max(selected_counts)
        if len(selected_racers) < min_required:
            error_msg = (
                f"Need at least {min_required} racers selected (because max racer_count = {min_required}), "
                f"but only {len(selected_racers)} selected."
            )

    # --- Filter Logic ---
    if error_msg is None:
        # 1. Filter Races by metadata (Board & Count)
        races_bc = df_races.filter(
            pl.col("board").is_in(selected_boards)
            & pl.col("racer_count").is_in(selected_counts)
        ).select(["config_hash", "board", "racer_count"])

        # 2. Roster Check: Ensure all participants in the race are in 'selected_racers'
        roster_ok = (
            df_racer_results.join(races_bc, on="config_hash", how="inner")
            .group_by(["config_hash", "board", "racer_count"])
            .agg(
                [
                    pl.col("racer_name").n_unique().alias("n_present"),
                    pl.col("racer_name")
                    .is_in(selected_racers)
                    .all()
                    .alias("all_in_pool"),
                ]
            )
            .filter(
                pl.col("all_in_pool") & (pl.col("n_present") == pl.col("racer_count"))
            )
            .select(["config_hash"])
        )

        eligible_hashes = roster_ok.get_column("config_hash").unique()

        df_races_f = df_races.filter(pl.col("config_hash").is_in(eligible_hashes))
        df_racer_results_f = df_racer_results.filter(
            pl.col("config_hash").is_in(eligible_hashes)
        )
        df_positions_f = df_positions.filter(
            pl.col("config_hash").is_in(eligible_hashes)
        )

        if df_races_f.height == 0:
            error_msg = (
                "No data. Either no races match board/count, "
                "or the selected racer pool excludes members of those races."
            )
            df_races_f = df_races.head(0)
            df_racer_results_f = df_racer_results.head(0)
            df_positions_f = df_positions.head(0)
    else:
        df_races_f = df_races.head(0)
        df_racer_results_f = df_racer_results.head(0)
        df_positions_f = df_positions.head(0)

    # Validation Note Display
    note = (
        mo.md(
            f"<div style='color:#ff6b6b; font-weight:600; margin-top:0.5rem;'>⚠ {error_msg}</div>"
        )
        if error_msg is not None
        else mo.md(
            f"<div style='color:#7ee787; font-weight:600; margin-top:0.5rem;'>✓ Using "
            f"{df_races_f.height} races.</div>"
        )
    )

    note
    return df_positions_f, df_racer_results_f, df_races_f


@app.cell
def _(mo):
    # 1. Define the toggle in its own cell so it can be used as an input downstream
    matchup_metric_toggle = mo.ui.switch(
        value=False,  # False = Residual (default), True = Percentage
        label="Show Percentage Shift",
    )
    return (matchup_metric_toggle,)


@app.cell
def _(df_positions_f, df_racer_results_f, df_races_f, pl):
    # 2. HEAVY COMPUTATION CELL
    def unpivot_positions(df_flat: pl.DataFrame) -> pl.DataFrame:
        return (
            df_flat.unpivot(
                index=["config_hash", "turn_index", "current_racer_id"],
                on=["pos_r0", "pos_r1", "pos_r2", "pos_r3", "pos_r4", "pos_r5"],
                variable_name="racer_slot",
                value_name="position",
            )
            .with_columns(
                [
                    pl.col("racer_slot")
                    .str.extract(r"pos_r(\d+)", 1)
                    .cast(pl.Int64)
                    .alias("racer_id"),
                ]
            )
            .with_columns(
                (pl.col("racer_id") == pl.col("current_racer_id")).alias(
                    "is_current_turn"
                )
            )
            .drop("racer_slot")
            .filter(pl.col("position").is_not_null())
        )

    def _calculate_all_data():
        if df_positions_f.height == 0:
            return None

        # --- A. PREPARE METRICS ---
        df_long = unpivot_positions(df_positions_f)

        # 1. TRUTH SOURCE: Global Win Rates (Used for Table & Pressure)
        global_win_rates = (
            df_racer_results_f.group_by("racer_name")
            .agg(
                [
                    (pl.col("rank") == 1).sum().alias("total_wins"),
                    pl.len().alias("total_races"),
                ]
            )
            .with_columns(
                (pl.col("total_wins") / pl.col("total_races")).alias("global_win_rate")
            )
        )

        # 2. Tightness & Volatility
        turn_stats = df_long.group_by(["config_hash", "turn_index"]).agg(
            pl.col("position").mean().alias("mean_pos")
        )
        tightness_calc = (
            df_long.join(turn_stats, on=["config_hash", "turn_index"])
            .with_columns((pl.col("position") - pl.col("mean_pos")).abs().alias("dev"))
            .group_by("config_hash")
            .agg(pl.col("dev").mean().alias("race_tightness_score"))
        )

        volatility_calc = (
            df_long.with_columns(
                pl.col("position")
                .rank(method="dense", descending=True)
                .over(["config_hash", "turn_index"])
                .alias("rank_now")
            )
            .sort(["config_hash", "racer_id", "turn_index"])
            .with_columns(
                pl.col("rank_now")
                .shift(1)
                .over(["config_hash", "racer_id"])
                .alias("rank_prev")
            )
            .filter(pl.col("rank_prev").is_not_null())
            .with_columns(
                (pl.col("rank_now") != pl.col("rank_prev"))
                .cast(pl.Int8)
                .alias("rank_changed")
            )
            .group_by("config_hash")
            .agg(pl.col("rank_changed").mean().alias("race_volatility_score"))
        )

        final_dist_calc = df_long.group_by(["config_hash", "racer_id"]).agg(
            pl.col("position").max().alias("final_distance")
        )

        # 3. Clutch & Closing (Tie-aware logic)
        winner_turns = (
            df_racer_results_f.filter(pl.col("rank") == 1)
            .group_by("config_hash")
            .agg(pl.col("turns_taken").min().alias("winner_turns"))
        )

        snapshot_target = winner_turns.with_columns(
            (pl.col("winner_turns") * 0.66)
            .floor()
            .clip(lower_bound=1)
            .cast(pl.Int32)
            .alias("snapshot_turn")
        )

        snapshot_state = (
            df_long.join(snapshot_target, on="config_hash")
            .filter(pl.col("turn_index") <= pl.col("snapshot_turn"))
            .sort(["config_hash", "racer_id", "turn_index"])
            .group_by(["config_hash", "racer_id"])
            .last()
        )

        snapshot_ranks = snapshot_state.join(
            df_races_f.select(["config_hash", "racer_count"]), on="config_hash"
        ).with_columns(
            pl.col("position")
            .rank(method="min", descending=True)
            .over("config_hash")
            .alias("rank_at_snapshot")
        )

        racer_map = df_racer_results_f.select(
            ["config_hash", "racer_id", "racer_name", "rank"]
        ).unique()
        snapshot_with_names = snapshot_ranks.join(
            racer_map, on=["config_hash", "racer_id"], how="inner"
        )

        # PRESSURE METRICS (Keep using the "Truth" source for these as they are relative to global performance)
        clutch_calc = (
            snapshot_with_names.filter(
                pl.col("rank_at_snapshot") == pl.col("racer_count")
            )
            .group_by("racer_name")
            .agg(
                (pl.col("rank") == 1).sum().alias("clutch_wins"),
                pl.len().alias("clutch_opps"),
            )
            .join(
                global_win_rates.select(["racer_name", "global_win_rate"]),
                on="racer_name",
                how="left",
            )
            .with_columns(
                [
                    (pl.col("clutch_wins") / pl.col("clutch_opps")).alias(
                        "raw_clutch_rate"
                    ),
                ]
            )
            .with_columns(
                [
                    (
                        (pl.col("raw_clutch_rate") - pl.col("global_win_rate"))
                        / pl.col("global_win_rate")
                    ).alias("rel_clutch_shift")
                ]
            )
            .select(
                ["racer_name", "raw_clutch_rate", "rel_clutch_shift"]
            )  # CLEAN SELECTION
        )

        closing_calc = (
            snapshot_with_names.filter(pl.col("rank_at_snapshot") == 1)
            .group_by("racer_name")
            .agg(
                (pl.col("rank") == 1).sum().alias("closing_wins"),
                pl.len().alias("closing_opps"),
            )
            .join(
                global_win_rates.select(["racer_name", "global_win_rate"]),
                on="racer_name",
                how="left",
            )
            .with_columns(
                [
                    (pl.col("closing_wins") / pl.col("closing_opps")).alias(
                        "raw_closing_rate"
                    ),
                ]
            )
            .with_columns(
                [
                    (
                        (pl.col("raw_closing_rate") - pl.col("global_win_rate"))
                        / pl.col("global_win_rate")
                    ).alias("rel_closing_shift")
                ]
            )
            .select(
                ["racer_name", "raw_closing_rate", "rel_closing_shift"]
            )  # CLEAN SELECTION
        )

        # 4. Start Position Bias (REVERTED TO LOCAL CALCULATION)
        start_stats = (
            df_racer_results_f.join(
                df_races_f.select(["config_hash", "racer_count"]), on="config_hash"
            )
            .with_columns(
                [
                    (pl.col("racer_id") == 0).alias("is_first"),
                    (pl.col("racer_id") == (pl.col("racer_count") - 1)).alias(
                        "is_last"
                    ),
                ]
            )
            .group_by("racer_name")
            .agg(
                [
                    (pl.col("rank").filter(pl.col("is_first")) == 1)
                    .mean()
                    .alias("win_rate_first"),
                    (pl.col("rank").filter(pl.col("is_last")) == 1)
                    .mean()
                    .alias("win_rate_last"),
                    # LOCAL CALCULATION (Restored)
                    (pl.col("rank") == 1).mean().alias("win_rate_global_local"),
                ]
            )
            .with_columns(
                [
                    (
                        (pl.col("win_rate_first") - pl.col("win_rate_global_local"))
                        / pl.col("win_rate_global_local")
                    ).alias("rel_bias_first"),
                    (
                        (pl.col("win_rate_last") - pl.col("win_rate_global_local"))
                        / pl.col("win_rate_global_local")
                    ).alias("rel_bias_last"),
                ]
            )
            .select(
                ["racer_name", "rel_bias_first", "rel_bias_last"]
            )  # CLEAN SELECTION
        )

        # 5. Environment & Merge
        race_environment_stats = df_racer_results_f.group_by("config_hash").agg(
            [
                (
                    pl.col("ability_trigger_count").sum() / pl.col("racer_id").count()
                ).alias("race_avg_triggers"),
                (pl.col("recovery_turns").sum() / pl.col("turns_taken").sum()).alias(
                    "race_avg_trip_rate"
                ),
            ]
        )

        stats_races = (
            df_races_f.join(tightness_calc, on="config_hash", how="left")
            .join(volatility_calc, on="config_hash", how="left")
            .join(race_environment_stats, on="config_hash", how="left")
            .fill_null(0)
        )

        stats_results = df_racer_results_f.join(
            final_dist_calc, on=["config_hash", "racer_id"], how="left"
        )

        potency_score = (
            stats_results.with_columns(
                (pl.col("ability_trigger_count") > 0).alias("used")
            )
            .group_by("racer_id")
            .agg(
                [
                    pl.col("final_vp").filter(pl.col("used")).mean().alias("vp_used"),
                    pl.col("final_vp")
                    .filter(~pl.col("used"))
                    .mean()
                    .alias("vp_unused"),
                    pl.col("final_vp").mean().alias("vp_global"),
                ]
            )
            .with_columns(
                [
                    pl.col("vp_used").fill_null(pl.col("vp_global")),
                    pl.col("vp_unused").fill_null(pl.col("vp_global")),
                ]
            )
            .with_columns(
                (pl.col("vp_used") - pl.col("vp_unused")).alias("strategic_potency")
            )
        )

        # 6. Base Stats Aggregation (Median Consistency)

        # A. Calculate Median VP per racer
        racer_medians = stats_results.group_by("racer_name").agg(
            pl.col("final_vp").median().alias("median_vp")
        )

        # B. Calculate % of races within +/- 1.0 VP of Median
        consistency_calc = (
            stats_results.join(racer_medians, on="racer_name", how="left")
            .with_columns(
                (
                    (pl.col("final_vp") >= (pl.col("median_vp") - 1.0))
                    & (pl.col("final_vp") <= (pl.col("median_vp") + 1.0))
                ).alias("is_consistent")
            )
            .group_by("racer_name")
            .agg(pl.col("is_consistent").mean().alias("consistency_score"))
        )

        base_stats = (
            stats_results.with_columns(
                pl.when(pl.col("turns_taken") > 0)
                .then(pl.col("turns_taken"))
                .otherwise(1)
                .alias("safe_turns"),
                pl.when(pl.col("final_vp") > 0)
                .then(pl.col("final_vp"))
                .otherwise(None)
                .alias("safe_vp"),
            )
            .with_columns(
                (pl.col("safe_turns") - pl.col("recovery_turns"))
                .clip(lower_bound=1)
                .alias("rolling_turns")
            )
            .join(
                stats_races.select(
                    [
                        "config_hash",
                        "race_tightness_score",
                        "race_volatility_score",
                        "race_avg_triggers",
                        "race_avg_trip_rate",
                        "total_turns",
                    ]
                ),
                on="config_hash",
                how="left",
            )
            .group_by("racer_name")
            .agg(
                [
                    pl.col("racer_id").first().alias("racer_id"),
                    pl.col("final_vp").mean().alias("mean_vp"),
                    pl.col("final_vp").std().alias("std_vp"),
                    (pl.col("rank") == 1).sum().alias("cnt_1st"),
                    (pl.col("rank") == 2).sum().alias("cnt_2nd"),
                    pl.len().alias("races_run"),
                    # Dynamics
                    pl.col("race_tightness_score").mean().alias("avg_race_tightness"),
                    pl.col("race_volatility_score").mean().alias("avg_race_volatility"),
                    pl.col("race_avg_triggers").mean().alias("avg_env_triggers"),
                    pl.col("race_avg_trip_rate").mean().alias("avg_env_trip_rate"),
                    pl.col("total_turns").mean().alias("avg_game_duration"),
                    # Abilities
                    (pl.col("ability_trigger_count") / pl.col("safe_turns"))
                    .mean()
                    .alias("triggers_per_turn"),
                    (pl.col("ability_self_target_count") / pl.col("safe_turns"))
                    .mean()
                    .alias("self_per_turn"),
                    (pl.col("ability_target_count") / pl.col("safe_turns"))
                    .mean()
                    .alias("target_per_turn"),
                    # Movement
                    pl.col("turns_taken").mean().alias("avg_turns"),
                    (pl.col("sum_dice_rolled") / pl.col("rolling_turns"))
                    .mean()
                    .alias("dice_per_turn"),
                    (pl.col("sum_dice_rolled_final") / pl.col("rolling_turns"))
                    .mean()
                    .alias("final_roll_per_turn"),
                    (pl.col("final_distance") / pl.col("safe_turns"))
                    .mean()
                    .alias("avg_speed"),
                    (pl.col("sum_dice_rolled") / pl.col("safe_vp"))
                    .mean()
                    .alias("dice_per_vp"),
                ]
            )
        )

        corr_df = (
            stats_results.group_by("racer_name")
            .agg(
                [
                    pl.corr("sum_dice_rolled", "final_vp").alias("dice_impact_score"),
                    pl.corr("sum_dice_rolled_final", "final_vp").alias(
                        "final_roll_impact_score"
                    ),
                    pl.corr("turns_taken", "final_vp").alias("duration_pref_score"),
                ]
            )
            .fill_nan(0)
        )

        final_stats = (
            base_stats.join(potency_score, on="racer_id", how="left")
            .join(corr_df, on="racer_name", how="left")
            .join(start_stats, on="racer_name", how="left")
            .join(clutch_calc, on="racer_name", how="left")
            .join(closing_calc, on="racer_name", how="left")
            .join(
                global_win_rates.select(["racer_name", "global_win_rate"]),
                on="racer_name",
                how="left",
            )
            .join(consistency_calc, on="racer_name", how="left")
            .with_columns(
                [
                    (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
                    (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd"),
                    pl.col("strategic_potency").fill_null(0),
                    pl.col("std_vp").fill_null(0),
                    pl.col("consistency_score").fill_null(0),
                    pl.col("rel_bias_first").fill_null(0),
                    pl.col("rel_bias_last").fill_null(0),
                    pl.col("rel_clutch_shift").fill_null(0),
                    pl.col("rel_closing_shift").fill_null(0),
                    pl.col("raw_clutch_rate").fill_null(0),
                    pl.col("raw_closing_rate").fill_null(0),
                    pl.col("global_win_rate").fill_null(0),
                ]
            )
        )

        # --- B. MATRICES ---
        global_means = final_stats.select(
            ["racer_name", pl.col("mean_vp").alias("my_global_avg")]
        )

        subjects = stats_results.select(["config_hash", "racer_name", "final_vp"])
        opponents = stats_results.select(
            [pl.col("config_hash"), pl.col("racer_name").alias("opponent_name")]
        )

        matchup_df = (
            subjects.join(opponents, on="config_hash", how="inner")
            .filter(pl.col("racer_name") != pl.col("opponent_name"))
            .group_by(["racer_name", "opponent_name"])
            .agg(pl.col("final_vp").mean().alias("avg_vp_with_opponent"))
            .join(global_means, on="racer_name", how="left")
            .with_columns(
                [
                    (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg")).alias(
                        "residual_matchup"
                    ),
                    (
                        (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg"))
                        / pl.col("my_global_avg")
                    ).alias("percentage_shift"),
                ]
            )
        )

        return {
            "stats": final_stats,
            "matchup_df": matchup_df,
            "results_raw": stats_results,
            "races_raw": stats_races,
        }

    dashboard_data = _calculate_all_data()
    return (dashboard_data,)


@app.cell
def _(
    alt,
    dashboard_data,
    df_races_f,
    get_racer_color,
    matchup_metric_toggle,
    mo,
    pl,
):
    if not dashboard_data:
        mo.stop(True, mo.md("⚠️ **No results loaded.**"))

    stats = dashboard_data["stats"]
    matchup_df = dashboard_data["matchup_df"]
    proc_results = dashboard_data["results_raw"]
    proc_races = dashboard_data["races_raw"]

    # --- 1. DYNAMIC MATCHUP CHART ---
    use_pct = matchup_metric_toggle.value
    metric_col = "percentage_shift" if use_pct else "residual_matchup"
    metric_title = "Pct Shift vs Own Avg" if use_pct else "Residual vs Own Avg"
    legend_format = "+.1%" if use_pct else "+.2f"

    c_matrix = (
        alt.Chart(matchup_df)
        .mark_rect()
        .encode(
            x=alt.X("opponent_name:N", title="Opponent Present"),
            y=alt.Y("racer_name:N", title="Subject Racer"),
            color=alt.Color(
                f"{metric_col}:Q",
                title=metric_title,
                scale=alt.Scale(scheme="redblue", domainMid=0),
                legend=alt.Legend(format=legend_format),
            ),
            tooltip=[
                "racer_name",
                "opponent_name",
                alt.Tooltip(
                    "avg_vp_with_opponent", format=".2f", title="Avg VP vs Opp"
                ),
                alt.Tooltip("my_global_avg", format=".2f", title="My Global Avg"),
                alt.Tooltip("residual_matchup", format="+.2f", title="Residual (Pts)"),
                alt.Tooltip("percentage_shift", format="+.1%", title="Shift (%)"),
            ],
        )
        .properties(title=f"Matchup Matrix ({metric_title})", width=680, height=680)
    )

    # --- 2. QUADRANT CHART BUILDER ---
    r_list = stats["racer_name"].unique().to_list()
    c_list = [get_racer_color(r) for r in r_list]

    def _build_quadrant_chart(
        stats_df,
        racers,
        colors,
        x_col,
        y_col,
        title,
        x_title,
        y_title,
        reverse_x=False,
        quad_labels=None,
        extra_tooltips=None,
    ):
        vals_x = stats_df[x_col].drop_nulls().to_list()
        vals_y = stats_df[y_col].drop_nulls().to_list()

        if not vals_x or not vals_y:
            return alt.Chart(stats_df).mark_text(text="No Data")

        min_x, max_x = min(vals_x), max(vals_x)
        min_y, max_y = min(vals_y), max(vals_y)

        if min_x == max_x:
            max_x += 0.01
            min_x -= 0.01
        if min_y == max_y:
            max_y += 0.01
            min_y -= 0.01

        pad_x = (max_x - min_x) * 0.15
        pad_y = (max_y - min_y) * 0.15
        view_min_x, view_max_x = min_x - pad_x, max_x + pad_x
        view_min_y, view_max_y = min_y - pad_y, max_y + pad_y
        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2

        base = alt.Chart(stats_df).encode(
            color=alt.Color(
                "racer_name", scale=alt.Scale(domain=racers, range=colors), legend=None
            )
        )

        h_line = (
            alt.Chart(pl.DataFrame({"y": [mid_y]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(y="y")
        )
        v_line = (
            alt.Chart(pl.DataFrame({"x": [mid_x]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(x="x")
        )

        tips = [
            "racer_name",
            alt.Tooltip(x_col, format=".2f"),
            alt.Tooltip(y_col, format=".2f"),
            "mean_vp",
        ]
        if extra_tooltips:
            tips.extend(extra_tooltips)

        points = base.mark_circle(size=150, opacity=0.9).encode(
            x=alt.X(
                x_col,
                title=x_title,
                scale=alt.Scale(
                    domain=[view_min_x, view_max_x], reverse=reverse_x, zero=False
                ),
            ),
            y=alt.Y(
                y_col,
                title=y_title,
                scale=alt.Scale(domain=[view_min_y, view_max_y], zero=False),
            ),
            tooltip=tips,
        )

        text_labels = points.mark_text(
            align="center",
            baseline="middle",
            dy=-15,
            dx=-15,
            fontSize=15,
            fontWeight="bold",
            stroke="black",
            strokeWidth=0.2,
        ).encode(text="racer_name")

        chart = h_line + v_line + points + text_labels

        if quad_labels and len(quad_labels) == 4:
            if reverse_x:
                left_x, right_x = view_max_x - (pad_x * 0.5), view_min_x + (pad_x * 0.5)
            else:
                left_x, right_x = view_min_x + (pad_x * 0.5), view_max_x - (pad_x * 0.5)
            top_y, bot_y = view_max_y - (pad_y * 0.5), view_min_y + (pad_y * 0.5)
            text_props = {
                "fontWeight": "bold",
                "opacity": 0.6,
                "fontSize": 11,
                "color": "#e0e0e0",
            }

            t1 = (
                alt.Chart(
                    pl.DataFrame({"x": [left_x], "y": [top_y], "t": [quad_labels[0]]})
                )
                .mark_text(align="left", baseline="top", **text_props)
                .encode(x="x", y="y", text="t")
            )
            t2 = (
                alt.Chart(
                    pl.DataFrame({"x": [right_x], "y": [top_y], "t": [quad_labels[1]]})
                )
                .mark_text(align="right", baseline="top", **text_props)
                .encode(x="x", y="y", text="t")
            )
            t3 = (
                alt.Chart(
                    pl.DataFrame({"x": [left_x], "y": [bot_y], "t": [quad_labels[2]]})
                )
                .mark_text(align="left", baseline="bottom", **text_props)
                .encode(x="x", y="y", text="t")
            )
            t4 = (
                alt.Chart(
                    pl.DataFrame({"x": [right_x], "y": [bot_y], "t": [quad_labels[3]]})
                )
                .mark_text(align="right", baseline="bottom", **text_props)
                .encode(x="x", y="y", text="t")
            )
            chart = chart + t1 + t2 + t3 + t4

        return chart.properties(title=title, width=680, height=680)

    # --- 3. GENERATE CHARTS ---
    # UPDATED: Use Median Consistency
    # X-Axis: consistency_score (0.0 to 1.0)
    # Reverse X? No, High Score = Reliable (Right side).
    # Wait, conventional charts usually have "Stable/Good" on Top-Right or Top-Left.
    # User wanted "Reliable" (Low Variance) grouped.
    # Let's put High Consistency (Reliable) on the RIGHT.

    c_consist = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "consistency_score",
        "mean_vp",
        "Consistency (Median Stability)",
        "Stability (% Races near Median)",
        "Avg VP",
        False,  # High Consistency = Right
        [
            "Reliable Winner",
            "Wildcard",
            "Erratic",
            "Reliable Loser",
        ],  # TL, TR, BL, BR ??
        # Wait, if X is Consistency (Right=High):
        # Top-Right: High VP, High Consist = Reliable Winner
        # Top-Left: High VP, Low Consist = Wildcard (Boom/Bust winner)
        # Bot-Right: Low VP, High Consist = Reliable Loser
        # Bot-Left: Low VP, Low Consist = Erratic Loser
    )
    # The quadrant labels order is [TL, TR, BL, BR]
    # So: ["Wildcard", "Reliable Winner", "Erratic", "Reliable Loser"]

    c_consist = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "consistency_score",
        "mean_vp",
        "Consistency (Median Stability)",
        "Stability (% Races within 1.0 VP of Median)",
        "Avg VP",
        False,
        ["Wildcard", "Reliable Winner", "Erratic", "Reliable Loser"],
    )

    c_ability = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "triggers_per_turn",
        "strategic_potency",
        "Ability Strategic Value",
        "Frequency (Trig/Turn)",
        "Potency (VP Delta)",
        False,
        ["Spam / Low Value", "Engine", "Low Impact", "Clutch / High Value"],
    )
    c_excitement = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "avg_race_tightness",
        "avg_race_volatility",
        "Excitement Profile",
        "Tightness",
        "Volatility",
        True,
        ["Rubber Band", "Thriller", "Procession", "Stalemate"],
    )
    c_movement_val = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "avg_speed",
        "dice_impact_score",
        "Movement vs Luck Reliance",
        "Speed (Avg Move/Turn)",
        "Dice Impact (Low = Reliable, High = Gambler)",
        False,
        ["Dice Hungry", "Nitro Junkie", "Slow Farmer", "Efficient Engine"],
    )

    c_start_bias = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "rel_bias_last",
        "rel_bias_first",
        "Starting Position Bias (Rel. Win%)",
        "Comeback Bias (Shift when Last)",
        "Frontrunner Bias (Shift when First)",
        False,
        ["Flexible", "Frontrunner", "Disadvantaged", "Comeback King"],
    )

    c_clutch_profile = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "rel_clutch_shift",
        "rel_closing_shift",
        "Pressure Profile (Relative Shift)",
        "Clutch Shift (Win% vs Avg when Last)",
        "Closing Shift (Win% vs Avg when First)",
        False,
        ["Choke Artist", "Champion", "Weak Closer", "Frontrunner"],
        extra_tooltips=[
            alt.Tooltip("raw_clutch_rate", format=".1%", title="Win% from Last"),
            alt.Tooltip("raw_closing_rate", format=".1%", title="Win% from First"),
            alt.Tooltip("global_win_rate", format=".1%", title="Global Win%"),
        ],
    )

    c_duration = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "avg_turns",
        "duration_pref_score",
        "Duration Profile (Pacing)",
        "Avg Personal Turns (Rusher -> Staller)",
        "Duration Pref (Hates Long -> Loves Long)",
        False,
        ["Scaler", "Late Bloomer", "Rusher/Winner", "Flash in Pan"],
    )

    # Global Dynamics
    global_agg = (
        proc_races.join(
            proc_results.group_by("config_hash").agg(
                pl.col("final_vp").mean().alias("avg_vp")
            ),
            on="config_hash",
        )
        .group_by(["board", "racer_count"])
        .agg(
            [
                pl.col("total_turns").mean().alias("Avg Turns"),
                pl.col("avg_vp").mean().alias("Avg VP"),
                pl.col("race_tightness_score").mean().alias("Tightness"),
                pl.col("race_avg_trip_rate").mean().alias("Trip Rate"),
            ]
        )
        .unpivot(
            index=["board", "racer_count"], variable_name="metric", value_name="val"
        )
    )
    c_global = (
        alt.Chart(global_agg)
        .mark_bar()
        .encode(
            x=alt.X("board:N", title="Board", axis=alt.Axis(labelAngle=0)),
            xOffset="racer_count:N",
            y=alt.Y("val:Q", title=None),
            color=alt.Color("racer_count:N", title="Players"),
            column=alt.Column("metric:N", title=None),
            tooltip=["board", "racer_count", alt.Tooltip("val", format=".2f")],
        )
        .resolve_scale(y="independent")
        .properties(width=100, height=250, title="Global Statistics by Map & Count")
    )

    # Environment Matrix
    race_meta = df_races_f.select(["config_hash", "board", "racer_count"])
    joined = proc_results.join(race_meta, on="config_hash", how="inner")
    racer_baselines = joined.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp")
    )
    env_stats = (
        joined.group_by(["racer_name", "board", "racer_count"])
        .agg(
            [
                pl.col("final_vp").mean().alias("cond_avg_vp"),
                pl.col("final_vp").count().alias("sample_size"),
            ]
        )
        .join(racer_baselines, on="racer_name", how="left")
        .with_columns(
            [
                (
                    (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp"))
                    / pl.col("racer_global_avg_vp")
                ).alias("relative_shift"),
                (
                    pl.col("board").cast(pl.String)
                    + " ("
                    + pl.col("racer_count").cast(pl.String)
                    + "p)"
                ).alias("env_label"),
            ]
        )
    )
    sort_order = (
        env_stats.select(["env_label", "board", "racer_count"])
        .unique()
        .sort(["board", "racer_count"])
        .get_column("env_label")
        .to_list()
    )
    c_env = (
        alt.Chart(env_stats)
        .mark_rect()
        .encode(
            x=alt.X("env_label:N", title="Environment", sort=sort_order),
            y=alt.Y("racer_name:N", title="Racer"),
            color=alt.Color(
                "relative_shift:Q",
                title="Shift vs Own Avg",
                scale=alt.Scale(scheme="redblue", domainMid=0),
                legend=alt.Legend(format=".0%"),
            ),
            tooltip=[
                "racer_name",
                "board",
                "racer_count",
                alt.Tooltip("cond_avg_vp", format=".2f"),
                alt.Tooltip("relative_shift", format="+.1%"),
            ],
        )
        .properties(title="Env Adaptability", width=680, height=680)
    )

    # --- 4. TABLES ---
    master_df = stats.sort("mean_vp", descending=True)

    df_overview = master_df.select(
        [
            pl.col("racer_name").alias("Racer"),
            pl.col("mean_vp").round(2).alias("Avg VP"),
            # Replaced VP SD with Consistency
            (pl.col("consistency_score") * 100).round(1).alias("Consist%"),
            (pl.col("rel_bias_first") * 100).round(1).alias("Bias 1st%"),
            (pl.col("rel_bias_last") * 100).round(1).alias("Bias Last%"),
            (pl.col("pct_1st") * 100).round(1).alias("Tot Win%"),
        ]
    )

    df_movement = master_df.select(
        [
            pl.col("racer_name").alias("Racer"),
            pl.col("avg_speed").round(2).alias("Speed"),
            (pl.col("rel_clutch_shift") * 100).round(1).alias("Clutch Shift%"),
            (pl.col("rel_closing_shift") * 100).round(1).alias("Close Shift%"),
            pl.col("dice_per_turn").round(2).alias("Base Roll"),
            pl.col("final_roll_per_turn").round(2).alias("Final Roll"),
            pl.col("dice_impact_score").round(2).alias("Dice Imp"),
        ]
    )

    df_abilities = master_df.select(
        [
            pl.col("racer_name").alias("Racer"),
            pl.col("strategic_potency").round(2).alias("Potency"),
            pl.col("triggers_per_turn").round(2).alias("Trig/Turn"),
            pl.col("self_per_turn").round(2).alias("Self/Turn"),
            pl.col("target_per_turn").round(2).alias("Tgt/Turn"),
        ]
    )
    df_dynamics = master_df.select(
        [
            pl.col("racer_name").alias("Racer"),
            pl.col("avg_race_volatility").round(2).alias("Volatility"),
            pl.col("avg_race_tightness").round(2).alias("Tightness"),
            pl.col("avg_game_duration").round(1).alias("Avg Game Len"),
            pl.col("avg_env_triggers").round(1).alias("Race Trigs"),
            (pl.col("avg_env_trip_rate") * 100).round(1).alias("Race Trip%"),
        ]
    )
    df_vp = master_df.select(
        [
            pl.col("racer_name").alias("Racer"),
            pl.col("mean_vp").round(2).alias("Avg VP"),
            pl.col("strategic_potency").round(2).alias("Potency"),
            pl.col("dice_impact_score").round(2).alias("Dice Imp"),
            pl.col("final_roll_impact_score").round(2).alias("Final Imp"),
            pl.col("duration_pref_score").round(2).alias("Dur Imp"),
        ]
    )

    # --- 5. UI COMPOSITION ---
    left_charts_ui = mo.ui.tabs(
        {
            "🎯 Consistency": mo.vstack(
                [
                    mo.ui.altair_chart(c_consist),
                    mo.md(
                        "**Consistency**: % of races where Final VP is within ±1.0 of the racer's personal Median VP."
                    ),
                ]
            ),
            "🚦 Start Bias": mo.vstack(
                [
                    mo.ui.altair_chart(c_start_bias),
                    mo.md(
                        "**X: Shift Last** vs **Y: Shift First**. Positive = Win% increases relative to personal average."
                    ),
                ]
            ),
            "💪 Pressure": mo.vstack(
                [
                    mo.ui.altair_chart(c_clutch_profile),
                    mo.md(
                        "**X: Clutch Shift** (Last Place) vs **Y: Closing Shift** (Leading) at 2/3 race mark. Relative to personal average."
                    ),
                ]
            ),
            "⚡ Ability Value": mo.vstack(
                [
                    mo.ui.altair_chart(c_ability),
                    mo.md(
                        "**X: Frequency** vs **Y: Potency**. Potency = Avg VP increase when ability is used."
                    ),
                ]
            ),
            "🏃 Movement Value": mo.vstack(
                [
                    mo.ui.altair_chart(c_movement_val),
                    mo.md(
                        "**X: Speed** vs **Y: Luck** (Dice correlation). Top-Right: Fast but lucky. Bottom-Left: Slow but reliable."
                    ),
                ]
            ),
            "⏱️ Duration": mo.vstack(
                [
                    mo.ui.altair_chart(c_duration),
                    mo.md(
                        "**X: Speed** (Avg turns) vs **Y: Duration Pref** (Likes Long Games?)."
                    ),
                ]
            ),
            "🔥 Excitement": mo.vstack(
                [
                    mo.ui.altair_chart(c_excitement),
                    mo.md("**Tightness** vs **Volatility**."),
                ]
            ),
            "🌍 Global": mo.ui.altair_chart(c_global),
        }
    )

    right_ui = mo.ui.tabs(
        {
            "🏆 Overview": mo.vstack(
                [
                    mo.ui.table(df_overview, selection=None, page_size=50),
                    mo.md(
                        "**Bias%**: % Increase/Decrease in win rate relative to personal average."
                    ),
                ]
            ),
            "⚔️ Interactions": mo.vstack(
                [matchup_metric_toggle, mo.ui.altair_chart(c_matrix)]
            ),
            "🌍 Environments": mo.ui.altair_chart(c_env),
            "🏃 Movement": mo.vstack(
                [
                    mo.ui.table(df_movement, selection=None, page_size=50),
                    mo.md(
                        "**Clutch Shift**: Improvement in win% when Last. **Close Shift**: Improvement in win% when Leading."
                    ),
                ]
            ),
            "💎 VP Analysis": mo.vstack(
                [
                    mo.ui.table(df_vp, selection=None, page_size=50),
                    mo.md(
                        "Correlations (Impact Scores). **Dice Imp**: How much high rolls matter for victory."
                    ),
                ]
            ),
            "⚡ Abilities": mo.ui.table(df_abilities, selection=None, page_size=50),
            "🔥 Dynamics": mo.ui.table(df_dynamics, selection=None, page_size=50),
        }
    )

    final_output = mo.md(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 2rem; width: 100%; min-height: 550px;">
        <div style="flex: 1 1 450px; min-width: 0; display: flex; justify-content: center; align-items: start;">{left_charts_ui}</div>
        <div style="flex: 1 1 400px; min-width: 0; overflow-x: auto;">{right_ui}</div>
    </div>
    """)
    final_output
    return


if __name__ == "__main__":
    app.run()
