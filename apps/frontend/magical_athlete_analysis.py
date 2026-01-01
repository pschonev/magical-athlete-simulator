import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import altair as alt
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
    )
    from magical_athlete_simulator.core.types import RacerName
    from magical_athlete_simulator.core.events import (
        MoveCmdEvent,
        WarpCmdEvent,
        TripCmdEvent,
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

    # 3. Load Data
    try:
        if not path_races.exists() or not path_res.exists():
            raise FileNotFoundError(
                f"Folder '{base_folder}' must contain 'races.parquet' and 'racer_results.parquet'"
            )

        df_racer_results = pl.read_parquet(path_res)
        df_races = pl.read_parquet(path_races)
        load_status = f"✅ Loaded from: `{base_folder}`"
    except Exception as e:
        df_racer_results = pl.DataFrame()
        df_races = pl.DataFrame()
        load_status = f"❌ Error: {str(e)}"
    return df_racer_results, df_races, load_status


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
    get_last_result_hash, set_last_result_hash = mo.state(
        None, allow_self_loops=True
    )
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
        start=1,
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
                set_step_idx(0) # Reset sim
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
                set_step_idx(0)
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

        table_rows.append(f"| {i+1}. {ui_racer} | {w_pos} | {move_grp} | {b_rem} |")

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
                    mo.hstack(
                        [add_racer_dropdown, add_button], justify="start", gap=1
                    ),
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
    if (
        racer_results_table.value is not None
        and racer_results_table.value.height > 0
    ):
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
            "Racer Results": mo.vstack([
                _header(), 
                racer_results_table
            ]),
            "Races": mo.vstack([
                _header(), 
                races_table
            ]),
            "Source": mo.vstack(
                [
                    mo.md("### Data Directory"),
                    mo.md("Select the folder containing `races.parquet` and `racer_results.parquet`."),
                    mo.hstack([results_folder_browser, reload_data_btn], align="center"),
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
        AbilityTriggerCounter,
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
        board=BOARD_DEFINITIONS.get(
            current_board_val, BOARD_DEFINITIONS["standard"]
        )(),
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

    ability_counter = AbilityTriggerCounter()
    sim_turn_counter = {"current": 0}


    def on_event(engine, event):
        t_idx = sim_turn_counter["current"]
        snapshot_recorder.on_event(engine, event, turn_index=t_idx)
        ability_counter.on_event(event)


    if hasattr(scenario.engine, "on_event_processed"):
        scenario.engine.on_event_processed = on_event

    engine = scenario.engine
    snapshot_recorder.capture(engine, "InitialState", turn_index=0)

    with mo.status.spinner(title="Simulating..."):
        while not engine.state.race_over:
            log_console.export_html(clear=True)
            t_idx = sim_turn_counter["current"]
            scenario.run_turn()
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
    curr_step: Any | Literal[0] = (
        current_data.global_step_index if current_data else 0
    )
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
def _(alt, df_racer_results, df_races, get_racer_color, mo, pl):
    # --- ANALYTICS DASHBOARD ---

    def _prepare_stats():
        # 1. Correlations (Impact Scores) - These remain valid per-racer
        corr_df = (
            df_racer_results
            .group_by("racer_name")
            .agg([
                pl.corr("ability_trigger_count", "final_vp").alias("ability_impact_score"),
                pl.corr("sum_dice_rolled", "final_vp").alias("dice_impact_score")
            ])
            .fill_nan(0)
        )

        # 2. Main Aggregations
        base_stats = (
            df_racer_results
            .with_columns(
                pl.when(pl.col("turns_taken") > 0).then(pl.col("turns_taken")).otherwise(1).alias("safe_turns"),
                pl.when(pl.col("final_vp") > 0).then(pl.col("final_vp")).otherwise(None).alias("safe_vp")
            )
            .group_by("racer_name")
            .agg([
                # Score
                pl.col("final_vp").mean().alias("mean_vp"),
                pl.col("final_vp").var().alias("var_vp"),

                # Ability Volume (Per Turn is fairer for short games)
                (pl.col("ability_trigger_count") / pl.col("safe_turns")).mean().alias("triggers_per_turn"),
                (pl.col("ability_self_target_count") / pl.col("safe_turns")).mean().alias("self_per_turn"),
                (pl.col("ability_target_count") / pl.col("safe_turns")).mean().alias("target_per_turn"),

                # Dice Volume (Per Turn)
                (pl.col("sum_dice_rolled") / pl.col("safe_turns")).mean().alias("dice_per_turn"),
                (pl.col("sum_dice_rolled") / pl.col("safe_vp")).mean().alias("dice_per_vp"),

                # Speed / Game Stats
                pl.col("turns_taken").mean().alias("avg_turns"),
                (pl.col("recovery_turns") / pl.col("safe_turns")).mean().alias("recovery_rate"),

                # Win/Place
                (pl.col("rank") == 1).sum().alias("cnt_1st"),
                (pl.col("rank") == 2).sum().alias("cnt_2nd"),
                pl.len().alias("races_run")
            ])
        )

        return base_stats.join(corr_df, on="racer_name", how="left").with_columns([
            (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
            (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd")
        ])

    def _build_quadrant_chart(stats_df, racers, colors, x_col, y_col, title, x_title, y_title, reverse_x=False):
        min_x, max_x = stats_df[x_col].min(), stats_df[x_col].max()
        min_y, max_y = stats_df[y_col].min(), stats_df[y_col].max()

        if min_x == max_x: max_x += 0.01
        if min_y == max_y: max_y += 0.01

        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2

        base = alt.Chart(stats_df).encode(
            color=alt.Color("racer_name", scale=alt.Scale(domain=racers, range=colors))
        )

        h_line = alt.Chart(pl.DataFrame({"y": [mid_y]})).mark_rule(strokeDash=[5,5], color="gray").encode(y="y")
        v_line = alt.Chart(pl.DataFrame({"x": [mid_x]})).mark_rule(strokeDash=[5,5], color="gray").encode(x="x")

        points = base.mark_circle(size=150).encode(
            x=alt.X(x_col, title=x_title, scale=alt.Scale(reverse=reverse_x, zero=False)),
            y=alt.Y(y_col, title=y_title, scale=alt.Scale(zero=False)),
            tooltip=["racer_name", x_col, y_col, "mean_vp", "races_run"]
        )
        return (h_line + v_line + points).properties(title=title, width=500, height=350)

    def _build_game_length_chart():
        gl_stats = (
            df_races
            .group_by(["board", "racer_count"])
            .agg(pl.col("total_turns").mean().alias("avg_duration"))
            .sort(["board", "racer_count"])
        )
        return alt.Chart(gl_stats).mark_bar().encode(
            x=alt.X("racer_count:O", title="Number of Racers"),
            y=alt.Y("avg_duration", title="Avg Turns to Finish"),
            column=alt.Column("board", title="Board Map"),
            color=alt.Color("board", legend=None),
            tooltip=["board", "racer_count", "avg_duration"]
        ).properties(title="Game Duration Analysis", width=150, height=300)

    # --- Execution ---
    if df_racer_results.height == 0:
        final_output = mo.md("⚠️ **No results loaded.**")
    else:
        stats = _prepare_stats()
        r_list = stats["racer_name"].unique().to_list()
        c_list = [get_racer_color(r) for r in r_list]

        # 1. Consistency
        c_consist = _build_quadrant_chart(
            stats, r_list, c_list, 
            "var_vp", "mean_vp", 
            "Consistency (Risk vs Reward)", "Consistency (Lower Var →)", "Avg Final VP", 
            reverse_x=True
        )

        # 2. Ability Value (Per Turn)
        c_ability = _build_quadrant_chart(
            stats, r_list, c_list, 
            "triggers_per_turn", "ability_impact_score", 
            "Ability Strategy (Freq vs Impact)", "Avg Triggers / Turn", "Impact (Corr Triggers/VP)",
            reverse_x=False
        )

        # 3. Dice Strategy (Per Turn)
        c_dice = _build_quadrant_chart(
            stats, r_list, c_list, 
            "dice_per_turn", "dice_impact_score", 
            "Dice Strategy (Volume vs Impact)", "Avg Dice Value / Turn", "Impact (Corr Dice/VP)",
            reverse_x=False
        )

        c_len = _build_game_length_chart()

        charts_ui = mo.ui.tabs({
            "🎯 Consistency": mo.ui.altair_chart(c_consist),
            "⚡ Ability Value": mo.ui.altair_chart(c_ability),
            "🎲 Dice Value": mo.ui.altair_chart(c_dice),
            "⏳ Game Length": mo.ui.altair_chart(c_len),
        }).style({"min-height": "450px", "width": "100%"})

        display_df = stats.select([
            pl.col("racer_name").alias("Racer"),
            pl.col("mean_vp").round(2).alias("Avg VP"),
            pl.col("var_vp").round(2).alias("VP Var"),
            pl.col("ability_impact_score").round(2).alias("Abil Imp"),
            pl.col("triggers_per_turn").round(2).alias("Trig/Turn"),
            pl.col("self_per_turn").round(2).alias("Self/Turn"),
            pl.col("target_per_turn").round(2).alias("Tgt/Turn"),
            pl.col("dice_per_vp").round(1).alias("Dice/VP"),
            pl.col("avg_turns").round(1).alias("Avg Turns"),
            (pl.col("pct_1st") * 100).round(1).alias("1st %"),
            (pl.col("pct_2nd") * 100).round(1).alias("2nd %"),
        ]).sort("Avg VP", descending=True)

        table_ui = mo.ui.table(display_df, selection=None, page_size=10)

        final_output = mo.hstack([
            charts_ui, 
            mo.vstack([mo.md("### 🔢 Aggregate Stats"), table_ui])
        ], widths=[5, 5], gap=2)
    final_output
    return


if __name__ == "__main__":
    app.run()
