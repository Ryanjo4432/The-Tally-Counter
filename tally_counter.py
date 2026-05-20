import sys
import json
import math
import threading
import time
import shutil
import random
from pathlib import Path

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

from PyQt6.QtWidgets import QApplication, QWidget, QDialog
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont, QCursor
)

WOOD_DARKEST  = QColor(10,  6,  2)
WOOD_DARK     = QColor(26, 15,  7)
WOOD_MID      = QColor(46, 28, 11)
WOOD_GRAIN_1  = QColor(32, 19,  8)
WOOD_GRAIN_2  = QColor(55, 34, 13)

BRASS_DARKEST = QColor(48, 32,  6)
BRASS_DARK    = QColor(82, 58, 12)
BRASS_MID     = QColor(142, 102, 24)
BRASS_LIGHT   = QColor(192, 150, 48)
BRASS_BRIGHT  = QColor(228, 188, 72)
BRASS_SHINE   = QColor(252, 224, 120)

IRON_DARKEST  = QColor(16, 16, 20)
IRON_DARK     = QColor(28, 28, 35)
IRON_MID      = QColor(50, 52, 62)
IRON_LIGHT    = QColor(78, 80, 95)
IRON_SHINE    = QColor(108, 112, 130)

COPPER_DARK   = QColor(82,  40, 14)
COPPER_MID    = QColor(132, 68, 26)
COPPER_LIGHT  = QColor(168, 96, 42)

PARCHMENT     = QColor(214, 188, 128)
PARCHMENT_DIM = QColor(172, 146, 88)
PARCHMENT_OLD = QColor(192, 162, 104)

COUNTER_BG    = QColor(7,  4,  1)
COUNTER_DIG   = QColor(218, 192, 96)
COUNTER_GHOST = QColor(88,  68, 24)

