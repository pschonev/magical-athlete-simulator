import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import math

    # --- 1. Configuration ---
    # 30 Spaces: Green Start, Red Finish, White/Grey alternating track
    space_colors = ["#4CAF50"] + ["#F5F5F5", "#E0E0E0"] * 14 + ["#F44336"]
    space_colors = space_colors[:30]

    players = [
        {"id": "P1", "color": "#00BCD4"},  # Cyan
        {"id": "P2", "color": "#FF9800"},  # Orange
        {"id": "P3", "color": "#9C27B0"},  # Purple
        {"id": "P4", "color": "#3F51B5"},  # Indigo
        {"id": "P5", "color": "#FFEB3B"},  # Yellow
    ]


    # --- 2. Track Geometry Generator ---
    def generate_racetrack_positions(
        num_spaces, start_x, start_y, straight_len, radius
    ):
        positions = []

        # Calculate total perimeter to distribute spaces evenly
        # Perimeter = 2 * Straight + 2 * Pi * Radius
        perimeter = (2 * straight_len) + (2 * math.pi * radius)
        step_distance = perimeter / num_spaces

        # Centers for the turn circles
        right_circle_cx = start_x + straight_len
        right_circle_cy = start_y - radius
        left_circle_cx = start_x
        left_circle_cy = start_y - radius

        for i in range(num_spaces):
            dist = i * step_distance

            # Determine which segment of the track we are on
            # 1. Bottom Straight (Moving Right)
            if dist < straight_len:
                x = start_x + dist
                y = start_y
                angle = 0  # Pointing Right

            # 2. Right Turn (Moving Up and Left)
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                # Angle goes from 90 (bottom) to -90 (top) via 0 (right)
                # Fraction of semicircle covered
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (math.pi / 2) - (fraction * math.pi)

                x = right_circle_cx + radius * math.cos(theta_rad)
                y = right_circle_cy + radius * math.sin(theta_rad)
                # Rotation of the rectangle should be tangent to the curve
                # Tangent is perpendicular to radius.
                # Calculated visually: Heading = theta - 90 degrees
                angle = math.degrees(theta_rad) + 90

            # 3. Top Straight (Moving Left)
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x = (start_x + straight_len) - top_dist
                y = start_y - (2 * radius)
                angle = 180  # Pointing Left

            # 4. Left Turn (Moving Down and Right)
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                # Angle goes from 270/-90 (top) to 90 (bottom) via 180 (left)
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (-math.pi / 2) - (fraction * math.pi)

                x = left_circle_cx + radius * math.cos(theta_rad)
                y = left_circle_cy + radius * math.sin(theta_rad)
                angle = math.degrees(theta_rad) + 90

            positions.append((x, y, angle))

        return positions


    # Generate the board data (Start at 100, 300)
    # Adjust straight_len and radius to change aspect ratio
    board_positions = generate_racetrack_positions(
        num_spaces=30, start_x=120, start_y=350, straight_len=350, radius=100
    )

    # --- 3. Interactive Elements ---
    turn_slider = mo.ui.slider(start=0, stop=29, step=1, label="Turn Number")


    # --- 4. Render Function (Updated for Racetrack) ---
    def render_racetrack(turn):
        svg_elements = []

        # A. Draw Track Spaces
        # Rect dimensions (Longer than tall)
        rw, rh = 50, 30

        for i, (cx, cy, rot) in enumerate(board_positions):
            transform = f"rotate({rot}, {cx}, {cy})"

            # Space Rectangle
            svg_elements.append(
                f'<rect x="{cx - rw / 2:.1f}" y="{cy - rh / 2:.1f}" width="{rw}" height="{rh}" '
                f'fill="{space_colors[i]}" stroke="#555" stroke-width="1" transform="{transform}" rx="4" />'  # rx for rounded corners
            )
            # Space Number
            svg_elements.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" font-family="sans-serif" font-size="10" font-weight="bold" '
                f'text-anchor="middle" fill="#333" transform="{transform}" style="pointer-events: none;">{i}</text>'
            )

        # B. Draw Players (Same Grouping Logic)
        # Demo positions: P1 leads, others trail
        positions_indices = [
            turn,
            max(0, turn - 1),
            max(0, turn - 3),
            turn,
            max(0, turn - 1),
        ]

        occupancy = {}
        for pid, pos in enumerate(positions_indices):
            if pos not in occupancy:
                occupancy[pos] = []
            occupancy[pos].append(players[pid])

        # C. Render Player Tokens
        for space_idx, occupants in occupancy.items():
            if space_idx >= 30:
                continue

            bx, by, brot = board_positions[space_idx]
            count = len(occupants)

            # Dynamic Offsets for up to 5 players
            # Coordinates relative to the center of the rectangle
            offsets = []
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

            for i, player in enumerate(occupants):
                if i >= len(offsets):
                    break
                ox, oy = offsets[i]

                # Rotate the offset to match the board space rotation
                rad = math.radians(brot)
                rot_ox = ox * math.cos(rad) - oy * math.sin(rad)
                rot_oy = ox * math.sin(rad) + oy * math.cos(rad)

                svg_elements.append(
                    f'<circle cx="{bx + rot_ox:.1f}" cy="{by + rot_oy:.1f}" r="7" '
                    f'fill="{player["color"]}" stroke="white" stroke-width="1.5" />'
                )

        return f"""
        <svg width="600" height="500" style="background: #eef; border: 2px solid #ccc; border-radius: 8px;">
            <!-- Decorative Grass Center -->
            <ellipse cx="295" cy="250" rx="150" ry="70" fill="#C8E6C9" stroke="none" />
            {"".join(svg_elements)}
        </svg>
        """
    return mo, render_racetrack, turn_slider


@app.cell
def _(mo, render_racetrack, turn_slider):
    # --- 5. Display ---
    mo.vstack([turn_slider, mo.Html(render_racetrack(turn_slider.value))])
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
