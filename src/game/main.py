from __future__ import annotations

import os
import sys
import math
from typing import Final
import json
from enum import Enum, auto

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_MODELVIEW,
    GL_PROJECTION,
    GL_QUADS,
    GL_TRIANGLE_FAN,
    GL_TRIANGLE_STRIP,
    GL_TRIANGLES,
    glBegin,
    glClear,
    glClearColor,
    glEnd,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glVertex2f,
    glViewport,
    glColor3f,
    glRectf,
)

from OpenGL.GLUT import (
    GLUT_DEPTH,
    GLUT_DOUBLE,
    GLUT_RGB,
    glutCreateWindow,
    glutDisplayFunc,
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutKeyboardFunc,
    glutMainLoop,
    glutPostRedisplay,
    glutReshapeFunc,
    glutSwapBuffers,
    glutReshapeWindow,
    glutSetWindowTitle,
    glutTimerFunc,
)


# Initial window size (pixels) before we resize to fit the grid on first draw.
WINDOW_W: Final[int] = 900
WINDOW_H: Final[int] = 700

# Pixels per map cell; window size becomes num_cols * cell_size by num_rows * cell_size.
cell_size = 50
current_phase = 1
is_new_phase = True

class Grid:
    """
    Holds a 2D cell array. Constructor builds a placeholder grid; load_map replaces
    self.grid with the JSON matrix.
    """

    def __init__(self, width: int, height: int):
        # load_map passes (len(matrix), len(matrix[0])) so self.width is JSON row count
        # and self.height is JSON column count; names are historical, not geometric "width".
        self.width = width
        self.height = height
        # Placeholder 2D list; load_map replaces self.grid with the JSON matrix immediately.
        self.grid = [[0 for _ in range(width)] for _ in range(height)]

class Position:
    """Class to represent the position of the player and boxes in the grid."""
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

class Player:
    def __init__(self, position: Position):
        self.position = position
        # Flag to prevent multiple rotations from a single step
        self.just_rotated = False
        self.size = 1
        print("Player initialized at position:", self.position.x, self.position.y)

    def get_position(self) -> Position:
        """Returns the current position of the player."""
        return self.position
    
    def move(self, dx: int, dy: int) -> None:
        """Moves the player by (dx, dy) if the destination cell is walkable."""
        self.position.x += dx
        self.position.y += dy

    def get_cells(self) -> list[tuple[int, int]]:
        """Return a list of (row, col) cells currently occupied by the player."""
        cells = []
        top_left_row = self.position.x
        top_left_col = self.position.y
        for row_offset in range(self.size):
            for col_offset in range(self.size):
                cell_row = top_left_row + row_offset
                cell_col = top_left_col + col_offset
                cells.append((cell_row, cell_col))
        return cells
    
class Box:
    def __init__(self, position: Position):
        self.position = position
        print("Box initialized at position:", self.position.x, self.position.y)

    def get_position(self) -> Position:
        return self.position

def load_map_data(phase_number: int) -> tuple[Grid, list[int], list[list[int]], int, int]:
    """
    Read src/game/phases/{phase}/map.json and return the grid plus spawn metadata.

    Expected JSON keys: map (2D int array), agent_start_position, boxes_start_positions.
    Optional keys: movements_limit (default 10), agent_start_size (default 1).
    Cell values: 0 empty, 1 obstacle, 2 goal, 3 scale_toggle, 4 rotate_pad.
    """
    with open(f"src/game/phases/{phase_number:03d}/map.json", "r") as file:
        map_data = json.load(file)
    matrix = map_data["map"]
    agent_start_position = map_data["agent_start_position"]
    boxes_start_positions = map_data["boxes_start_positions"]
    movements_limit = map_data.get("movements_limit", 10)
    agent_start_size = map_data.get("agent_start_size", 1)
    # Grid(len(matrix), len(matrix[0])) => width = row count, height = col count.
    grid_object = Grid(len(matrix), len(matrix[0]))
    grid_object.grid = matrix
    return grid_object, agent_start_position, boxes_start_positions, movements_limit, agent_start_size


def build_phase(phase_number: int) -> tuple[Grid, Player, list[Box], int]:
    """
    Returns:
      grid:   The Grid object.
      player: A Player instance placed at the start position.
      boxes:  A list of Box instances placed at their start positions.
      movements_limit: The maximum number of movements allowed.
    """
    grid_object, agent_start_position, boxes_start_positions, limit, agent_start_size = load_map_data(phase_number)

    player = Player(Position(agent_start_position[0], agent_start_position[1]))
    player.size = agent_start_size
    
    boxes = []
    for box_pos in boxes_start_positions:
        box = Box(Position(box_pos[0], box_pos[1]))
        boxes.append(box)

    return grid_object, player, boxes, limit
    
def update_window_title():
    """Update the window title according to the current game state and moves."""
    state = phase["state"]
    if state == "playing":
        msg = f"{phase['movements_left']} Movimentos faltando!"
        glutSetWindowTitle(msg.encode())
    elif state == "won":
        if os.path.isfile(_next_phase_path(current_phase + 1)):
            glutSetWindowTitle(b"Fase concluida! Proxima fase em 2s... (N para avancar ja)")
        else:
            glutSetWindowTitle(b"Voce ganhou! Parabens!")
    elif state == "lost":
        glutSetWindowTitle(b"Aperte R para reiniciar a fase!")



grid_object, player, boxes, movements_limit = build_phase(current_phase)
# Mutable dict so later code can swap phases without replacing the global name.
phase = {}
phase["grid"] = grid_object
phase["player"] = player
phase["boxes"] = boxes
phase["movements_left"] = movements_limit
phase["movements_limit"] = movements_limit
phase["state"] = "playing"  # or "won", "lost"


def reshape_window(width: int, height: int) -> None:
    """
    GLUT calls this when the window is created or resized.

    Without glOrtho + glViewport, glRectf uses clip space [-1, 1] and map-sized
    coordinates would be clipped; this maps window pixels 1:1 to world units.
    """
    if width <= 0 or height <= 0:
        return
    # Drawable area in framebuffer pixels: lower-left (0,0), full window.
    glViewport(0, 0, width, height)
    # Projection stack: ortho with origin top-left, Y increasing downward (matches row index).
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, float(width), float(height), 0.0, -1.0, 1.0)
    # Modelview stays identity for 2D grid drawing in pixel coordinates.
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

class Cell(Enum):
    """Enum for the different types of cells in the grid."""
    EMPTY = auto();
    WALL = auto();
    GOAL = auto();
    BOX = auto();
    BOX_ON_GOAL = auto();
    OUT_OF_BOUNDS = auto();
    PLAYER = auto();
    SCALE_TOGGLE = auto();
    ROTATE_PAD = auto();
    BOX_ON_SCALE_TOGGLE = auto();
    BOX_ON_ROTATE_PAD = auto();

class Color(Enum):
    """Enum for the different colors used in the grid."""
    EMPTY    = (0.0, 0.0, 0.0)
    WALL     = (0.5, 0.5, 0.5)
    GOAL     = (1.0, 0.0, 0.0)
    BOX      = (0.8, 0.5, 0.0)
    BOX_ON_GOAL = (0.4, 0.25, 0.0)
    PLAYER   = (0.2, 0.9, 0.2)
    SCALE_TOGGLE = (0.0, 0.0, 1.0)
    ROTATE_PAD = (0.0, 1.0, 1.0)
    BOX_ON_SCALE_TOGGLE = (0.4, 0.2, 0.8)
    BOX_ON_ROTATE_PAD = (0.0, 0.7, 0.6)

# Maps Cell types to their corresponding colors for drawing.
CELL_COLOR = {
    Cell.EMPTY:        Color.EMPTY,
    Cell.WALL:         Color.WALL,
    Cell.GOAL:         Color.GOAL,
    Cell.BOX:          Color.BOX,
    Cell.BOX_ON_GOAL:  Color.BOX_ON_GOAL,
    Cell.PLAYER:       Color.PLAYER,
    Cell.SCALE_TOGGLE: Color.SCALE_TOGGLE,
    Cell.ROTATE_PAD:   Color.ROTATE_PAD,
    Cell.BOX_ON_SCALE_TOGGLE: Color.BOX_ON_SCALE_TOGGLE,
    Cell.BOX_ON_ROTATE_PAD: Color.BOX_ON_ROTATE_PAD,
}

def get_grid_type(code: int) -> Cell:
    """Helper function to convert the integer code from the grid to a Cell enum."""   
    if code == 1: return Cell.WALL
    if code == 2: return Cell.GOAL
    if code == 3: return Cell.SCALE_TOGGLE
    if code == 4: return Cell.ROTATE_PAD
    return Cell.EMPTY

def is_walkable(cell_type: Cell) -> bool:
    """Helper function to determine if the player or boxes can move on a cell of the given type."""
    return cell_type in (Cell.EMPTY, Cell.GOAL, Cell.SCALE_TOGGLE, Cell.ROTATE_PAD)

def draw_cell(row: int, col: int, cell_type: Cell) -> None:
    """Helper function to draw a single cell at the given row and column with the appropriate color."""
    glColor3f(*CELL_COLOR[cell_type].value)
    
    glRectf(
        col * cell_size,
        row * cell_size,
        (col + 1) * cell_size,
        (row + 1) * cell_size,
    )

def draw_player(row, col, scale):
    """Helper function to draw the player as a green rectangle with two black square eyes (a slime)"""
    
    # Top left corner of the cell
    x = col * cell_size
    y = row * cell_size

    # Height/Width of the player rectangle
    size = scale * cell_size

    # Draw the player body as a green rectangle
    glColor3f(0.2, 0.9, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + size, y)
    glVertex2f(x + size, y + size)
    glVertex2f(x, y + size)
    glEnd()

    # Size of the eyes as a fraction of the player size
    eye_size = 0.1 * size

    # Left eye
    glColor3f(0, 0, 0)
    glBegin(GL_QUADS)
    glVertex2f(x + 0.2*size - eye_size/2, y + 0.6*size - eye_size/2)
    glVertex2f(x + 0.2*size + eye_size/2, y + 0.6*size - eye_size/2)
    glVertex2f(x + 0.2*size + eye_size/2, y + 0.6*size + eye_size/2)
    glVertex2f(x + 0.2*size - eye_size/2, y + 0.6*size + eye_size/2)
    glEnd()
    # Right eye
    glBegin(GL_QUADS)
    glVertex2f(x + 0.8*size - eye_size/2, y + 0.6*size - eye_size/2)
    glVertex2f(x + 0.8*size + eye_size/2, y + 0.6*size - eye_size/2)
    glVertex2f(x + 0.8*size + eye_size/2, y + 0.6*size + eye_size/2)
    glVertex2f(x + 0.8*size - eye_size/2, y + 0.6*size + eye_size/2)
    glEnd()

def draw_box(row, col):
    """Helper function to draw a box as a brown crate."""
    # Top-left corner of the cell
    x = col * cell_size
    y = row * cell_size

    # margin to make the box smaller (in pixels)
    margin = 0.02 * cell_size  

    # Calculate the bounds of the inner box
    left = x + margin
    right = x + cell_size - margin
    top = y + margin
    bottom = y + cell_size - margin

    # Main box body (fills the inner area)
    glColor3f(0.8, 0.5, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(left, top)
    glVertex2f(right, top)
    glVertex2f(right, bottom)
    glVertex2f(left, bottom)
    glEnd()

    # Box border
    glColor3f(0.6, 0.35, 0.0)
    border = 0.1 * (cell_size - 2*margin)  
    # Top border
    glBegin(GL_QUADS)
    glVertex2f(left, top)
    glVertex2f(right, top)
    glVertex2f(right, top + border)
    glVertex2f(left, top + border)
    glEnd()
    # Bottom border
    glBegin(GL_QUADS)
    glVertex2f(left, bottom - border)
    glVertex2f(right, bottom - border)
    glVertex2f(right, bottom)
    glVertex2f(left, bottom)
    glEnd()
    # Left border
    glBegin(GL_QUADS)
    glVertex2f(left, top)
    glVertex2f(left + border, top)
    glVertex2f(left + border, bottom)
    glVertex2f(left, bottom)
    glEnd()
    # Right border
    glBegin(GL_QUADS)
    glVertex2f(right - border, top)
    glVertex2f(right, top)
    glVertex2f(right, bottom)
    glVertex2f(right - border, bottom)
    glEnd()

    # Vertical stripes
    stripe = 0.1 * (cell_size - 2*margin)   
    offsets = [0.25, 0.5, 0.75]            
    for off in offsets:
        # x for the centre of the stripe
        stripe_x = left + off * (right - left)
        # Left and right edges of the stripe
        stripe_left = stripe_x - stripe / 2
        stripe_right = stripe_x + stripe / 2

        glBegin(GL_QUADS)
        glVertex2f(stripe_left, top + border)
        glVertex2f(stripe_right, top + border)
        glVertex2f(stripe_right, bottom - border)
        glVertex2f(stripe_left, bottom - border)
        glEnd()

def draw_goal(row: int, col: int) -> None:
    """Draw a goal cell as a red square with a darker red border."""
    pad = cell_size * 0.1
    x = col * cell_size + pad
    y = row * cell_size + pad
    size = cell_size - 2 * pad

    # Bright red fill
    glColor3f(1.0, 0.12, 0.12)
    glRectf(x, y, x + size, y + size)

def draw_rotate_pad(row: int, col: int) -> None:
    """Draw a rotate pad as a 270-degree arc with a clockwise arrowhead at its tip."""
    cx = col * cell_size + cell_size / 2.0
    cy = row * cell_size + cell_size / 2.0
    r_outer = cell_size * 0.38
    r_inner = cell_size * 0.22
    segments = 40

    angle_start = math.radians(120)
    angle_end = math.radians(390)  # 120 + 270

    glColor3f(0.0, 0.85, 0.95)
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(segments + 1):
        t = i / segments
        angle = angle_start + t * (angle_end - angle_start)
        glVertex2f(cx + r_outer * math.cos(angle), cy + r_outer * math.sin(angle))
        glVertex2f(cx + r_inner * math.cos(angle), cy + r_inner * math.sin(angle))
    glEnd()

    # Arrowhead at angle_end 
    r_mid = (r_outer + r_inner) / 2.0
    base_x = cx + r_mid * math.cos(angle_end)
    base_y = cy + r_mid * math.sin(angle_end)

    # Tangent direction for increasing angle (clockwise on screen with Y-down)
    tx = -math.sin(angle_end)
    ty = math.cos(angle_end)

    # Radial outward normal for the arrowhead width
    nx = math.cos(angle_end)
    ny = math.sin(angle_end)

    tip_len = cell_size * 0.17
    half_w = (r_outer - r_inner) * 0.95

    tip_x = base_x + tx * tip_len
    tip_y = base_y + ty * tip_len
    b1_x = base_x + nx * half_w
    b1_y = base_y + ny * half_w
    b2_x = base_x - nx * half_w
    b2_y = base_y - ny * half_w

    glBegin(GL_TRIANGLES)
    glVertex2f(tip_x, tip_y)
    glVertex2f(b1_x, b1_y)
    glVertex2f(b2_x, b2_y)
    glEnd()

def draw_scale_pad(row: int, col: int) -> None:
    """Draw a scale toggle pad as two nested blue squares (outer dark, inner light)."""
    # Top-left corner of the cell in pixels
    x = col * cell_size
    y = row * cell_size

    # Outer square
    glColor3f(0.0, 0.0, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + cell_size, y)
    glVertex2f(x + cell_size, y + cell_size)
    glVertex2f(x, y + cell_size)
    glEnd()

    # Inner square
    margin = 0.25 * cell_size
    left   = x + margin
    right  = x + cell_size - margin
    top    = y + margin
    bottom = y + cell_size - margin

    glColor3f(0.5, 0.5, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(left, top)
    glVertex2f(right, top)
    glVertex2f(right, bottom)
    glVertex2f(left, bottom)
    glEnd()

def draw_wall(row: int, col: int) -> None:
    """Draw a wall cell as a brick pattern with horizontal rows and staggered vertical joints."""
    x = col * cell_size
    y = row * cell_size
    mt = max(2.0, 0.07 * cell_size)  # mortar line thickness

    # Brick base fill (gray)
    glColor3f(0.55, 0.55, 0.55)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + cell_size, y)
    glVertex2f(x + cell_size, y + cell_size)
    glVertex2f(x, y + cell_size)
    glEnd()

    # Mortar color for all lines
    glColor3f(0.3, 0.3, 0.3)

    # Top edge mortar line (always present)
    glRectf(x, y, x + cell_size, y + mt)

    # Horizontal mortar line splitting the cell into two brick rows
    mid_y = y + cell_size / 2.0
    glRectf(x, mid_y - mt / 2.0, x + cell_size, mid_y + mt / 2.0)

    # Top brick row: single vertical joint at 50%
    jx = x + cell_size * 0.5
    glRectf(jx - mt / 2.0, y, jx + mt / 2.0, mid_y)

    # Bottom brick row: staggered joints at 25% and 75%
    for frac in (0.25, 0.75):
        jx = x + cell_size * frac
        glRectf(jx - mt / 2.0, mid_y, jx + mt / 2.0, y + cell_size)

def get_box_at(x, y):
    """Helper function to check if there is a box at the given coordinates and return it."""
    for box in phase["boxes"]:
        if box.position.x == x and box.position.y == y:
            return box
    return None

def cell_at(x: int, y: int) -> Cell:
    # Verify for movement out of bounds
    if x >= phase['grid'].width or y >= phase['grid'].height or x < 0 or y < 0:
        return Cell.OUT_OF_BOUNDS
    
    # Check if the player is on this cell
    player_pos = phase["player"].get_position()
    if player_pos.x == x and player_pos.y == y:
        return Cell.PLAYER
    
    # Gets the cell in the main grid, doesn't count player or boxes
    bottom_cell = get_grid_type(phase['grid'].grid[x][y])
    
    # Check if any box is on this cell
    box = get_box_at(x, y)
    if box:
        # If the box is on a goal cell, return BOX_ON_GOAL
        if bottom_cell == Cell.GOAL:
            return Cell.BOX_ON_GOAL
        
        elif bottom_cell == Cell.SCALE_TOGGLE:
            return Cell.BOX_ON_SCALE_TOGGLE
        
        elif bottom_cell == Cell.ROTATE_PAD:
            return Cell.BOX_ON_ROTATE_PAD
        
        else:
            return Cell.BOX

    return bottom_cell

def draw_scene() -> None:
    """Display callback: clear, paint every cell from phase["grid"], swap buffers."""
    global is_new_phase, phase
    grid_object = phase["grid"]
    grid_matrix = grid_object.grid
    # See module docstring: width attribute == row count, height == column count.
    num_rows = grid_object.width
    num_cols = grid_object.height

    if is_new_phase:
        # Window client area: columns wide, rows tall (matches glOrtho pixel space).
        glutReshapeWindow(num_cols * cell_size, num_rows * cell_size)
        is_new_phase = False

    # Avoid leftover color from previous frame; depth bit included for consistency with GLUT_DEPTH.
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    for row in range(num_rows):
        for col in range(num_cols):
            cell_type = get_grid_type(grid_matrix[row][col])
            if cell_type == Cell.WALL:
                draw_wall(row, col)
            elif cell_type == Cell.GOAL:
                glColor3f(0.18, 0.0, 0.0)
                glRectf(col * cell_size, row * cell_size, (col + 1) * cell_size, (row + 1) * cell_size)
                draw_goal(row, col)
            elif cell_type == Cell.ROTATE_PAD:
                glColor3f(0.0, 0.13, 0.15)
                glRectf(col * cell_size, row * cell_size, (col + 1) * cell_size, (row + 1) * cell_size)
                draw_rotate_pad(row, col)
            elif cell_type == Cell.SCALE_TOGGLE:
                glColor3f(0.0, 0.0, 0.13)
                glRectf(col * cell_size, row * cell_size, (col + 1) * cell_size, (row + 1) * cell_size)
                draw_scale_pad(row, col)
            else:
                draw_cell(row, col, cell_type)
    
    # Draw the player on top of the grid.
    player_pos = phase["player"].get_position()
    draw_player(player_pos.x, player_pos.y, phase["player"].size)

    # Draw the boxes on top of the grid.
    for box in phase["boxes"]:
        box_pos = box.get_position()
        # Draw the box with the appropriate color based on its position.
        draw_box(box_pos.x, box_pos.y)

    glutSwapBuffers()

def restart_phase():
    """Reload the current phase from scratch, resetting all state."""
    global phase, is_new_phase
    grid_object, player, boxes, limit = build_phase(current_phase)
    phase["grid"] = grid_object
    phase["player"] = player
    phase["boxes"] = boxes
    phase["movements_left"] = limit
    phase["movements_limit"] = limit
    phase["state"] = "playing"
    is_new_phase = True
    update_window_title()
    # Re-enable keyboard in case it was disabled
    glutKeyboardFunc(handle_keypress)

MOVE_DELTAS = {
    'w': (-1, 0),  
    's': (1, 0),   
    'a': (0, -1),  
    'd': (0, 1),   
}

def handle_keypress(key, x: int, y: int) -> None:
    """Dispatch keyboard input based on current game state."""
    key = key.decode().lower()
    global current_phase

    # Restart works in every state
    if key == 'r':
        restart_phase()
        glutPostRedisplay()
        return

    state = phase.get("state", "playing")

    if state == "playing":
        if key in MOVE_DELTAS and phase["movements_left"] > 0:
            dx, dy = MOVE_DELTAS[key]
            handle_movement(dx, dy)
            glutPostRedisplay()

    elif state == "won":
        if key == 'n':
            next_num = current_phase + 1
            next_file = f"src/game/phases/{next_num:03d}/map.json"
            if os.path.isfile(next_file):
                current_phase = next_num
                restart_phase() 
            # If last phase, 'n' does nothing
            glutPostRedisplay()

def apply_rotation():
    """Rotate the player's position 90 degrees clockwise around the center of the grid."""
    player = phase["player"]
    center_row = (phase["grid"].width - 1) / 2.0
    center_col = (phase["grid"].height - 1) / 2.0
    old_row, old_col = player.position.x, player.position.y

    new_row = int(center_row + (old_col - center_col))
    new_col = int(center_col - (old_row - center_row))

    if 0 <= new_row < phase["grid"].width and 0 <= new_col < phase["grid"].height:
        destination = cell_at(new_row, new_col)
        if is_walkable(destination):
            player.position.x, player.position.y = new_row, new_col
            player.just_rotated = True
        else:
            print("Teleport blocked by wall.")
    else:
        print("Teleport out of bounds.")

def can_place_giant(dx: int, dy: int) -> bool:
    """Return True if a 2x2 footprint starting at (dx, dy) is entirely inside the grid and contains only walkable, box‑free cells."""
    for row_offset in range(2):
        for col_offset in range(2):
            cell_x = dx + row_offset
            cell_y = dy + col_offset
            # Bounds check
            if not (0 <= cell_x < phase["grid"].width and 0 <= cell_y < phase["grid"].height):
                return False
            # Must be walkable terrain and no box present
            terrain = get_grid_type(phase["grid"].grid[cell_x][cell_y])
            if not is_walkable(terrain) or get_box_at(cell_x, cell_y) is not None:
                return False
    return True

def apply_cell_effects(cell_type: Cell, player: Player) -> None:
    """Apply effects associated with the cell type to the player."""
    if cell_type == Cell.SCALE_TOGGLE or cell_type == Cell.BOX_ON_SCALE_TOGGLE:
        if player.size == 1:
            position_valid = False
            search_x = player.position.x
            while search_x >= 0:
                if can_place_giant(search_x, player.position.y):
                    player.position.x = search_x
                    player.size = 2
                    position_valid = True
                    break
                search_x -= 1
            if not position_valid:
                print("Problem finding space for giant player.")

            
            player.size = 2
            print("Player size is now 2.")
        else:
            player.size = 1
    elif cell_type == Cell.ROTATE_PAD or cell_type == Cell.BOX_ON_ROTATE_PAD:
        if not player.just_rotated:
            apply_rotation()

def try_move_giant(dx, dy, player: Player) -> bool:
    """Attempt to move a giant player (size > 1) by (dx, dy). Returns True if the move was successful, False otherwise."""
    new_x = player.position.x + dx
    new_y = player.position.y + dy

    old_cells = player.get_cells()

    # Generate the list of cells that the giant player would occupy after the move.
    new_cells = []
    for row_offset in range(player.size):
        for col_offset in range(player.size):
            cell_x = new_x + row_offset
            cell_y = new_y + col_offset
            new_cells.append((cell_x, cell_y))

    for cell_x, cell_y in new_cells:
        # Check bounds first to avoid index errors in cell_at and get_box_at.
        if cell_x < 0 or cell_x >= phase["grid"].width or cell_y < 0 or cell_y >= phase["grid"].height:
            return False
        
        if (cell_x, cell_y) in old_cells:
            continue
        if not is_walkable(cell_at(cell_x, cell_y)):
            return False

    player.position.x = new_x
    player.position.y = new_y

    found_scale = False
    found_rotate = False

    for cell_x, cell_y in new_cells:
        if (cell_x, cell_y) in old_cells:
            continue

        cell_value = phase["grid"].grid[cell_x][cell_y]
        cell_type = get_grid_type(cell_value)

        if cell_type == Cell.SCALE_TOGGLE:
            found_scale = True
        elif cell_type == Cell.ROTATE_PAD:
            found_rotate = True

    if found_scale:
        apply_cell_effects(Cell.SCALE_TOGGLE, player)
    if found_rotate:
        apply_cell_effects(Cell.ROTATE_PAD, player)

    return True

def try_step(dx: int, dy: int) -> bool:
    """Attempt to move the player by (dx, dy). Returns True if the move was successful, False otherwise."""
    player = phase["player"]
    new_x = player.position.x + dx
    new_y = player.position.y + dy

    if player.size > 1:
        return try_move_giant(dx, dy, player)

    target = cell_at(new_x, new_y)

    # If the target cell is empty or a goal, move the player there.
    if is_walkable(target):
        player.position.x, player.position.y = new_x, new_y
        apply_cell_effects(target, player)
        return True
    
    # If the target cell has a box, we need to check if the box can be moved in the same direction.
    elif target in (Cell.BOX, Cell.BOX_ON_GOAL, Cell.BOX_ON_SCALE_TOGGLE, Cell.BOX_ON_ROTATE_PAD):
        box = get_box_at(new_x, new_y)
        if box:
            beyond_x = new_x + dx
            beyond_y = new_y + dy
            beyond_target = cell_at(beyond_x, beyond_y)
            if is_walkable(beyond_target):
                box.position.x, box.position.y = beyond_x, beyond_y
                player.position.x, player.position.y = new_x, new_y
                apply_cell_effects(target, player)

                return True
    
    # If we reach here, the move was not successful (either a wall, out of bounds, or an immovable box).
    return False

NEXT_PHASE_DELAY_MS: Final[int] = 2000


def _next_phase_path(phase_number: int) -> str:
    return f"src/game/phases/{phase_number:03d}/map.json"


def _advance_phase_timer(value: int) -> None:
    """glutTimerFunc callback: load next phase if state is still 'won'."""
    global current_phase
    if phase["state"] != "won":
        return
    next_num = current_phase + 1
    if os.path.isfile(_next_phase_path(next_num)):
        current_phase = next_num
        restart_phase()
        glutPostRedisplay()


def _schedule_next_phase_if_available() -> None:
    """Start the auto-advance timer when the next phase file exists."""
    if os.path.isfile(_next_phase_path(current_phase + 1)):
        glutTimerFunc(NEXT_PHASE_DELAY_MS, _advance_phase_timer, 0)


def handle_movement(dx: int, dy: int) -> None:
    """Process one step of movement, update counters and game state."""
    player = phase["player"]
    player.just_rotated = False

    if try_step(dx, dy):
        phase["movements_left"] -= 1
        update_window_title()

        # Check for victory or loss
        if phase["state"] == "playing" and check_victory():
            phase["state"] = "won"
            update_window_title()
            _schedule_next_phase_if_available()
        elif phase["movements_left"] <= 0 and phase["state"] == "playing":
            phase["state"] = "lost"
            update_window_title()

    

def check_victory() -> bool:
    """Return True if every box is on a goal."""
    for box in phase["boxes"]:
        if cell_at(box.position.x, box.position.y) != Cell.BOX_ON_GOAL:
            return False
    return True

def main() -> None:
    """Initialize GLUT, create window, wire callbacks, run event loop."""
    glutInit(sys.argv)
    # Double buffering + RGB color + depth buffer (depth unused for pure 2D but harmless).
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Grid: obstacles (gray), agent (red) at (0,0)")
    update_window_title()
    # Must run after glutCreateWindow: no current GL context exists before then.
    glClearColor(0.0, 0.0, 0.0, 1.0)
    # Establish pixel projection whenever the window size changes.
    glutReshapeFunc(reshape_window)
    glutDisplayFunc(draw_scene)
    glutKeyboardFunc(handle_keypress)
    # Blocks until the window is closed.
    glutMainLoop()


if __name__ == "__main__":
    main()
