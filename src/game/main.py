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
)


WINDOW_W: Final[int] = 900
WINDOW_H: Final[int] = 700

def draw_grid() -> None:
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
