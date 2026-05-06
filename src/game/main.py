from __future__ import annotations

import sys
from typing import Final
import json
from enum import Enum, auto

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_MODELVIEW,
    GL_PROJECTION,
    glClear,
    glClearColor,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
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
)


# Initial window size (pixels) before we resize to fit the grid on first draw.
WINDOW_W: Final[int] = 900
WINDOW_H: Final[int] = 700

# Pixels per map cell; window size becomes num_cols * cell_size by num_rows * cell_size.
cell_size = 50


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
        print("Player initialized at position:", self.position.x, self.position.y)

    def get_position(self) -> Position:
        return self.position
    
    def move(self, dx: int, dy: int) -> None:
        self.position.x += dx
        self.position.y += dy
    
class Box:
    def __init__(self, position: Position):
        self.position = position
        print("Box initialized at position:", self.position.x, self.position.y)

    def get_position(self) -> Position:
        return self.position

def load_map_data(phase_number: int) -> tuple[Grid, list[int], list[list[int]]]:
    """
    Read src/game/phases/{phase}/map.json and return the grid plus spawn metadata.

    Expected JSON keys: map (2D int array), agent_start_position, boxes_start_positions.
    Cell values: 0 empty, 1 obstacle, 2 goal/interest (colors chosen in draw_grid).
    """
    with open(f"src/game/phases/{phase_number:03d}/map.json", "r") as file:
        map_data = json.load(file)
    matrix = map_data["map"]
    agent_start_position = map_data["agent_start_position"]
    boxes_start_positions = map_data["boxes_start_positions"]
    # Grid(len(matrix), len(matrix[0])) => width = row count, height = col count.
    grid_object = Grid(len(matrix), len(matrix[0]))
    grid_object.grid = matrix
    return grid_object, agent_start_position, boxes_start_positions


def build_phase(phase_number: int) -> tuple[Grid, Player, list[Box]]:
    """
    Returns:
      grid:   The Grid object.
      player: A Player instance placed at the start position.
      boxes:  A list of Box instances placed at their start positions.
    """
    grid_object, agent_start_position, boxes_start_positions = load_map_data(phase_number)

    player = Player(Position(agent_start_position[0], agent_start_position[1]))
    
    boxes = []
    for box_pos in boxes_start_positions:
        box = Box(Position(box_pos[0], box_pos[1]))
        boxes.append(box)

    return grid_object, player, boxes
    
        


# First time draw_grid runs we snap the window to the map pixel size; then clear this flag.
is_new_phase = True

grid_object, player, boxes = build_phase(1)
# Mutable dict so later code can swap phases without replacing the global name.
phase = {}
phase["grid"] = grid_object
phase["player"] = player
phase["boxes"] = boxes
phase["movements_left"] = 10


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

class Color(Enum):
    """Enum for the different colors used in the grid."""
    EMPTY    = (0.0, 0.0, 0.0)
    WALL     = (0.5, 0.5, 0.5)
    GOAL     = (1.0, 0.0, 0.0)
    BOX      = (0.8, 0.5, 0.0)
    BOX_ON_GOAL = (0.4, 0.25, 0.0)
    PLAYER   = (0.2, 0.9, 0.2)

# Maps Cell types to their corresponding colors for drawing.
CELL_COLOR = {
    Cell.EMPTY:        Color.EMPTY,
    Cell.WALL:         Color.WALL,
    Cell.GOAL:         Color.GOAL,
    Cell.BOX:          Color.BOX,
    Cell.BOX_ON_GOAL:  Color.BOX_ON_GOAL,
    Cell.PLAYER:       Color.PLAYER,
}

def get_grid_type(code: int) -> Cell:
    """Helper function to convert the integer code from the grid to a Cell enum."""   
    if code == 1:
        return Cell.WALL
    elif code == 2:
        return Cell.GOAL
    return Cell.EMPTY

def draw_cell(row: int, col: int, cell_type: Cell) -> None:
    """Helper function to draw a single cell at the given row and column with the appropriate color."""
    glColor3f(*CELL_COLOR[cell_type].value)
    
    glRectf(
        col * cell_size,
        row * cell_size,
        (col + 1) * cell_size,
        (row + 1) * cell_size,
    )

def get_box_at(x, y):
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
            draw_cell(row, col, cell_type)
    
    # Draw the player on top of the grid.
    player_pos = phase["player"].get_position()
    draw_cell(player_pos.x, player_pos.y, Cell.PLAYER)

    # Draw the boxes on top of the grid.
    for box in phase["boxes"]:
        box_pos = box.get_position()
        # Draw the box with the appropriate color based on its position.
        draw_cell(box_pos.x, box_pos.y, cell_at(box_pos.x, box_pos.y))

    glutSwapBuffers()

MOVE_DELTAS = {
    'w': (-1, 0),  
    's': (1, 0),   
    'a': (0, -1),  
    'd': (0, 1),   
}

def handle_keypress(key, x: int, y: int) -> None:
    """Keyboard callback: move player with WASD using the move method, then redraw."""
    key = key.decode().lower()
    if key in MOVE_DELTAS:
        dx, dy = MOVE_DELTAS[key]
        handle_movement(dx, dy)
    

    glutPostRedisplay()

def handle_movement(dx, dy):
    player = phase["player"]
    new_x = player.position.x + dx
    new_y = player.position.y + dy
    # check what is in the cell the player is trying to move into
    target = cell_at(new_x, new_y)
    # if it's empty or a goal, move the player there; if it's a box, check the cell beyond it and move both if possible
    if target in (Cell.EMPTY, Cell.GOAL):
        player.position.x, player.position.y = new_x, new_y
    elif target in (Cell.BOX, Cell.BOX_ON_GOAL):
        # find the box object in phase["boxes"] at (new_x, new_y)
        box = get_box_at(new_x, new_y)
        if box:
            # check cell beyond the box to understand if it can move or not
            beyond_x = new_x + dx
            beyond_y = new_y + dy
            beyond_target = cell_at(beyond_x, beyond_y)
            if beyond_target in (Cell.EMPTY, Cell.GOAL):
                # move the box
                box.position.x, box.position.y = beyond_x, beyond_y
                # move the player
                player.position.x, player.position.y = new_x, new_y
    
    if check_victory():
        print("Phase completed!")
        glutSetWindowTitle(b"Phase Complete!")
        # Disable further input after victory.
        glutKeyboardFunc(None)

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
