from __future__ import annotations

import sys
from typing import Final, Sequence

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
    glutReshapeWindow
)


WINDOW_W: Final[int] = 900
WINDOW_H: Final[int] = 700

cell_size = 50

class Grid:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = [[0 for _ in range(width)] for _ in range(height)]

is_new_phase = True
phase = {
    "grid": Grid(10, 10),
    "movements_left": 10,
}

def draw_grid() -> None:
    global is_new_phase, phase
    if is_new_phase:
        grid = phase["grid"]
        glutReshapeWindow(grid.width * cell_size, grid.height * cell_size)
        is_new_phase = False
    pass

def main() -> None:
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Grid: obstacles (gray), agent (red) at (0,0)")
    glutDisplayFunc(draw_grid)
    glutMainLoop()


if __name__ == "__main__":
    main()
