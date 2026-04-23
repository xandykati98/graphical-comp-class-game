from __future__ import annotations

import sys
from typing import Final, Sequence
import json

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


def load_map(phase_number: int) -> dict:
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


# First time draw_grid runs we snap the window to the map pixel size; then clear this flag.
is_new_phase = True

grid_object, agent_start_position, boxes_start_positions = load_map(1)
# Mutable dict so later code can swap phases without replacing the global name.
phase = {
    "grid": grid_object,
    "agent_start_position": agent_start_position,
    "boxes_start_positions": boxes_start_positions,
    "movements_left": 10,
}


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


def draw_grid() -> None:
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
            cell_value = grid_matrix[row][col]
            if cell_value == 1:
                # Obstacle
                glColor3f(0.5, 0.5, 0.5)
            elif cell_value == 2:
                # Goal / interest
                glColor3f(1.0, 0.0, 0.0)
            else:
                # Empty: explicit black so we do not reuse the previous cell's color.
                glColor3f(0.0, 0.0, 0.0)
            # Screen X from column, screen Y from row (see module docstring).
            glRectf(
                col * cell_size,
                row * cell_size,
                (col + 1) * cell_size,
                (row + 1) * cell_size,
            )
    # Double-buffered: show the frame we just drew.
    glutSwapBuffers()


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
    glutDisplayFunc(draw_grid)
    # Blocks until the window is closed.
    glutMainLoop()


if __name__ == "__main__":
    main()
