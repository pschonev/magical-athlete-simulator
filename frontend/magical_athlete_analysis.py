# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "altair==6.0.0",
#     "marimo>=0.19.0",
#     "polars==1.36.1",
#     "sqlmodel==0.0.31",
# ]
# [tool.marimo.display]
# theme = "dark"
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(
    width="full",
    app_title="Magical Athlete Simulator",
    css_file="docs/magical_athlete_analysis.css",
)


@app.cell
def _():
    import sys

    print(sys.version)
    return


@app.cell
async def _():
    from __future__ import annotations

    import logging
    import math
    import micropip
    import re
    from typing import get_args, Any, Literal
    import dataclasses

    import altair as alt
    import marimo as mo
    from rich.console import Console
    from rich.logging import RichHandler

    MAGICAL_ATHLETE_SIMULATOR_VERSION = "0.7.1"
    await micropip.install(
        f"magical-athlete-simulator=={MAGICAL_ATHLETE_SIMULATOR_VERSION}",
        keep_going=True,
    )

    from magical_athlete_simulator.core.events import (
        MoveCmdEvent,
        TripCmdEvent,
        WarpCmdEvent,
    )
    from magical_athlete_simulator.core.types import RacerName
    from magical_athlete_simulator.engine.board import (
        BOARD_DEFINITIONS,
        VictoryPointTile,
        TripTile,
        MoveDeltaTile,
    )
    from magical_athlete_simulator.engine.logging import (
        GameLogHighlighter,
        RichMarkupFormatter,
    )
    from magical_athlete_simulator.simulation.telemetry import StepSnapshot

    # Imports
    from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
    return (
        Any,
        BOARD_DEFINITIONS,
        Console,
        GameLogHighlighter,
        GameScenario,
        Literal,
        MAGICAL_ATHLETE_SIMULATOR_VERSION,
        MoveCmdEvent,
        MoveDeltaTile,
        RacerConfig,
        RacerName,
        RichHandler,
        RichMarkupFormatter,
        StepSnapshot,
        TripCmdEvent,
        TripTile,
        VictoryPointTile,
        WarpCmdEvent,
        alt,
        dataclasses,
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

    # 1. Get location and check type
    notebook_loc = mo.notebook_location()
    is_url = isinstance(notebook_loc, mo._runtime.runtime.URLPath)

    default_results_path = (
        notebook_loc / "results" if is_url else notebook_loc / ".." / "results"
    )

    if is_url:
        # If running via URL (e.g. WASM), we can't use a local file browser
        results_folder_browser = None
        print(f"Running in URL mode. Base: {default_results_path}")
    else:
        # If local, create the browser
        # Ensure we convert Path to string for the widget
        results_folder_browser = mo.ui.file_browser(
            selection_mode="directory",
            label="Select Results Folder",
            initial_path=str(default_results_path),
        )
        print(f"Running locally. Default results path: {default_results_path}")
    return (
        Path,
        default_results_path,
        is_url,
        pl,
        reload_data_btn,
        results_folder_browser,
    )


@app.cell
def _(
    Path,
    default_results_path,
    is_url,
    pl,
    reload_data_btn,
    results_folder_browser,
):
    reload_data_btn.value

    # 1. Determine the Base Folder
    if is_url:
        # URL Mode: Use the URLPath object directly
        base_folder = default_results_path
    else:
        # Local Mode: Use browser value if selected, else default
        if results_folder_browser.value:
            base_folder = Path(results_folder_browser.value[0].path)
        else:
            base_folder = Path("results")

    # 2. Construct Paths
    # (The / operator works on both pathlib.Path and marimo URLPath objects)
    path_races = base_folder / "races.parquet"
    path_res = base_folder / "racer_results.parquet"
    path_positions = base_folder / "race_positions.parquet"

    # 3. Load Data
    try:
        if not is_url:  # noqa: SIM102
            if (
                not Path(path_races).exists()
                or not Path(path_res).exists()
                or not Path(path_positions).exists()
            ):
                raise FileNotFoundError(
                    f"Folder '{base_folder}' must contain 'races.parquet', 'racer_results.parquet' and 'race_positions.parquet'"
                )

        if is_url:
            import io
            import urllib.request
            import pyarrow as pa

            def _wasm_read_parquet(path: Path) -> pl.DataFrame:
                with urllib.request.urlopen(path) as response:
                    parquet_bytes = response.read()
                return pl.read_parquet(io.BytesIO(parquet_bytes), use_pyarrow=True)

            df_racer_results = _wasm_read_parquet(path_res)
            df_races = _wasm_read_parquet(path_races)
            df_positions = _wasm_read_parquet(path_positions)
        else:
            df_racer_results = pl.read_parquet(path_res)
            df_races = pl.read_parquet(path_races)
            df_positions = pl.read_parquet(path_positions)
        load_status = f"✅ Loaded from: `{base_folder}`"

    except Exception as e:
        df_racer_results = pl.DataFrame()
        df_races = pl.DataFrame()
        df_positions = pl.DataFrame()
        load_status = f"❌ Error: {str(e)}"
        print(load_status)

    print(
        f"df_racer_results: {df_racer_results.height} rows, path `{path_races}` and columns: {df_racer_results.columns}"
    )
    print(
        f"df_racer_results: {df_races.height} rows, path `{path_res}` and columns: {df_races.columns}"
    )
    print(
        f"df_racer_results: {df_positions.height} rows, path `{path_positions}` and columns: {df_positions.columns}"
    )
    return df_positions, df_racer_results, df_races, load_status


@app.cell
def _(df_racer_results, df_races, mo, pl):
    import json  # Required for the WASM fix

    HASH_COL = "config_hash"
    BG_COLOR = "#181c1a"

    # 1. Get unique racers for column headers
    unique_racers = sorted(df_racer_results.get_column("racer_name").unique().to_list())

    # 2. FIX DATA TYPE: Decode JSON -> List (WASM Compatible)
    df_races_clean = df_races.with_columns(
        pl.col("racer_names")
        .cast(pl.String)
        .map_elements(json.loads, return_dtype=pl.List(pl.String))
        .alias("racer_names")
    )

    # 3. EXPAND: Create Display & Boolean Columns
    exprs = [
        # Readable string for searching
        pl.col("racer_names").list.join(", ").alias("roster_display")
    ]
    for r in unique_racers:
        exprs.append(pl.col("racer_names").list.contains(r).alias(f"Has {r}"))

    df_races_expanded = df_races_clean.with_columns(exprs)

    # 4. DEFINE COLUMN GROUPS

    # A. Priority Columns (Frozen on left)
    priority_cols = [
        "roster_display",
        "board",
        "racer_count",
        "seed",
        "error_code",
        "total_turns",
    ]

    # B. Matrix Columns (The boolean flags)
    matrix_cols = [f"Has {r}" for r in unique_racers]

    # C. Columns to Hide/Drop explicitly
    drop_cols = ["timestamp"]  # Redundant with created_at

    # D. "The Rest" - Calculate dynamically
    other_cols = [
        c
        for c in df_races_expanded.columns
        if c not in priority_cols and c not in matrix_cols and c not in drop_cols
    ]

    racer_results_table = mo.ui.table(
        df_racer_results.sort(["config_hash", "racer_id"]).select(
            pl.all().exclude(HASH_COL), pl.col(HASH_COL)
        ),
        selection="single",
        label="Racer Results",
    )

    races_table = mo.ui.table(
        df_races_expanded.select(priority_cols + matrix_cols + other_cols),
        selection="single",
        label="Races (Matrix View)",
        freeze_columns_left=priority_cols,
    )
    return BG_COLOR, df_races_clean, racer_results_table, races_table


@app.cell
def _(BG_COLOR, math):
    from typing import NamedTuple

    # --- DATA STRUCTURES ---
    class RacerPalette(NamedTuple):
        primary: str
        secondary: str | None = None
        outline: str = "#000000"

    # --- CONSTANTS: RACERS ---
    # Colors derived from the "Magical Athlete" magnets
    RACER_PALETTES = {
        # --- THE PINKS/REDS ---
        "HugeBaby": RacerPalette("#FFB7C5", "#FFFFFF", "#39FF14"),  # Pastel Pink (Baby)
        "Scoocher": RacerPalette("#8B4513", "#FF0000", "#800080"),  # Brown (Snail/Dog?)
        "Genius": RacerPalette("#FF0000", "#0000FF", "#FFFF00"),  # Bright Red (Shirt)
        # --- THE YELLOWS (Fixed the conflict) ---
        "Banana": RacerPalette("#FFE135", "#000000", "#800080"),  # Standard Yellow
        # Skipper: Swapped Yellow skin -> Blue Coat
        "Skipper": RacerPalette(
            "#1A4099", "#FFD700", "#800080"
        ),  # Royal Blue (Primary)
        # PartyAnimal: Swapped Yellow skin -> Green Shirt
        "PartyAnimal": RacerPalette(
            "#32CD32", "#FFFF00", "#FF00FF"
        ),  # Lime Green (Primary)
        # Romantic: Swapped Yellow skin -> Pink/Purple Accents
        "Romantic": RacerPalette("#DA70D6", "#FFFF00", "#800080"),  # Orchid (Primary)
        # Mastermind: Swapped Yellow skin -> Purple Accents
        "Mastermind": RacerPalette("#800080", "#FFD700", "#008000"),  # Purple (Primary)
        # --- THE BLUES/GREENS ---
        "Copycat": RacerPalette(
            "#00BFFF", "#FFFFFF", "#FFA500"
        ),  # Deep Sky Blue (Cat?)
        "Magician": RacerPalette(
            "#191970", "#9370DB", "#FFA500"
        ),  # Midnight Blue (To distinguish from Copycat)
        "Gunk": RacerPalette("#556B2F", "#8B4513", "#FFA500"),  # Olive Drab
        # --- OTHERS ---
        "Centaur": RacerPalette("#D2691E", "#8B4513", "#800080"),  # Chocolate
        "FlipFlop": RacerPalette("#9370DB", "#FFFF00", "#FF0000"),  # Medium Purple
    }

    FALLBACK_PALETTES = [
        RacerPalette("#8A2BE2", None, "#000"),
        RacerPalette("#5F9EA0", None, "#000"),
        RacerPalette("#D2691E", None, "#000"),
    ]

    # --- CONSTANTS: BOARD THEME ---
    BOARD_THEME = {
        "background": BG_COLOR,
        "tile_1": "#2d3432",
        "tile_2": "#363e3b",
        "stroke_default": "#555",
        "text_default": "#aaa",
        # Special Tiles
        "start_fill": "#4CAF50",
        "start_text": "#4CAF50",
        "start_stroke": "#D3D3D3",  # [NEW] Light Grey
        "goal_fill": "#F44336",
        "goal_text": "#F44336",
        "goal_stroke": "#C5A059",  # [NEW] Muted Golden
        "trip_fill": "#111111",
        "trip_text": "#F44336",
        "vp_fill": "#81D4FA",
        "vp_text": "#000000",
        "move_pos_fill": "#A5D6A7",
        "move_pos_text": "#1B5E20",
        "move_neg_fill": "#EF9A9A",
        "move_neg_text": "#B71C1C",
    }

    # --- HELPER FUNCTIONS ---
    def get_racer_palette(name: str) -> RacerPalette:
        if name in RACER_PALETTES:
            return RACER_PALETTES[name]
        return FALLBACK_PALETTES[hash(name) % len(FALLBACK_PALETTES)]

    def get_racer_color(name: str) -> str:
        return get_racer_palette(name).primary

    def generate_racetrack_positions(
        num_spaces, start_x, start_y, straight_len, radius
    ):
        """
        Generates a Clockwise stadium track starting from the Top-Left straight.
        """
        positions = []
        perimeter = (2 * straight_len) + (2 * math.pi * radius)
        step_distance = perimeter / num_spaces

        right_circle_cx = start_x + straight_len
        right_circle_cy = start_y + radius
        left_circle_cx = start_x
        left_circle_cy = start_y + radius

        for i in range(num_spaces):
            dist = i * step_distance

            # 1. Top Straight (Moving Right)
            if dist < straight_len:
                x = start_x + dist
                y = start_y
                angle = 0
            # 2. Right Curve (Moving Clockwise/Down)
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                fraction = arc_dist / (math.pi * radius)
                theta = (-math.pi / 2) + (fraction * math.pi)
                x = right_circle_cx + radius * math.cos(theta)
                y = right_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90
            # 3. Bottom Straight (Moving Left)
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x = (start_x + straight_len) - top_dist
                y = start_y + (2 * radius)
                angle = 180
            # 4. Left Curve (Moving Clockwise/Up)
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                fraction = arc_dist / (math.pi * radius)
                theta = (math.pi / 2) + (fraction * math.pi)
                x = left_circle_cx + radius * math.cos(theta)
                y = left_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90

            positions.append((x, y, angle))

        return positions

    # Constants
    NUM_TILES = 31
    board_positions = generate_racetrack_positions(NUM_TILES, 120, 150, 350, 100)
    return BOARD_THEME, board_positions, get_racer_color, get_racer_palette


@app.cell
def _(
    BOARD_THEME,
    MoveDeltaTile,
    StepSnapshot,
    TripTile,
    VictoryPointTile,
    get_racer_palette,
    math,
):
    # --- RENDERER (RAW / UNPATCHED) ---
    def render_game_track(turn_data: StepSnapshot, positions_map, board=None):
        import html as _html

        # --- VISUALIZATION CONSTANTS ---
        MAIN_RADIUS = 9.0
        SECONDARY_RADIUS = 8.0
        OUTLINE_WIDTH = 1.5
        SECONDARY_WIDTH = 1.5
        TEXT_STROKE_WIDTH = "4px"

        if not turn_data:
            return "<p>No Data</p>"

        svg_elements = []

        # Dimensions & Scaling
        W, H = 1000, 600
        scale_factor = 1.45
        trans_x = 75
        trans_y = -60
        rw, rh = 50, 30

        # 1. Track Groups
        track_group_start = (
            f'<g transform="translate({trans_x}, {trans_y}) scale({scale_factor})">'
        )

        # 2. Track Spaces
        for i, (cx, cy, rot) in enumerate(positions_map):
            transform = f"rotate({rot}, {cx}, {cy})"

            # --- 1. DEFAULT STYLES ---
            is_start = i == 0
            is_end = i == len(positions_map) - 1

            if (i // 2) % 2 == 0:
                fill_color = BOARD_THEME["tile_1"]
            else:
                fill_color = BOARD_THEME["tile_2"]

            stroke_color = BOARD_THEME["stroke_default"]
            stroke_width = "2"

            text_content = str(i)
            text_fill = BOARD_THEME["text_default"]
            font_weight = "bold"
            font_size = "10"

            # --- 2. SPECIAL TILE LOGIC ---
            if board:
                mods = board.static_features.get(i, [])
                for mod in mods:
                    if isinstance(mod, VictoryPointTile):
                        fill_color = BOARD_THEME["vp_fill"]
                        text_content = "VP"
                        text_fill = BOARD_THEME["vp_text"]
                    elif isinstance(mod, TripTile):
                        fill_color = BOARD_THEME["trip_fill"]
                        text_content = "T"
                        text_fill = BOARD_THEME["trip_text"]
                        font_size = "16"
                    elif isinstance(mod, MoveDeltaTile):
                        d = mod.delta
                        if d > 0:
                            fill_color = BOARD_THEME["move_pos_fill"]
                            text_content = f"+{d}"
                            text_fill = BOARD_THEME["move_pos_text"]
                        elif d < 0:
                            fill_color = BOARD_THEME["move_neg_fill"]
                            text_content = f"{d}"
                            text_fill = BOARD_THEME["move_neg_text"]

            # --- 3. START / END OVERRIDES ---
            if is_start:
                stroke_color = BOARD_THEME["start_stroke"]
                stroke_width = "4"
                if text_content == str(i):
                    text_content = "S"
                    text_fill = BOARD_THEME["start_text"]
            elif is_end:
                stroke_color = BOARD_THEME["goal_stroke"]
                stroke_width = "4"
                if text_content == str(i):
                    text_content = "G"
                    text_fill = BOARD_THEME["goal_text"]

            svg_elements.append(
                f'<rect x="{cx - rw / 2:.1f}" y="{cy - rh / 2:.1f}" width="{rw}" height="{rh}" '
                f'fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" '
                f'transform="{transform}" rx="4" />'
            )

            svg_elements.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" font-family="sans-serif" '
                f'font-size="{font_size}" font-weight="{font_weight}" '
                f'text-anchor="middle" fill="{text_fill}" transform="{transform}">{text_content}</text>'
            )

        # 3. Racers
        occupancy = {}
        for idx, pos in enumerate(turn_data.positions):
            draw_pos = min(pos, len(positions_map) - 1)
            name = turn_data.names[idx]
            palette = get_racer_palette(name)

            mods = turn_data.modifiers
            abils = turn_data.abilities
            mod_str = str(mods[idx]) if idx < len(mods) else "[]"
            abil_str = str(abils[idx]) if idx < len(abils) else "[]"
            tooltip_text = f"{name} (ID: {idx})\nVP: {turn_data.vp[idx]}\nTripped: {turn_data.tripped[idx]}\nAbils: {abil_str}\nMods: {mod_str}"

            occupancy.setdefault(draw_pos, []).append(
                {
                    "name": name,
                    "palette": palette,
                    "is_current": (idx == turn_data.current_racer),
                    "tripped": turn_data.tripped[idx],
                    "tooltip": tooltip_text,
                }
            )

        # Render Racers
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

                vis_dx = cx - bx
                vis_dy = cy - by
                text_anchor = "middle"
                dy_text = 24
                tx = cx
                ty = cy

                if count > 1:
                    if abs(vis_dy) > abs(vis_dx):
                        if vis_dy < 0:
                            dy_text = -14
                        else:
                            dy_text = 24
                    else:
                        dy_text = 5
                        if vis_dx < 0:
                            text_anchor = "end"
                            tx = cx - 14
                        else:
                            text_anchor = "start"
                            tx = cx + 14

                pal = racer["palette"]
                stroke = pal.outline

                svg_elements.append(f"<g>")
                svg_elements.append(f"<title>{_html.escape(racer['tooltip'])}</title>")

                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{MAIN_RADIUS}" fill="{pal.primary}" stroke="{stroke}" stroke-width="{OUTLINE_WIDTH}" />'
                )

                if pal.secondary:
                    svg_elements.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{SECONDARY_RADIUS}" fill="none" stroke="{pal.secondary}" stroke-width="{SECONDARY_WIDTH}" />'
                    )

                svg_elements.append(
                    f'<text x="{tx}" y="{ty}" dy="{dy_text}" font-family="sans-serif" font-size="13" '
                    f'font-weight="900" text-anchor="{text_anchor}" fill="{pal.primary}" '
                    f'style="paint-order: stroke; stroke: #000; stroke-width: {TEXT_STROKE_WIDTH};">'
                    f"{_html.escape(racer['name'])}</text>"
                )

                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{cx}" y="{cy}" dy="5" fill="#ff0000" font-weight="bold" font-size="14" text-anchor="middle">X</text>'
                    )
                svg_elements.append(f"</g>")

        svg_elements.append("</g>")

        # 4. Center Display (No Box)
        center_x = (100 + 500) / 2 * scale_factor + trans_x
        center_y = (350 - 100) * scale_factor + trans_y

        active_idx = turn_data.current_racer
        active_name = turn_data.names[active_idx]
        active_pal = get_racer_palette(active_name)
        roll = turn_data.last_roll

        # Active Racer Name (Floating)
        svg_elements.append(
            f'<text x="{center_x}" y="{center_y - 15}" font-size="28" font-weight="bold" text-anchor="middle" fill="{active_pal.primary}" style="paint-order: stroke; stroke: {active_pal.outline}; stroke-width: 2px; filter: drop-shadow(0px 0px 2px black);">{_html.escape(active_name)}</text>'
        )

        if roll:
            svg_elements.append(
                f'<text x="{center_x}" y="{center_y + 35}" font-size="40" font-weight="bold" text-anchor="middle" fill="#eee" >🎲 {roll}</text>'
            )
        elif turn_data.turn_index > 0:
            svg_elements.append(
                f'<text x="{center_x}" y="{center_y + 35}" font-size="60" font-weight="bold" text-anchor="middle" fill="#ff0000" >X</text>'
            )

        return f"""<svg width="{W}" height="{H}" style="background:{BOARD_THEME["background"]};"> 
                {track_group_start}
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

    # --- NEW: Share & Load Logic ---
    encoded_config_input = mo.ui.text(
        label="Paste Encoded Config", placeholder="eyJ...", full_width=True
    )

    def _on_load_click(_):
        """Parse encoded string using the existing class and update UI state."""
        val = encoded_config_input.value
        if not val:
            return

        from magical_athlete_simulator.simulation.hashing import GameConfiguration

        try:
            # 1. Decode using your existing Single Source of Truth
            config = GameConfiguration.from_encoded(val)

            # 2. Update the Shared State directly
            set_seed(config.seed)
            set_board(config.board)
            set_selected_racers(list(config.racers))
            set_saved_positions({n: 0 for n in config.racers})
            set_use_scripted_dice(False)
            set_step_idx(0)  # Reset simulation
        except Exception:
            pass

    load_encoded_btn = mo.ui.button(label="Load Configuration", on_click=_on_load_click)

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
        def _move(_):
            roster = list(get_selected_racers())
            new_index = index + direction
            if 0 <= new_index < len(roster):
                roster[index], roster[new_index] = roster[new_index], roster[index]
                set_selected_racers(roster)
                set_step_idx(0)

        return _move

    # 4. Action Buttons
    action_buttons = {}
    for i, ui_racer in enumerate(current_roster):
        btn_remove = mo.ui.button(
            label="✖",
            on_click=lambda _, r=ui_racer: (
                set_saved_positions(_snapshot_values(exclude=r)),
                set_selected_racers(lambda cur: [x for x in cur if x != r]),
                set_step_idx(0),
            ),
            disabled=(len(current_roster) <= 1),
        )
        btn_up = mo.ui.button(label="↑", on_click=move_racer(i, -1), disabled=(i == 0))
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
        encoded_config_input,
        load_encoded_btn,
        racer_table,
        reset_button,
        scenario_seed,
        use_scripted_dice_ui,
    )


@app.cell
def _(board_selector, current_roster, mo, scenario_seed):
    from magical_athlete_simulator.simulation.hashing import GameConfiguration

    # Generate string from current state
    current_config_obj = GameConfiguration(
        racers=tuple(current_roster),
        board=board_selector.value,
        seed=scenario_seed.value,
    )

    share_widget = mo.ui.text_area(
        value=current_config_obj.encoded,
        disabled=True,  # Read-only
        full_width=True,
        rows=5,
    )
    return (share_widget,)


@app.cell
def _(
    add_button,
    add_racer_dropdown,
    board_selector,
    debug_mode_ui,
    dice_input,
    encoded_config_input,
    load_encoded_btn,
    mo,
    racer_table,
    reset_button,
    results_tabs,
    scenario_seed,
    share_widget,
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
            ).style({"overflow-x": "auto", "max-width": "100%"}),
            mo.vstack(
                [
                    results_tabs,
                    mo.hstack(
                        [
                            mo.md("Enter encoded config: "),
                            encoded_config_input,
                            load_encoded_btn,
                            mo.md("Copy encoded config: "),
                            share_widget,
                        ],
                        justify="start",
                    ),
                ]
            ).style({"overflow-x": "auto", "max-width": "100%"}),
        ],
    )
    return


@app.cell
def _(
    df_races_clean,
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
        # Use the CLEANED races frame so racer_names is already a list
        filtered = df_races_clean.filter(pl.col("config_hash") == curr_res_hash)
        if filtered.height > 0:
            target_config = filtered.row(0, named=True)

    # 4. Apply Configuration (if any change detected)
    if target_config:
        raw_names = target_config.get("racer_names")

        # Now always expect a list from both paths
        if isinstance(raw_names, list):
            new_roster = [str(n) for n in raw_names]
        else:
            new_roster = []

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
    MAGICAL_ATHLETE_SIMULATOR_VERSION,
    load_status,
    mo,
    racer_results_table,
    races_table,
    reload_data_btn,
    results_folder_browser,
):
    def _header():
        return mo.hstack(
            [mo.md(f"**v{MAGICAL_ATHLETE_SIMULATOR_VERSION}**"), reload_data_btn],
            justify="end",
            gap=1,
        )

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
    dataclasses,
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
        MetricsAggregator,
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
    metrics_aggregator = MetricsAggregator(config_hash="interactive-session")
    metrics_aggregator.initialize_racers(scenario.engine)

    # FIX 1: Start the counter at 1.
    # Turn 0 is reserved for "Board Setup". Turn 1 is the first actual move.
    sim_turn_counter = {"current": 1}

    def on_event(engine, event):
        t_idx = sim_turn_counter["current"]
        snapshot_recorder.on_event(engine, event, turn_index=t_idx)
        metrics_aggregator.on_event(event)

    if hasattr(scenario.engine, "on_event_processed"):
        scenario.engine.on_event_processed = on_event
    # --- CHANGED BLOCK END ---

    engine = scenario.engine

    # FIX 2: Capture Initial State as Turn 0
    snapshot_recorder.capture(engine, "InitialState", turn_index=0)

    with mo.status.spinner(title="Simulating..."):
        while not engine.state.race_over:
            log_console.export_html(clear=True)
            t_idx = sim_turn_counter["current"]

            actual_racer_idx = engine.state.current_racer_idx
            pre_turn_serial = engine.state.roll_state.serial_id

            scenario.run_turn()

            post_turn_serial = engine.state.roll_state.serial_id

            metrics_aggregator.on_turn_end(engine, turn_index=t_idx)
            snapshot_recorder.on_turn_end(engine, turn_index=t_idx)

            last_snap = snapshot_recorder.step_history[-1]

            # Fix 1: Ensure snapshot points to the actor
            updates = {"current_racer": actual_racer_idx}

            # Fix 2: "Red X" logic
            # We check (t_idx > 1) because Turn 1 is the first roll.
            # If a "Recovery" happens on Turn 2+, the serial won't change.
            if t_idx > 1 and post_turn_serial == pre_turn_serial:
                updates["last_roll"] = 0

            fixed_snap = dataclasses.replace(last_snap, **updates)
            snapshot_recorder.step_history[-1] = fixed_snap

            sim_turn_counter["current"] += 1
            if len(snapshot_recorder.step_history) > 1000:
                break

    step_history: list[StepSnapshot] = snapshot_recorder.step_history
    turn_map = snapshot_recorder.turn_map

    info_md = mo.md(
        f"✅ **Simulation complete!** {len(current_roster)} racers, {sim_turn_counter['current'] - 1} turns"
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
        next_turn_step_val = turn_map[next_turn_target][-1]
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
        start=-1,
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
def _(BG_COLOR, current_data, current_turn_idx, mo, step_history, turn_map):
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
                bg, border, opacity = BG_COLOR, "#333", "0.5"
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
                    f"""<div id="{container_id}" style="height:750px; overflow-y:auto; background:{BG_COLOR}; font-family:monospace;">{full_html}</div>"""
                ),
                mo.iframe(scroll_script, width="0", height="0"),
            ]
        )
    return (log_ui,)


@app.cell
def _(
    BOARD_DEFINITIONS,
    board_positions,
    current_data,
    get_board,
    log_ui,
    mo,
    nav_ui,
    render_game_track,
):
    # --- COMPOSITION ---
    if not current_data:
        layout = mo.md("Waiting for simulation...")
    else:
        factory = BOARD_DEFINITIONS.get(get_board())
        if not factory:
            factory = BOARD_DEFINITIONS["standard"]
        board_instance = factory()

        # 3. Render
        track_svg = mo.Html(
            render_game_track(current_data, board_positions, board=board_instance)
        )
        layout = mo.hstack(
            [mo.vstack([nav_ui, track_svg], align="center"), log_ui],
            gap=2,
            align="start",
        )
    layout
    return


@app.cell
def _():
    from magical_athlete_simulator.core.registry import RACER_ABILITIES
    from magical_athlete_simulator.racers import get_ability_classes
    from magical_athlete_simulator.core.agent import (
        BooleanInteractive,
        SelectionInteractive,
    )

    ability_classes = get_ability_classes()

    # Filter: Keep racer if NONE of their abilities are interactive
    # This checks if the racer class implements the interactive protocols
    automatic_racers_list = [
        racer
        for racer, abilities in RACER_ABILITIES.items()
        if not any(
            issubclass(
                ability_classes.get(a),
                (BooleanInteractive, SelectionInteractive),
            )
            for a in abilities
            if ability_classes.get(a)
        )
    ]
    return (automatic_racers_list,)


@app.cell
def _(mo):
    # last_run_config starts as None.
    # It only updates when "Run Analysis" is clicked.
    last_run_config, set_last_run_config = mo.state(None)
    return last_run_config, set_last_run_config


@app.cell
def _(mo):
    select_auto_racers_btn = mo.ui.run_button(
        label="🤖 Select automatic racers",
        kind="neutral",
        tooltip="Select all racers that do not require human/AI decisions.",
    )
    return (select_auto_racers_btn,)


@app.cell
def _(
    automatic_racers_list,
    df_racer_results,
    df_races,
    mo,
    select_auto_racers_btn,
    set_last_run_config,
):
    # 1. Prepare Options from RAW Data
    all_racers = sorted(df_racer_results.get_column("racer_name").unique().to_list())
    all_boards = sorted(df_races.get_column("board").unique().to_list())
    all_counts = sorted(df_races.get_column("racer_count").unique().to_list())

    # 2. Handle Auto-Select Logic
    # We can safely read .value because the button was defined in a previous cell
    if select_auto_racers_btn.value:
        _current_selection = [r for r in automatic_racers_list if r in all_racers]
    else:
        _current_selection = all_racers

    # 3. Define Filter Widgets
    ui_racers = mo.ui.multiselect(
        options=all_racers,
        value=_current_selection,
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

    matchup_metric_toggle = mo.ui.switch(value=True, label="Show Percentage Shift")

    # 4. Define "Run Analysis" Button with Callback
    def _submit_filters(_):
        set_last_run_config(
            {
                "racers": ui_racers.value,
                "boards": ui_boards.value,
                "counts": ui_counts.value,
            }
        )

    run_computation_btn = mo.ui.button(
        label="🚀 Run Analysis",
        kind="success",
        on_click=_submit_filters,
        tooltip="Click to process data with current filters.",
    )
    return (
        matchup_metric_toggle,
        run_computation_btn,
        ui_boards,
        ui_counts,
        ui_racers,
    )


@app.cell
def _(
    last_run_config,
    mo,
    run_computation_btn,
    select_auto_racers_btn,
    ui_boards,
    ui_counts,
    ui_racers,
):
    # A. Check for "Stale" state (Widgets != Last Run)
    stale_warning = None  # Initialize to None, not empty markdown

    if last_run_config() is not None:
        is_stale = (
            ui_racers.value != last_run_config()["racers"]
            or ui_boards.value != last_run_config()["boards"]
            or ui_counts.value != last_run_config()["counts"]
        )
        if is_stale:
            # FIX: Removed the trailing comma that made this a Tuple
            stale_warning = mo.md(
                '<div style="color: #DC143C; margin-bottom: 0.75rem;">⚠️ <b>Filters Changed:</b> The dashboard below is showing old data. Click <b>🚀 Run Analysis</b> to update.</div>',
            )

    # B. Layout
    header = mo.md(
        """
        <hr style="margin: 1.25rem 0;" />
        <h2 style="margin: 0 0 0.5rem 0;">Aggregated Dashboard</h2>
        <div style="color: #aaa; margin-bottom: 0.75rem;">
          Filter races by roster, board, and player count (applies to all aggregated charts/tables below). ⚠️ Does not include races with error_code or Copycat+Scoocher on Standard Board (due to loops).
        </div>
        """
    )

    mo.vstack(
        [
            header,
            mo.hstack(
                [
                    ui_racers,
                    select_auto_racers_btn,
                    ui_counts,
                    ui_boards,
                    run_computation_btn,
                ],
                justify="start",
            ),
            stale_warning if stale_warning else mo.md(""),
        ]
    )
    return


@app.cell
def _(df_positions, df_racer_results, df_races, last_run_config, mo, pl):
    # 1. Gate: If never run, stop here.
    if last_run_config() is None:
        mo.stop(
            True,
            mo.md(
                '<div style="color: #DC143C; margin-bottom: 0.75rem;">ℹ️ <b>Waiting for Input:</b> Adjust filters above and click <b>🚀 Run Analysis</b> to generate stats.<div>'
            ),
        )

    # 2. Unwrap the specific config used for THIS run
    selected_racers = list(last_run_config()["racers"])
    selected_counts = list(last_run_config()["counts"])
    selected_boards = list(last_run_config()["boards"])

    # 3. Validation Logic
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

    # 4. Apply Filters
    if error_msg is None:
        # Filter Races by metadata
        races_bc = df_races.filter(
            pl.col("board").is_in(selected_boards)
            & pl.col("racer_count").is_in(selected_counts)
            & pl.col("error_code").is_null()
            & pl.col("total_turns").gt(1)  # remove Copycat + Scoocher stuff
        ).select(["config_hash", "board", "racer_count"])

        # Roster Check
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

    # 5. Validation Note
    if error_msg:
        mo.output.replace(
            mo.md(
                f"<div style='color:#ff6b6b; font-weight:600; margin-top:0.5rem;'>⚠ {error_msg}</div>"
            )
        )
    return (
        df_positions_f,
        df_racer_results_f,
        df_races_f,
        selected_boards,
        selected_counts,
        selected_racers,
    )


@app.cell
def _(
    df_positions_f,
    df_racer_results_f,
    df_races_f,
    mo,
    pl,
    selected_boards,
    selected_counts,
    selected_racers,
):
    # A. Check Data Load
    if df_positions_f.height == 0:
        mo.stop(True, mo.md("⚠️ **No data matches filters.**"))

    # Apply Racer Filter to Results (Optimization)
    df_racer_results_filtered = df_racer_results_f.filter(
        pl.col("racer_name").is_in(selected_racers)
    )

    # --- HELPER FUNCTIONS ---
    def unpivot_positions(df_flat: pl.DataFrame) -> pl.DataFrame:
        return (
            df_flat.unpivot(
                index=["config_hash", "turn_index", "current_racer_id"],
                on=["pos_r0", "pos_r1", "pos_r2", "pos_r3", "pos_r4", "pos_r5"],
                variable_name="racer_slot",
                value_name="position",
            )
            .with_columns(
                pl.col("racer_slot")
                .str.extract(r"pos_r(\d+)", 1)
                .cast(pl.Int64)
                .alias("racer_id")
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
        # --- A. PREPARE METRICS ---
        df_long = unpivot_positions(df_positions_f)

        # 1. TRUTH SOURCE: Global Win Rates
        global_win_rates = (
            df_racer_results_filtered.group_by("racer_name")
            .agg(
                (pl.col("rank") == 1).sum().alias("total_wins"),
                pl.len().alias("total_races"),
            )
            .with_columns(
                (pl.col("total_wins") / pl.col("total_races")).alias("global_win_rate")
            )
        )

        # 2. Tightness & Volatility (race-level)
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

        # --- NEW: GROSS SPEED (accurate) ---
        df_pos_sorted = df_long.sort(["config_hash", "racer_id", "turn_index"])

        df_gross_dist = (
            df_pos_sorted.with_columns(
                pl.col("position")
                .shift(1)
                .over(["config_hash", "racer_id"])
                .alias("prev_pos")
            )
            .with_columns(
                (pl.col("position") - pl.col("prev_pos").fill_null(0)).alias(
                    "move_delta"
                )
            )
            .filter(pl.col("move_delta") > 0)
            .group_by(["config_hash", "racer_id"])
            .agg(pl.col("move_delta").sum().alias("gross_distance"))
        )

        # --- NEW: Late-game snapshot (66%) + position-vs-median ---
        winner_turns = (
            df_racer_results_filtered.filter(pl.col("rank") == 1)
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

        df_snap_pos = df_long.join(snapshot_target, on="config_hash").filter(
            pl.col("turn_index") == pl.col("snapshot_turn")
        )

        df_race_medians = df_snap_pos.group_by("config_hash").agg(
            pl.col("position").median().alias("median_pos_at_snap")
        )

        df_late_game = (
            df_snap_pos.join(df_race_medians, on="config_hash")
            .with_columns(
                (pl.col("position") - pl.col("median_pos_at_snap")).alias(
                    "pos_diff_from_median"
                )
            )
            .select(["config_hash", "racer_id", "pos_diff_from_median"])
        )

        # 3. Race environment stats
        race_environment_stats = df_racer_results_filtered.group_by("config_hash").agg(
            (pl.col("ability_trigger_count").sum() / pl.col("racer_id").count()).alias(
                "race_avg_triggers"
            ),
            (pl.col("recovery_turns").sum() / pl.col("turns_taken").sum()).alias(
                "race_avg_trip_rate"
            ),
        )

        stats_races = (
            df_races_f.join(tightness_calc, on="config_hash", how="left")
            .join(volatility_calc, on="config_hash", how="left")
            .join(race_environment_stats, on="config_hash", how="left")
            .fill_null(0)
        )

        # 4. Results enriched with movement features
        stats_results = (
            df_racer_results_filtered.join(
                df_gross_dist, on=["config_hash", "racer_id"], how="left"
            )
            .join(df_late_game, on=["config_hash", "racer_id"], how="left")
            .with_columns(
                # 1. Fill basic nulls
                pl.col("gross_distance").fill_null(0),
                pl.col("pos_diff_from_median").fill_null(0),
            )
            .with_columns(
                # 3. THE FIX: Convert 0 -> Null (None)
                # This tells Polars "Do not count this row in averages"
                pl.when(pl.col("turns_taken") <= 0)
                .then(None)
                .otherwise(pl.col("turns_taken"))
                .alias("total_turns_clean"),
                pl.when(pl.col("rolling_turns") <= 0)
                .then(None)
                .otherwise(pl.col("rolling_turns"))
                .alias("rolling_turns_clean"),
            )
            .with_columns(
                # 4. Apply Specific Denominators
                # A. MOVEMENT (Uses Total Turns)
                # If total_turns is Null, speed becomes Null (ignored in avg), which is correct.
                (pl.col("gross_distance") / pl.col("total_turns_clean")).alias(
                    "speed_gross"
                ),
                # B. ABILITIES (Uses Total Turns)
                (pl.col("ability_trigger_count") / pl.col("total_turns_clean")).alias(
                    "triggers_per_turn"
                ),
                (
                    pl.col("ability_self_target_count") / pl.col("total_turns_clean")
                ).alias("self_per_turn"),
                (pl.col("ability_target_count") / pl.col("total_turns_clean")).alias(
                    "target_per_turn"
                ),
                # C. DICE (Uses Rolling Turns)
                # Only calculated if they actually rolled.
                (pl.col("sum_dice_rolled") / pl.col("rolling_turns_clean")).alias(
                    "dice_per_rolling_turn"
                ),
                (pl.col("sum_dice_rolled_final") / pl.col("rolling_turns_clean")).alias(
                    "final_roll_per_rolling_turn"
                ),
            )
            .with_columns(
                (
                    (pl.col("gross_distance") - pl.col("sum_dice_rolled"))
                    / pl.col("total_turns_clean")
                ).alias("non_dice_movement")
            )
        )

        # --- UPDATED: Consistency = within 1 std dev of mean (per racer) ---
        racer_mu_sigma = stats_results.group_by("racer_name").agg(
            pl.col("final_vp").mean().alias("mean_vp_mu"),
            pl.col("final_vp").std().fill_null(0).alias("std_vp_sigma"),
        )

        consistency_calc = (
            stats_results.join(racer_mu_sigma, on="racer_name", how="left")
            .with_columns(
                pl.when(pl.col("std_vp_sigma") == 0)
                .then(True)
                .otherwise(
                    (pl.col("final_vp") - pl.col("mean_vp_mu")).abs()
                    <= pl.col("std_vp_sigma")
                )
                .alias("is_consistent"),
            )
            .group_by("racer_name")
            .agg(
                pl.col("is_consistent").mean().alias("consistency_score"),
                pl.col("std_vp_sigma").first().alias("std_dev_val"),
            )
        )

        # 5. Base stats aggregation
        base_stats = (
            stats_results.join(
                stats_races.select(
                    [
                        "config_hash",
                        "race_tightness_score",
                        "race_volatility_score",
                        "race_avg_triggers",
                        "race_avg_trip_rate",
                        pl.col("total_turns").alias("race_global_turns"),
                    ]
                ),
                on="config_hash",
                how="left",
            )
            .group_by("racer_name")
            .agg(
                pl.col("final_vp").mean().alias("mean_vp"),
                (pl.col("rank") == 1).sum().alias("cnt_1st"),
                (pl.col("rank") == 2).sum().alias("cnt_2nd"),
                pl.len().alias("races_run"),
                # Dynamics
                pl.col("race_tightness_score").mean().alias("avg_race_tightness"),
                pl.col("race_volatility_score").mean().alias("avg_race_volatility"),
                pl.col("race_avg_triggers").mean().alias("avg_env_triggers"),
                pl.col("race_avg_trip_rate").mean().alias("avg_env_trip_rate"),
                pl.col("race_global_turns").mean().alias("avg_game_duration"),
                # Movement / Dice
                pl.col("non_dice_movement").mean().alias("avg_ability_move"),
                pl.col("speed_gross").mean().alias("avg_speed_gross"),
                pl.col("dice_per_rolling_turn").mean().alias("avg_dice_base"),
                pl.col("final_roll_per_rolling_turn").mean().alias("avg_final_roll"),
                # Ability usage
                pl.col("triggers_per_turn").mean(),
                pl.col("self_per_turn").mean(),
                pl.col("target_per_turn").mean(),
            )
        )

        # 6. Per-racer correlations
        corr_df = (
            stats_results.group_by("racer_name")
            .agg(
                pl.corr("dice_per_rolling_turn", "final_vp").alias("dice_dependency"),
                pl.corr("non_dice_movement", "final_vp").alias(
                    "ability_move_dependency"
                ),
                (pl.corr("racer_id", "final_vp") * -1).alias("start_pos_bias"),
                pl.corr("pos_diff_from_median", "final_vp").alias("midgame_bias"),
                pl.corr("ability_trigger_count", "final_vp").alias(
                    "trigger_dependency"
                ),
            )
            .fill_nan(0)
        )

        final_stats = (
            base_stats.join(corr_df, on="racer_name", how="left")
            .join(consistency_calc, on="racer_name", how="left")
            .join(
                global_win_rates.select(["racer_name", "global_win_rate"]),
                on="racer_name",
                how="left",
            )
            .with_columns(
                (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
                (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd"),
                pl.col("consistency_score").fill_null(0),
                pl.col("global_win_rate").fill_null(0),
                (pl.col("avg_final_roll") - pl.col("avg_dice_base")).alias(
                    "plus_minus_modified"
                ),
                pl.col("std_dev_val").fill_null(0).alias("std_vp_sigma"),
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
                (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg")).alias(
                    "residual_matchup"
                ),
                (
                    (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg"))
                    / pl.col("my_global_avg")
                ).alias("percentage_shift"),
            )
        )

        return {
            "stats": final_stats,
            "matchup_df": matchup_df,
            "results_raw": stats_results,
            "races_raw": stats_races,
        }

    with mo.status.spinner(
        title=f"Aggregating data for {df_races_f.height} races..."
    ) as _spinner:
        dashboard_data = _calculate_all_data()

    # Success message
    mo.output.replace(
        mo.md(
            f"✅ **{df_races_f.height}** races analyzed with **{len(selected_racers)}** racers in races with **{', '.join([str(c) for c in selected_counts])}** racers on **{' and '.join(selected_boards)}**.",
        )
    )
    return (dashboard_data,)


@app.cell
def _(
    BG_COLOR,
    alt,
    dashboard_data,
    df_races_f,
    get_racer_color,
    matchup_metric_toggle,
    mo,
    pl,
):
    # If no data is available (button not clicked yet), stop execution here.
    if dashboard_data is None:
        mo.stop(True)

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
                scale=alt.Scale(
                    range=[
                        "#F06292",  # Pink
                        "#F06292",  # Pink (Anchor)
                        "#3E3B45",  # Deep Lavender Grey (The Bridge)
                        "#3E3B45",  # Deep Lavender Grey (The Bridge)
                        "#42A5F5",
                        "#42A5F5",  # Blue
                        "#42A5F5",
                        "#42A5F5",  # Blue (Anchor)
                    ],
                    interpolate="rgb",
                ),
                legend=alt.Legend(format=legend_format),
            ),
            tooltip=[
                "racer_name",
                "opponent_name",
                alt.Tooltip(
                    "avg_vp_with_opponent:Q", format=".2f", title="Avg VP vs Opp"
                ),
                alt.Tooltip("my_global_avg:Q", format=".2f", title="My Global Avg"),
                alt.Tooltip(
                    "residual_matchup:Q", format="+.2f", title="Residual (Pts)"
                ),
                alt.Tooltip("percentage_shift:Q", format="+.1%", title="Shift (%)"),
            ],
        )
        .properties(
            title=f"Matchup Matrix ({metric_title})",
            width=680,
            height=680,
            background=BG_COLOR,
        )
    )

    # --- 2. QUADRANT CHART BUILDER (UPDATED) ---
    r_list = stats["racer_name"].unique().to_list()
    c_list = [get_racer_color(r) for r in r_list]

    # [HELPER] Calculate contrast color (Black or White) based on luminance
    def _get_contrasting_stroke(hex_color):
        if not hex_color or not hex_color.startswith("#"):
            return "white"
        hex_color = hex_color.lstrip("#")
        try:
            r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            # Standard luminance formula
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            # If bright (>0.6), use black outline. If dark, use white.
            return "black" if luminance > 0.6 else "white"
        except:
            return "white"

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
        PLOT_BG = "#232826"

        vals_x = stats_df[x_col].drop_nulls().to_list()
        vals_y = stats_df[y_col].drop_nulls().to_list()

        if not vals_x or not vals_y:
            return alt.Chart(stats_df).mark_text(text="No Data")

        # --- [NEW] Prepare Outline Colors ---
        # Map racernames to hex, then to their contrasting stroke
        racer_to_hex = dict(zip(racers, colors))
        racer_to_stroke = {
            r: _get_contrasting_stroke(c) for r, c in racer_to_hex.items()
        }

        # Enrich the dataframe with a 'txt_stroke' column for Altair to read
        chart_df = stats_df.with_columns(
            pl.col("racer_name")
            .map_elements(
                lambda n: racer_to_stroke.get(n, "white"), return_dtype=pl.String
            )
            .alias("txt_stroke")
        )

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

        base = alt.Chart(chart_df).encode(
            color=alt.Color(
                "racer_name:N",
                scale=alt.Scale(domain=racers, range=colors),
                legend=None,
            )
        )

        h_line = (
            alt.Chart(pl.DataFrame({"y": [mid_y]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(y="y:Q")
        )
        v_line = (
            alt.Chart(pl.DataFrame({"x": [mid_x]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(x="x:Q")
        )

        tips = [
            "racer_name:N",
            alt.Tooltip(f"{x_col}:Q", format=".2f", title=x_title),
            alt.Tooltip(f"{y_col}:Q", format=".2f", title=y_title),
            alt.Tooltip("mean_vp:Q", format=".2f", title="Avg VP"),
        ]
        if extra_tooltips:
            tips.extend(extra_tooltips)

        points = base.mark_circle(size=250, opacity=0.9).encode(
            x=alt.X(
                f"{x_col}:Q",
                title=x_title,
                scale=alt.Scale(
                    domain=[view_min_x, view_max_x], reverse=reverse_x, zero=False
                ),
                axis=alt.Axis(grid=False),  # <--- Turn off X grid
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=y_title,
                scale=alt.Scale(domain=[view_min_y, view_max_y], zero=False),
                axis=alt.Axis(grid=False),  # <--- Turn off Y grid
            ),
            tooltip=tips,
        )

        # --- [NEW] LAYERED TEXT FOR OUTLINE EFFECT ---

        # Layer 1: The Outline (Thicker Stroke, Contrast Color)
        text_outline = points.mark_text(
            align="center",
            baseline="middle",
            dy=-22,
            dx=-22,
            fontSize=15,  # Slightly smaller than 20 for cleaner look
            fontWeight=800,  # Extra Bold is crucial for colored text
            stroke=PLOT_BG,  # <--- THE FIX: Stroke matches plot background
            strokeWidth=3,  # Wide halo
            opacity=1,
        ).encode(
            text="racer_name:N",
            # No color needed, it's just the mask
        )

        text_fill = points.mark_text(
            align="center",
            baseline="middle",
            dy=-22,
            dx=-22,
            fontSize=15,
            fontWeight=800,
        ).encode(
            text="racer_name:N",
            # Use the racer color directly, but consider a transform to pastel if possible
            color=alt.Color(
                "racer_name:N", scale=alt.Scale(domain=racers, range=colors)
            ),
        )

        chart = h_line + v_line + points + text_outline + text_fill

        if quad_labels and len(quad_labels) == 4:
            if reverse_x:
                left_x, right_x = (
                    view_max_x - (pad_x * 0.5),
                    view_min_x + (pad_x * 0.5),
                )
            else:
                left_x, right_x = (
                    view_min_x + (pad_x * 0.5),
                    view_max_x - (pad_x * 0.5),
                )
            top_y, bot_y = view_max_y - (pad_y * 0.5), view_min_y + (pad_y * 0.5)

            text_props = {
                "fontWeight": "bold",
                "opacity": 0.6,
                "fontSize": 14,  # Increased Label Size
                "color": "#e0e0e0",
            }

            t1 = (
                alt.Chart(
                    pl.DataFrame({"x": [left_x], "y": [top_y], "t": [quad_labels[0]]})
                )
                .mark_text(align="left", baseline="top", **text_props)
                .encode(x="x:Q", y="y:Q", text="t:N")
            )
            t2 = (
                alt.Chart(
                    pl.DataFrame({"x": [right_x], "y": [top_y], "t": [quad_labels[1]]})
                )
                .mark_text(align="right", baseline="top", **text_props)
                .encode(x="x:Q", y="y:Q", text="t:N")
            )
            t3 = (
                alt.Chart(
                    pl.DataFrame({"x": [left_x], "y": [bot_y], "t": [quad_labels[2]]})
                )
                .mark_text(align="left", baseline="bottom", **text_props)
                .encode(x="x:Q", y="y:Q", text="t:N")
            )
            t4 = (
                alt.Chart(
                    pl.DataFrame({"x": [right_x], "y": [bot_y], "t": [quad_labels[3]]})
                )
                .mark_text(align="right", baseline="bottom", **text_props)
                .encode(x="x:Q", y="y:Q", text="t:N")
            )
            chart = chart + t1 + t2 + t3 + t4

        # Increased Chart Size
        return chart.properties(
            title=title,
            width=800,
            height=800,
            background=BG_COLOR,
        )

    # --- 3. GENERATE CHARTS (Unchanged Logic, uses new builder) ---
    c_consist = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "consistency_score",
        "mean_vp",
        "Consistency (Stability)",
        "Stability (% within 1σ of mean VP)",
        "Avg VP",
        False,
        ["Wildcard", "Reliable Winner", "Erratic", "Reliable Loser"],
        extra_tooltips=[
            alt.Tooltip("std_vp_sigma:Q", format=".2f", title="1σ (Std Dev)"),
        ],
    )

    c_excitement = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "avg_race_tightness",
        "avg_race_volatility",
        "Excitement Profile",
        "Tightness (Avg distance from mean position)",
        "Volatility (% of turns with rank changes)",
        True,
        ["Rubber Band", "Thriller", "Procession", "Stalemate"],
    )

    c_sources = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "ability_move_dependency",
        "dice_dependency",
        "Sources of Victory",
        "Ability Move Dep (Corr to VP)",
        "Dice Dep (Corr to VP)",
        False,
        ["Dice-Driven", "Hybrid Winner", "Low Signal", "Ability-Driven"],
        extra_tooltips=[
            alt.Tooltip("avg_ability_move:Q", format=".2f", title="Ability Mvmt/Turn"),
            alt.Tooltip("avg_dice_base:Q", format=".2f", title="Dice/Rolling Turn"),
        ],
    )

    c_momentum = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "start_pos_bias",
        "midgame_bias",
        "Momentum Profile",
        "Start Pos Bias (+ = comeback)",
        "Mid-Game Bias (+ = leader wins)",
        False,
        ["Frontrunner", "Snowballer", "Comeback King", "Late Bloomer"],
        extra_tooltips=[
            alt.Tooltip("pct_1st:Q", format=".1%", title="Win%"),
            alt.Tooltip("mean_vp:Q", format=".2f", title="Avg VP"),
        ],
    )

    c_engine = _build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "triggers_per_turn",
        "trigger_dependency",
        "Engine Profile",
        "Activity (Avg Triggers / Turn)",
        "Efficacy (Corr Triggers to VP)",
        False,
        [
            "Potent",
            "Ability Abuser",
            "Low Reliance",
            "Spammer",
        ],
    )

    # ... (Rest of global charts and UI layout logic remains exactly the same) ...
    # To save space, I am keeping the logic below identical to your previous cell.

    # --- 4. GLOBAL DYNAMICS ---
    race_meta = df_races_f.select(["config_hash", "board", "racer_count"])
    races_with_meta = proc_races.join(race_meta, on="config_hash", how="left")
    results_with_meta = proc_results.join(race_meta, on="config_hash", how="left")

    race_level_agg = races_with_meta.group_by(["board", "racer_count"]).agg(
        pl.col("total_turns").mean().alias("Avg Turns"),
        pl.col("race_tightness_score").mean().alias("Tightness"),
        pl.col("race_volatility_score").mean().alias("Volatility"),
        pl.col("race_avg_trip_rate").mean().alias("Trip Rate"),
        pl.col("race_avg_triggers").mean().alias("Abilities Triggered"),
    )

    result_level_agg = (
        results_with_meta.group_by(["board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("Avg VP"),
            pl.corr("sum_dice_rolled", "final_vp").alias("Dice Dep"),
            pl.corr("non_dice_movement", "final_vp").alias("Ability Dep"),
            (pl.corr("racer_id", "final_vp") * -1).alias("Start Bias"),
            pl.corr("pos_diff_from_median", "final_vp").alias("MidGame Bias"),
        )
        .fill_nan(0)
    )

    global_wide = race_level_agg.join(
        result_level_agg, on=["board", "racer_count"], how="inner"
    ).fill_nan(0)

    global_grp1 = global_wide.select(
        [
            "board",
            "racer_count",
            "Avg VP",
            "Avg Turns",
            "Tightness",
            "Volatility",
            "Trip Rate",
        ]
    ).unpivot(index=["board", "racer_count"], variable_name="metric", value_name="val")

    global_grp2 = global_wide.select(
        [
            "board",
            "racer_count",
            "Dice Dep",
            "Ability Dep",
            "Start Bias",
            "MidGame Bias",
            "Abilities Triggered",
        ]
    ).unpivot(index=["board", "racer_count"], variable_name="metric", value_name="val")

    c_global_1 = (
        alt.Chart(global_grp1)
        .mark_bar()
        .encode(
            x=alt.X("board:N", title="Board", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("racer_count:N"),
            y=alt.Y("val:Q", title=None),
            color=alt.Color("racer_count:N", title="Players"),
            column=alt.Column("metric:N", title=None),
            tooltip=[
                "board:N",
                "racer_count:N",
                "metric:N",
                alt.Tooltip("val:Q", format=".3f"),
            ],
        )
        .resolve_scale(y="independent")
        .properties(width=120, height=200, title="Race Metrics by Board & Player Count")
    )

    c_global_2 = (
        alt.Chart(global_grp2)
        .mark_bar()
        .encode(
            x=alt.X("board:N", title="Board", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("racer_count:N"),
            y=alt.Y("val:Q", title=None),
            color=alt.Color("racer_count:N", title="Players"),
            column=alt.Column("metric:N", title=None),
            tooltip=[
                "board:N",
                "racer_count:N",
                "metric:N",
                alt.Tooltip("val:Q", format=".3f"),
            ],
        )
        .resolve_scale(y="independent")
        .properties(
            width=120, height=200, title="Victory Correlations & Ability Usage by Board"
        )
    )

    global_ui = mo.vstack(
        [mo.ui.altair_chart(c_global_1), mo.ui.altair_chart(c_global_2)]
    )

    # --- 5. ENVIRONMENT MATRIX ---
    env_metric_col = "relative_shift" if use_pct else "absolute_shift"
    env_metric_title = "Shift vs Own Avg (%)" if use_pct else "Shift vs Own Avg (VP)"
    env_legend_fmt = ".0%" if use_pct else "+.2f"

    joined = proc_results.join(race_meta, on="config_hash", how="inner")
    racer_baselines = joined.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp")
    )

    env_stats = (
        joined.group_by(["racer_name", "board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("cond_avg_vp"),
            pl.col("final_vp").count().alias("sample_size"),
        )
        .join(racer_baselines, on="racer_name", how="left")
        .with_columns(
            (
                (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp"))
                / pl.col("racer_global_avg_vp")
            ).alias("relative_shift"),
            (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp")).alias(
                "absolute_shift"
            ),
            (
                pl.col("racer_count").cast(pl.String)
                + "p\n"
                + pl.col("board").cast(pl.String)
            ).alias("env_label"),
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
            x=alt.X(
                "env_label:N",
                title="Environment",
                sort=sort_order,
                axis=alt.Axis(labelAngle=0, labelLimit=180),
            ),
            y=alt.Y("racer_name:N", title="Racer"),
            color=alt.Color(
                f"{env_metric_col}:Q",
                title=env_metric_title,
                scale=alt.Scale(
                    range=[
                        "#F06292",  # Pink
                        "#F06292",  # Pink (Anchor)
                        "#3E3B45",  # Deep Lavender Grey (The Bridge)
                        "#3E3B45",  # Deep Lavender Grey (The Bridge)
                        "#42A5F5",
                        "#42A5F5",
                        "#42A5F5",  # Blue (Anchor)
                    ],
                    interpolate="rgb",
                ),
                legend=alt.Legend(format=env_legend_fmt),
            ),
            tooltip=[
                "racer_name:N",
                "board:N",
                "racer_count:N",
                alt.Tooltip("cond_avg_vp:Q", format=".2f"),
                alt.Tooltip("racer_global_avg_vp:Q", format=".2f"),
                alt.Tooltip("absolute_shift:Q", format="+.2f"),
                alt.Tooltip("relative_shift:Q", format="+.1%"),
                alt.Tooltip("sample_size:Q", format=".0f"),
            ],
        )
        .properties(
            title=f"Env Adaptability ({env_metric_title})",
            width=680,
            height=680,
            background=BG_COLOR,
        )
    )

    # --- 6. TABLES ---
    master_df = stats.sort("mean_vp", descending=True)
    df_overview = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("mean_vp").round(2).alias("Avg VP"),
        (pl.col("consistency_score") * 100).round(1).alias("Consist%"),
        (pl.col("pct_1st") * 100).round(1).alias("1st%"),
        (pl.col("pct_2nd") * 100).round(1).alias("2nd%"),
        pl.col("races_run").alias("# Races"),
    )
    df_movement = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("avg_speed_gross").round(2).alias("Speed"),
        pl.col("avg_dice_base").round(2).alias("Base Roll"),
        pl.col("dice_dependency").round(2).alias("Dice Dep"),
        pl.col("plus_minus_modified").round(2).alias("+-Modified"),
        pl.col("avg_ability_move").round(2).alias("Ability Mvmt/Turn"),
        pl.col("ability_move_dependency").round(2).alias("Ability Move Dep"),
    )
    df_abilities = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("avg_ability_move").round(2).alias("Ability Mvmt/Turn"),
        pl.col("triggers_per_turn").round(2).alias("Trig/Turn"),
        pl.col("self_per_turn").round(2).alias("Self/Turn"),
        pl.col("target_per_turn").round(2).alias("Tgt/Turn"),
    )
    df_dynamics = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("avg_race_volatility").round(2).alias("Volatility"),
        pl.col("avg_race_tightness").round(2).alias("Tightness"),
        pl.col("avg_game_duration").round(1).alias("Avg Game Len"),
        pl.col("avg_env_triggers").round(1).alias("Race Trigs"),
        (pl.col("avg_env_trip_rate") * 100).round(1).alias("Race Trip%"),
    )
    df_vp = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("mean_vp").round(2).alias("Avg VP"),
        pl.col("dice_dependency").round(2).alias("Dice Dep"),
        pl.col("ability_move_dependency").round(2).alias("Ability Move Dep"),
        pl.col("start_pos_bias").round(2).alias("Start Bias"),
        pl.col("midgame_bias").round(2).alias("MidGame Bias"),
    )

    # --- 7. UI COMPOSITION ---
    left_charts_ui = mo.ui.tabs(
        {
            "🎯 Consistency": mo.vstack(
                [
                    mo.ui.altair_chart(c_consist),
                    mo.md(
                        """**Stability**: Percentage of races where Final VP is within ±1 standard deviation (1σ) of the racer's mean VP."""
                    ),
                ]
            ),
            "🎲 Dice vs Ability": mo.vstack(
                [
                    mo.ui.altair_chart(c_sources),
                    mo.md(
                        """**X: Ability Move Dependency** – Correlation of non-dice movement (ability-driven positioning) to VP.\n**Y: Dice Dependency** – Correlation of total dice rolled to VP."""
                    ),
                ]
            ),
            "🌊 Momentum": mo.vstack(
                [
                    mo.ui.altair_chart(c_momentum),
                    mo.md(
                        """**X: Start Pos Bias** – Correlation of starting position (racer ID) to VP.\n**Y: Mid-Game Bias** – Correlation of position at 66% mark to VP."""
                    ),
                ]
            ),
            "🔥 Excitement": mo.vstack(
                [
                    mo.ui.altair_chart(c_excitement),
                    mo.md(
                        """**Tightness** (X-axis, reversed): Average distance from mean position across all turns.\n**Volatility** (Y-axis): Percentage of turns where at least one racer changes rank."""
                    ),
                ]
            ),
            "⚡ Abilities": mo.vstack(
                [
                    mo.ui.altair_chart(c_engine),
                    mo.md(
                        """**X: Activity** – Average number of ability triggers per turn.\n**Y: Efficacy** – Correlation between trigger count and Victory Points.\n*Do more ability triggers mean more points?*"""
                    ),
                ]
            ),
            "🌍 Global": global_ui,
        }
    )

    right_ui = mo.ui.tabs(
        {
            "🏆 Overview": mo.vstack(
                [
                    mo.ui.table(df_overview, selection=None, page_size=50),
                    mo.md(
                        """**Avg VP**: Mean victory points across all races.\n**Consist%**: Reliability.\n**1st%** / **2nd%**: Win rate and runner-up rate."""
                    ),
                ]
            ),
            "⚔️ Interactions": mo.vstack(
                [matchup_metric_toggle, mo.ui.altair_chart(c_matrix)]
            ),
            "🌍 Environments": mo.vstack(
                [matchup_metric_toggle, mo.ui.altair_chart(c_env)]
            ),
            "🏃 Movement": mo.vstack(
                [
                    mo.ui.table(df_movement, selection=None, page_size=50),
                    mo.md("""**Speed**: Average gross distance moved per turn."""),
                ]
            ),
            "💎 VP Analysis": mo.vstack(
                [
                    mo.ui.table(df_vp, selection=None, page_size=50),
                    mo.md(
                        """**Start Bias**: Positive = comeback. Negative = frontrunner."""
                    ),
                ]
            ),
            "⚡ Abilities": mo.vstack(
                [
                    mo.ui.table(df_abilities, selection=None, page_size=50),
                    mo.md("""**Trig/Turn**: Average ability triggers per turn."""),
                ]
            ),
            "🔥 Dynamics": mo.vstack(
                [
                    mo.ui.table(df_dynamics, selection=None, page_size=50),
                    mo.md("""**Volatility**: Rank changes per turn."""),
                ]
            ),
        }
    )

    final_output = mo.md(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 2rem; width: 100%; min-height: 550px;">
        <div style="flex: 1 1 450px; min-width: 0; display: flex; justify-content: center; align-items: start;">
            <div style="width: 100%; display:flex; flex-direction:column; gap: 1rem;">
                {left_charts_ui}
            </div>
        </div>
        <div style="flex: 1 1 400px; min-width: 0; overflow-x: auto;">{right_ui}</div>
    </div>
    """)
    final_output
    return


if __name__ == "__main__":
    app.run()
