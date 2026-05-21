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


class CounterData:
    def __init__(self):
        base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        self.path     = base / 'tally_data.json'
        self.backup   = base / 'tally_data.bak'
        self.tmp_path = base / 'tally_data.tmp'

    def load(self) -> int:
        for p in (self.path, self.backup):
            try:
                if p.exists():
                    v = int(json.loads(p.read_text(encoding='utf-8')).get('count', 0))
                    return max(0, min(v, 1_000_000))
            except Exception:
                continue
        return 0

    def save(self, count: int):
        try:
            self.tmp_path.write_text(
                json.dumps({'count': count, 'version': 2}), encoding='utf-8')
            if self.path.exists():
                shutil.copy2(self.path, self.backup)
            self.tmp_path.replace(self.path)
        except Exception:
            pass


def _play_async(fn):
    threading.Thread(target=fn, daemon=True).start()

def play_click():
    if not HAS_SOUND:
        return
    def _():
        try:
            winsound.Beep(880, 18)
            time.sleep(0.008)
            winsound.Beep(440, 12)
        except Exception:
            pass
    _play_async(_)

def play_reset():
    if not HAS_SOUND:
        return
    def _():
        try:
            for f in (500, 350, 200):
                winsound.Beep(f, 22)
        except Exception:
            pass
    _play_async(_)


def draw_gear(painter: QPainter, cx: float, cy: float,
              outer_r: float, inner_r: float, teeth: int, angle: float,
              col_dark: QColor, col_mid: QColor, col_light: QColor,
              col_shine: QColor):
    painter.save()
    painter.translate(cx, cy)
    painter.rotate(angle)

    path = QPainterPath()
    n = teeth * 4
    half_tooth = math.pi / teeth * 0.55

    for i in range(n + 1):
        tooth_i = i // 4
        sub     = i %  4
        base_a  = 2 * math.pi * tooth_i / teeth
        if sub == 0:
            a, r = base_a - half_tooth * 0.6, inner_r
        elif sub == 1:
            a, r = base_a - half_tooth * 0.5, outer_r
        elif sub == 2:
            a, r = base_a + half_tooth * 0.5, outer_r
        else:
            a, r = base_a + half_tooth * 0.6, inner_r
        x, y = r * math.cos(a), r * math.sin(a)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()

    g = QRadialGradient(outer_r * 0.2, -outer_r * 0.25, outer_r * 1.4)
    g.setColorAt(0.0, col_shine)
    g.setColorAt(0.3, col_light)
    g.setColorAt(0.65, col_mid)
    g.setColorAt(1.0, col_dark)
    painter.setPen(QPen(col_dark, 1.2))
    painter.setBrush(QBrush(g))
    painter.drawPath(path)

    for k in range(min(teeth // 2, 6)):
        ha = 2 * math.pi * k / min(teeth // 2, 6)
        hx = inner_r * 0.72 * math.cos(ha)
        hy = inner_r * 0.72 * math.sin(ha)
        hr = inner_r * 0.1
        hg = QRadialGradient(hx - hr*0.3, hy - hr*0.3, hr * 2)
        hg.setColorAt(0, col_light)
        hg.setColorAt(0.4, col_mid)
        hg.setColorAt(1, col_dark)
        painter.setPen(QPen(col_dark, 0.5))
        painter.setBrush(QBrush(hg))
        painter.drawEllipse(QPointF(hx, hy), hr, hr)

    hub_r = inner_r * 0.28
    hg2 = QRadialGradient(-hub_r*0.3, -hub_r*0.4, hub_r * 2.2)
    hg2.setColorAt(0, col_light)
    hg2.setColorAt(0.5, col_mid)
    hg2.setColorAt(1, col_dark)
    painter.setPen(QPen(col_dark, 1))
    painter.setBrush(QBrush(hg2))
    painter.drawEllipse(QPointF(0, 0), hub_r, hub_r)

    pin_r = hub_r * 0.35
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(col_dark)
    painter.drawEllipse(QPointF(0, 0), pin_r, pin_r)
    painter.restore()


def draw_rivet(painter: QPainter, cx: float, cy: float, r: float,
               col_dark=None, col_mid=None, col_light=None):
    if col_dark  is None: col_dark  = BRASS_DARK
    if col_mid   is None: col_mid   = BRASS_MID
    if col_light is None: col_light = BRASS_SHINE
    g = QRadialGradient(cx - r*0.35, cy - r*0.4, r * 2.0)
    g.setColorAt(0.0, col_light)
    g.setColorAt(0.45, col_mid)
    g.setColorAt(1.0, col_dark)
    painter.setPen(QPen(col_dark, 0.6))
    painter.setBrush(QBrush(g))
    painter.drawEllipse(QPointF(cx, cy), r, r)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(col_dark)
    painter.drawEllipse(QPointF(cx, cy), r * 0.22, r * 0.22)


class PirateDialog(QDialog):
    confirmed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(340, 180)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._result = False
        self._drag_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        shad = QRectF(4, 4, w-4, h-4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 100))
        p.drawRoundedRect(shad, 10, 10)

        bg = QRectF(0, 0, w-4, h-4)
        wg = QLinearGradient(0, 0, w, h)
        wg.setColorAt(0, WOOD_MID)
        wg.setColorAt(0.5, WOOD_DARK)
        wg.setColorAt(1, WOOD_DARKEST)
        p.setBrush(QBrush(wg))
        p.drawRoundedRect(bg, 10, 10)

        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(bg, 10, 10)
        p.setClipPath(clip)
        p.setOpacity(0.18)
        p.setPen(QPen(WOOD_GRAIN_2, 1))
        for y in range(0, h, 4):
            p.drawLine(0, y, w, y)
        p.restore()

        p.setPen(QPen(BRASS_BRIGHT, 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(bg.adjusted(1, 1, -1, -1), 9, 9)
        p.setPen(QPen(BRASS_DARK, 1))
        p.drawRoundedRect(bg.adjusted(4, 4, -4, -4), 7, 7)

        for rx, ry in [(10, 10), (w-14, 10), (10, h-14), (w-14, h-14)]:
            draw_rivet(p, rx, ry, 5)

        tf = QFont("Palatino Linotype", 12, QFont.Weight.Bold)
        p.setFont(tf)
        p.setPen(QPen(BRASS_DARK))
        p.drawText(QRectF(0, 18, w-4, 28).translated(1, 1), Qt.AlignmentFlag.AlignCenter, "~  RESET TALLY  ~")
        p.setPen(QPen(PARCHMENT))
        p.drawText(QRectF(0, 18, w-4, 28), Qt.AlignmentFlag.AlignCenter, "~  RESET TALLY  ~")

        p.setPen(QPen(BRASS_MID, 1))
        p.drawLine(20, 50, w-24, 50)

        mf = QFont("Palatino Linotype", 9)
        p.setFont(mf)
        p.setPen(QPen(PARCHMENT_DIM))
        p.drawText(QRectF(20, 55, w-44, 45),
                   Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                   "Shall the tally be struck to zero?\nThis deed cannot be undone.")

        self._draw_btn(p, self._yes_rect(), "Aye, Reset", danger=True)
        self._draw_btn(p, self._no_rect(),  "Nay, Keep",  danger=False)
        p.end()

    def _yes_rect(self): return QRectF(20, 118, 130, 40)
    def _no_rect(self):  return QRectF(170, 118, 130, 40)

    def _draw_btn(self, p: QPainter, rect: QRectF, label: str, danger: bool):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawRoundedRect(rect.translated(2, 2), 6, 6)

        if danger:
            fg = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            fg.setColorAt(0, QColor(100, 30, 10))
            fg.setColorAt(0.5, QColor(70, 20, 5))
            fg.setColorAt(1, QColor(50, 15, 3))
        else:
            fg = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            fg.setColorAt(0, BRASS_MID)
            fg.setColorAt(0.5, BRASS_DARK)
            fg.setColorAt(1, BRASS_DARKEST)
        p.setBrush(QBrush(fg))
        p.setPen(QPen(BRASS_BRIGHT if not danger else QColor(200, 100, 50), 1.5))
        p.drawRoundedRect(rect, 6, 6)

        bf = QFont("Palatino Linotype", 9, QFont.Weight.Bold)
        p.setFont(bf)
        p.setPen(QPen(PARCHMENT))
        p.drawText(rect.toRect(), Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            if self._yes_rect().toRect().contains(pos):
                self._result = True
                self.accept()
                return
            if self._no_rect().toRect().contains(pos):
                self._result = False
                self.reject()
                return
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def was_confirmed(self) -> bool:
        return self._result


WIN_W = 480
WIN_H = 540


class TallyCounter(QWidget):
    def __init__(self):
        super().__init__()
        self.data  = CounterData()
        self.count = self.data.load()

        self.gear_a1   = 0.0
        self.gear_a2   = 0.0
        self.gear_a3   = 0.0
        self.gear_a4   = 0.0
        self.btn_depth = 0.0
        self.roll      = [0.0] * 6
        self.flicker   = 12
        self.hover_btn = False
        self.hover_rst = False

        self._btn_rect = QRect(75, 258, 330, 78)
        self._rst_rect = QRect(140, 352, 200, 48)
        self._cls_rect = QRect(WIN_W-38,  8, 28, 28)
        self._min_rect = QRect(WIN_W-70,  8, 28, 28)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

        self.setFixedSize(WIN_W, WIN_H)
        self.setWindowTitle("The Tally Counter")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._drag_pos = None

    def _tick(self):
        self.gear_a1 = (self.gear_a1 + 0.50) % 360
        self.gear_a2 = (self.gear_a2 - 0.32) % 360
        self.gear_a3 = (self.gear_a3 + 0.20) % 360
        self.gear_a4 = (self.gear_a4 - 0.42) % 360

        for i in range(6):
            if self.roll[i] > 0:
                self.roll[i] = max(0.0, self.roll[i] - 0.09)

        if self.btn_depth > 0:
            self.btn_depth = max(0.0, self.btn_depth - 0.12)

        self.flicker = max(0, int(random.gauss(14, 6)))
        self.update()

    def _increment(self):
        if self.count >= 1_000_000:
            return
        old = self.count
        self.count += 1
        self.data.save(self.count)
        for i in range(6):
            if (old // (10 ** (5-i))) % 10 != (self.count // (10 ** (5-i))) % 10:
                self.roll[i] = 1.0
        self.btn_depth = 1.0
        play_click()

    def _do_reset(self):
        play_reset()
        dlg = PirateDialog(self)
        dlg.move(self.x() + (WIN_W - dlg.width())//2,
                 self.y() + (WIN_H - dlg.height())//2)
        dlg.exec()
        if dlg.was_confirmed():
            self.count = 0
            self.data.save(0)
            for i in range(6):
                self.roll[i] = 0.3

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = WIN_W, WIN_H
        self._paint_wood(p, w, h)
        self._paint_brass_frame(p, w, h)
        self._paint_top_bar(p, w)
        self._paint_gears(p, w, h)
        self._paint_counter(p, w)
        self._paint_click_button(p, w)
        self._paint_reset_button(p, w)
        self._paint_decorations(p, w, h)
        self._paint_window_controls(p, w)
        self._paint_candle_glow(p, w, h)
        p.end()

    def _paint_wood(self, p: QPainter, w: int, h: int):
        margin = 5
        panel  = QRectF(margin, margin, w - margin*2, h - margin*2)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 160))
        p.drawRoundedRect(QRectF(margin+5, margin+5, w-margin*2, h-margin*2), 14, 14)

        wg = QLinearGradient(0, 0, w, h)
        wg.setColorAt(0.00, WOOD_MID)
        wg.setColorAt(0.25, WOOD_DARK)
        wg.setColorAt(0.60, WOOD_DARKEST)
        wg.setColorAt(0.85, WOOD_DARK)
        wg.setColorAt(1.00, WOOD_MID)
        clip = QPainterPath()
        clip.addRoundedRect(panel, 12, 12)
        p.fillPath(clip, QBrush(wg))

        p.save()
        p.setClipPath(clip)
        for y in range(0, h, 5):
            mx    = math.sin(y * 0.07) * 2.5 + math.sin(y * 0.023) * 1.2
            alpha = 22 if (y // 5) % 3 == 0 else 12
            p.setPen(QPen(QColor(WOOD_GRAIN_1.red(), WOOD_GRAIN_1.green(),
                                  WOOD_GRAIN_1.blue(), alpha), 0.8))
            p.drawLine(QPointF(margin + mx, y), QPointF(w - margin + mx, y))
        p.restore()

    def _paint_brass_frame(self, p: QPainter, w: int, h: int):
        specs = [
            (BRASS_DARKEST, 10, 5.0),
            (BRASS_BRIGHT,   2, 5.0),
            (BRASS_MID,      1, 7.5),
            (BRASS_DARK,     1, 13.0),
            (BRASS_LIGHT,    1, 14.5),
        ]
        p.setBrush(Qt.BrushStyle.NoBrush)
        for col, thickness, inset in specs:
            p.setPen(QPen(col, thickness))
            p.drawRoundedRect(QRectF(inset, inset, w-inset*2, h-inset*2), 10, 10)
        for cx, cy in [(22, 22), (w-22, 22), (22, h-22), (w-22, h-22)]:
            draw_rivet(p, cx, cy, 7)

    def _paint_top_bar(self, p: QPainter, w: int):
        plate = QRectF(55, 14, w - 110, 42)

        pg = QLinearGradient(plate.left(), plate.top(), plate.right(), plate.bottom())
        pg.setColorAt(0.0, BRASS_DARK)
        pg.setColorAt(0.2, BRASS_MID)
        pg.setColorAt(0.5, BRASS_LIGHT)
        pg.setColorAt(0.8, BRASS_MID)
        pg.setColorAt(1.0, BRASS_DARK)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(pg))
        p.drawRoundedRect(plate, 4, 4)

        p.setPen(QPen(BRASS_SHINE, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(plate, 4, 4)
        p.setPen(QPen(BRASS_DARKEST, 0.8))
        p.drawRoundedRect(plate.adjusted(2, 2, -2, -2), 3, 3)

        for rx, ry in [(plate.left()+8, plate.center().y()),
                       (plate.right()-8, plate.center().y())]:
            draw_rivet(p, rx, ry, 4.5)

        title = "~   THE  TALLY  COUNTER   ~"
        tf = QFont("Palatino Linotype", 12, QFont.Weight.Bold)
        p.setFont(tf)
        p.setPen(QPen(BRASS_DARKEST))
        p.drawText(plate.adjusted(1.5, 1.5, 1.5, 1.5).toRect(),
                   Qt.AlignmentFlag.AlignCenter, title)
        p.setPen(QPen(BRASS_SHINE))
        p.drawText(plate.adjusted(-0.7, -0.7, -0.7, -0.7).toRect(),
                   Qt.AlignmentFlag.AlignCenter, title)
        p.setPen(QPen(PARCHMENT_DIM))
        p.drawText(plate.toRect(), Qt.AlignmentFlag.AlignCenter, title)

    def _paint_gears(self, p: QPainter, w: int, h: int):
        draw_gear(p, 50, 100, 34, 22, 13, self.gear_a1,
                  IRON_DARKEST, IRON_MID, IRON_LIGHT, IRON_SHINE)
        draw_gear(p, w-50, 100, 28, 18, 10, self.gear_a2,
                  BRASS_DARKEST, BRASS_MID, BRASS_LIGHT, BRASS_SHINE)
        draw_gear(p, 44, h-62, 20, 13, 8, self.gear_a3,
                  COPPER_DARK, COPPER_MID, COPPER_LIGHT, BRASS_LIGHT)
        draw_gear(p, w-44, h-62, 22, 14, 9, self.gear_a4,
                  IRON_DARK, IRON_MID, IRON_LIGHT, IRON_SHINE)

        shaft_pen = QPen(IRON_MID, 3)
        shaft_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(shaft_pen)
        p.drawLine(QPointF(50, 100), QPointF(50, 84))
        p.drawLine(QPointF(w-50, 100), QPointF(w-50, 84))

    def _paint_counter(self, p: QPainter, w: int):
        housing = QRectF(28, 66, w - 56, 168)

        hg = QLinearGradient(housing.left(), housing.top(),
                              housing.right(), housing.bottom())
        hg.setColorAt(0.0, IRON_DARK)
        hg.setColorAt(0.3, QColor(26, 26, 34))
        hg.setColorAt(0.7, QColor(22, 22, 30))
        hg.setColorAt(1.0, IRON_DARK)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hg))
        p.drawRoundedRect(housing, 9, 9)

        p.setPen(QPen(BRASS_LIGHT, 2.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(housing, 9, 9)
        p.setPen(QPen(BRASS_SHINE, 0.8))
        p.drawRoundedRect(housing.adjusted(2.5, 2.5, -2.5, -2.5), 7, 7)
        p.setPen(QPen(BRASS_DARKEST, 0.8))
        p.drawRoundedRect(housing.adjusted(5, 5, -5, -5), 6, 6)

        for rx, ry in [(housing.left()+14, housing.top()+12),
                       (housing.right()-14, housing.top()+12),
                       (housing.left()+14, housing.bottom()-12),
                       (housing.right()-14, housing.bottom()-12)]:
            draw_rivet(p, rx, ry, 5.5)

        ag = QRadialGradient(housing.center().x(), housing.center().y()*0.8,
                              housing.width() * 0.45)
        ag.setColorAt(0.0, QColor(255, 155, 28, 28 + self.flicker))
        ag.setColorAt(0.6, QColor(200, 110, 15, 12))
        ag.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(housing, QBrush(ag))

        lf = QFont("Palatino Linotype", 7)
        p.setFont(lf)
        p.setPen(QPen(PARCHMENT_DIM))
        p.drawText(QRectF(housing.left(), housing.bottom()-20,
                           housing.width(), 18).toRect(),
                   Qt.AlignmentFlag.AlignCenter, "~  REGISTERED  COUNT  ~")

        win = QRectF(44, 82, w - 88, 120)

        wg = QRadialGradient(win.center().x(), win.center().y(), win.width()*0.6)
        wg.setColorAt(0.0, QColor(14, 9, 2))
        wg.setColorAt(1.0, COUNTER_BG)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(wg))
        p.drawRoundedRect(win, 6, 6)

        count_str = f"{self.count:06d}"
        dw = win.width() / 6
        dh = win.height()
        for i, ch in enumerate(count_str):
            self._paint_digit(p, QRectF(win.left() + i*dw, win.top(), dw, dh),
                              int(ch), self.roll[i])

        p.setPen(QPen(BRASS_DARKEST, 1.2))
        for i in range(1, 6):
            x = win.left() + i * dw
            p.drawLine(QPointF(x, win.top()+3), QPointF(x, win.bottom()-3))

        mid_y = win.center().y()
        p.setPen(QPen(QColor(BRASS_MID.red(), BRASS_MID.green(), BRASS_MID.blue(), 80), 1.5))
        p.drawLine(QPointF(win.left()+2, mid_y - dh*0.04),
                   QPointF(win.right()-2, mid_y - dh*0.04))
        p.drawLine(QPointF(win.left()+2, mid_y + dh*0.44),
                   QPointF(win.right()-2, mid_y + dh*0.44))

        glass_g = QLinearGradient(win.left(), win.top(), win.right(), win.bottom())
        glass_g.setColorAt(0.0, QColor(255, 255, 255, 18))
        glass_g.setColorAt(0.1, QColor(255, 255, 255,  8))
        glass_g.setColorAt(0.5, QColor(255, 255, 255,  3))
        glass_g.setColorAt(0.9, QColor(255, 255, 255,  6))
        glass_g.setColorAt(1.0, QColor(255, 255, 255, 14))
        p.fillRect(win, QBrush(glass_g))

        p.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
        p.drawLine(QPointF(win.left()+30, win.top()+8),  QPointF(win.left()+80, win.top()+22))
        p.drawLine(QPointF(win.right()-50, win.top()+5), QPointF(win.right()-25, win.top()+18))

        p.setPen(QPen(BRASS_BRIGHT, 3.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(win, 6, 6)
        p.setPen(QPen(BRASS_SHINE, 1))
        p.drawRoundedRect(win.adjusted(-1.5, -1.5, 1.5, 1.5), 7, 7)
        p.setPen(QPen(BRASS_DARKEST, 1))
        p.drawRoundedRect(win.adjusted(2.5, 2.5, -2.5, -2.5), 5, 5)

        for rx, ry in [(win.left()-10, win.top()-10), (win.right()+10, win.top()-10),
                       (win.left()-10, win.bottom()+10), (win.right()+10, win.bottom()+10)]:
            draw_rivet(p, rx, ry, 6)

    def _paint_digit(self, p: QPainter, rect: QRectF, digit: int, roll: float):
        p.save()
        p.setClipRect(rect)

        sg = QLinearGradient(rect.left(), 0, rect.right(), 0)
        sg.setColorAt(0.00, QColor(4,  2, 0))
        sg.setColorAt(0.08, QColor(10, 6, 1))
        sg.setColorAt(0.50, QColor(16, 11, 3))
        sg.setColorAt(0.92, QColor(10, 6, 1))
        sg.setColorAt(1.00, QColor(4,  2, 0))
        p.fillRect(rect, QBrush(sg))

        fs   = int(rect.height() * 0.62)
        font = QFont("Palatino Linotype", fs, QFont.Weight.Bold)
        p.setFont(font)
        h = rect.height()

        if roll > 0.01:
            old_d    = (digit - 1) % 10
            old_rect = QRectF(rect.left(), rect.top() - (1.0 - roll) * h, rect.width(), h)
            p.setPen(QPen(QColor(COUNTER_GHOST.red(), COUNTER_GHOST.green(),
                                  COUNTER_GHOST.blue(), int(255 * roll))))
            p.drawText(old_rect, Qt.AlignmentFlag.AlignCenter, str(old_d))

            new_rect = QRectF(rect.left(), rect.top() + roll * h, rect.width(), h)
            p.setPen(QPen(QColor(COUNTER_DIG.red(), COUNTER_DIG.green(),
                                  COUNTER_DIG.blue(), int(255 * (1.0 - roll * 0.4)))))
            p.drawText(new_rect, Qt.AlignmentFlag.AlignCenter, str(digit))
        else:
            p.setPen(QPen(COUNTER_DIG))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(digit))

        top_g = QLinearGradient(0, rect.top(), 0, rect.top() + h*0.32)
        top_g.setColorAt(0, QColor(0, 0, 0, 210))
        top_g.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(rect, QBrush(top_g))

        bot_g = QLinearGradient(0, rect.bottom() - h*0.32, 0, rect.bottom())
        bot_g.setColorAt(0, QColor(0, 0, 0, 0))
        bot_g.setColorAt(1, QColor(0, 0, 0, 210))
        p.fillRect(rect, QBrush(bot_g))
        p.restore()

    def _paint_click_button(self, p: QPainter, w: int):
        rect  = self._btn_rect
        depth = self.btn_depth
        hover = self.hover_btn
        shift = int(4 * depth)

        shadow_size = int(7 * (1.0 - depth))
        if shadow_size > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 130))
            p.drawRoundedRect(rect.adjusted(shadow_size, shadow_size, shadow_size, shadow_size), 13, 13)

        fr = rect.adjusted(shift, shift, shift, shift)

        bevel_path = QPainterPath()
        bevel_path.addRoundedRect(QRectF(fr), 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(IRON_SHINE.red(), IRON_SHINE.green(), IRON_SHINE.blue(), 90)
                   if depth < 0.4 else QColor(0, 0, 0, 90))
        p.drawPath(bevel_path)

        fg = QLinearGradient(fr.left(), fr.top(), fr.left(), fr.bottom())
        if depth < 0.3:
            fg.setColorAt(0.00, IRON_LIGHT)
            fg.setColorAt(0.12, IRON_MID)
            fg.setColorAt(0.50, IRON_DARK)
            fg.setColorAt(0.88, IRON_MID)
            fg.setColorAt(1.00, IRON_LIGHT)
        else:
            fg.setColorAt(0.00, IRON_DARKEST)
            fg.setColorAt(0.35, IRON_MID)
            fg.setColorAt(0.65, IRON_MID)
            fg.setColorAt(1.00, IRON_DARKEST)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fg))
        p.drawRoundedRect(QRectF(fr), 11, 11)

        if hover:
            hg = QRadialGradient(fr.center().x(), fr.center().y(), fr.width() * 0.6)
            hg.setColorAt(0.0, QColor(BRASS_BRIGHT.red(), BRASS_BRIGHT.green(), BRASS_BRIGHT.blue(), 30))
            hg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(fr), QBrush(hg))

        bg = QLinearGradient(fr.left(), fr.top(), fr.right(), fr.bottom())
        bg.setColorAt(0.0, BRASS_SHINE)
        bg.setColorAt(0.4, BRASS_LIGHT)
        bg.setColorAt(0.8, BRASS_MID)
        bg.setColorAt(1.0, BRASS_DARK)
        p.setPen(QPen(QBrush(bg), 3.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(fr), 11, 11)

        p.setPen(QPen(IRON_DARKEST, 1.2))
        p.drawRoundedRect(QRectF(fr).adjusted(5, 5, -5, -5), 8, 8)
        p.setPen(QPen(QColor(IRON_SHINE.red(), IRON_SHINE.green(),
                              IRON_SHINE.blue(), 60), 0.6))
        p.drawRoundedRect(QRectF(fr).adjusted(6, 6, -6, -6), 7, 7)

        for rx, ry in [(fr.left()+14, fr.top()+12), (fr.right()-14, fr.top()+12),
                       (fr.left()+14, fr.bottom()-12), (fr.right()-14, fr.bottom()-12)]:
            draw_rivet(p, rx, ry, 5)

        label = "✦   M A R K   ✦"
        bf = QFont("Palatino Linotype", 20, QFont.Weight.Bold)
        p.setFont(bf)
        p.setPen(QPen(IRON_DARKEST))
        p.drawText(QRectF(fr).adjusted(2, 2, 2, 2).toRect(), Qt.AlignmentFlag.AlignCenter, label)
        p.setPen(QPen(QColor(IRON_SHINE.red(), IRON_SHINE.green(), IRON_SHINE.blue(), 120)))
        p.drawText(QRectF(fr).adjusted(-0.7, -0.7, -0.7, -0.7).toRect(), Qt.AlignmentFlag.AlignCenter, label)
        p.setPen(QPen(PARCHMENT_OLD if depth < 0.3 else PARCHMENT_DIM))
        p.drawText(QRectF(fr).toRect(), Qt.AlignmentFlag.AlignCenter, label)

        if depth < 0.45:
            shine = QRectF(fr.left()+14, fr.top()+3, fr.width()-28, 3.5)
            sg = QLinearGradient(shine.left(), 0, shine.right(), 0)
            sg.setColorAt(0.0,  QColor(255, 255, 255,  0))
            sg.setColorAt(0.25, QColor(255, 255, 255, 55))
            sg.setColorAt(0.75, QColor(255, 255, 255, 55))
            sg.setColorAt(1.0,  QColor(255, 255, 255,  0))
            p.fillRect(shine, QBrush(sg))

    def _paint_reset_button(self, p: QPainter, w: int):
        rect  = self._rst_rect
        hover = self.hover_rst

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.adjusted(3, 3, 3, 3), 8, 8)

        fg = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        fg.setColorAt(0.0, COPPER_LIGHT)
        fg.setColorAt(0.4, COPPER_MID)
        fg.setColorAt(0.8, COPPER_DARK)
        fg.setColorAt(1.0, QColor(50, 22, 6))
        p.setBrush(QBrush(fg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 7, 7)

        if hover:
            hg = QRadialGradient(rect.center().x(), rect.center().y(), rect.width()*0.5)
            hg.setColorAt(0, QColor(BRASS_BRIGHT.red(), BRASS_BRIGHT.green(), BRASS_BRIGHT.blue(), 40))
            hg.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(rect, QBrush(hg))

        p.setPen(QPen(BRASS_MID, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 7, 7)
        p.setPen(QPen(BRASS_SHINE, 0.7))
        p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

        for rx, ry in [(rect.left()+9, rect.top()+9), (rect.right()-9, rect.top()+9),
                       (rect.left()+9, rect.bottom()-9), (rect.right()-9, rect.bottom()-9)]:
            draw_rivet(p, rx, ry, 4, COPPER_DARK, COPPER_MID, COPPER_LIGHT)

        rf = QFont("Palatino Linotype", 11, QFont.Weight.Bold)
        p.setFont(rf)
        p.setPen(QPen(COPPER_DARK))
        p.drawText(rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, "*   RESET   *")
        p.setPen(QPen(PARCHMENT_DIM))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "*   RESET   *")

        shine = QRectF(rect.left()+10, rect.top()+3, rect.width()-20, 2.5)
        sg = QLinearGradient(shine.left(), 0, shine.right(), 0)
        sg.setColorAt(0,   QColor(255, 255, 255,  0))
        sg.setColorAt(0.4, QColor(255, 255, 255, 40))
        sg.setColorAt(0.6, QColor(255, 255, 255, 40))
        sg.setColorAt(1,   QColor(255, 255, 255,  0))
        p.fillRect(shine, QBrush(sg))

    def _paint_decorations(self, p: QPainter, w: int, h: int):
        p.save()

        for y, alpha in [(244, 80), (246, 40), (248, 18)]:
            p.setPen(QPen(QColor(BRASS_MID.red(), BRASS_MID.green(),
                                  BRASS_MID.blue(), alpha), 1))
            p.drawLine(25, y, w-25, y)

        for y, alpha in [(408, 70), (410, 35)]:
            p.setPen(QPen(QColor(BRASS_MID.red(), BRASS_MID.green(),
                                  BRASS_MID.blue(), alpha), 1))
            p.drawLine(25, y, w-25, y)

        cx, cy = w//2, 450
        self._paint_compass(p, cx, cy, 26)
        self._paint_anchor(p, cx - 52, cy)
        self._paint_anchor(p, cx + 52, cy)

        tick_pen = QPen(BRASS_DARK, 0.9)
        p.setPen(tick_pen)
        for x in range(32, w-32, 14):
            idx = (x - 32) // 14
            p.drawLine(x, h-30, x, h-30-(8 if idx % 5 == 0 else 4))

        lf = QFont("Palatino Linotype", 7)
        p.setFont(lf)
        p.setPen(QPen(PARCHMENT_DIM))
        p.drawText(QRect(0, 246, w, 16), Qt.AlignmentFlag.AlignCenter,
                   "--  Press to increment the tally  --")
        p.restore()

    def _paint_compass(self, p: QPainter, cx: int, cy: int, r: int):
        p.setPen(QPen(BRASS_DARK, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r*0.30, r*0.30)

        for a in range(0, 360, 45):
            rad   = math.radians(a)
            tip_r = r if a % 90 == 0 else r*0.65
            x0 = cx + r*0.30 * math.cos(rad)
            y0 = cy + r*0.30 * math.sin(rad)
            x1 = cx + tip_r  * math.cos(rad)
            y1 = cy + tip_r  * math.sin(rad)
            p.setPen(QPen(BRASS_LIGHT if a % 90 == 0 else BRASS_DARK,
                          1.5 if a % 90 == 0 else 1))
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))

        cf = QFont("Palatino Linotype", 5, QFont.Weight.Bold)
        p.setFont(cf)
        p.setPen(QPen(BRASS_LIGHT))
        for label, angle in (("N", 270), ("S", 90), ("E", 0), ("W", 180)):
            rad = math.radians(angle)
            p.drawText(int(cx + (r+7) * math.cos(rad) - 3),
                       int(cy + (r+7) * math.sin(rad) + 4), label)

    def _paint_anchor(self, p: QPainter, cx: float, cy: float):
        r = 10
        p.setPen(QPen(BRASS_DARK, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy - r*0.4), r*0.28, r*0.28)
        p.drawLine(QPointF(cx, cy-r*0.7),      QPointF(cx, cy+r*0.9))
        p.drawLine(QPointF(cx-r*0.7, cy-r*0.05), QPointF(cx+r*0.7, cy-r*0.05))
        p.drawLine(QPointF(cx-r*0.45, cy+r*0.9), QPointF(cx+r*0.45, cy+r*0.9))

    def _paint_window_controls(self, p: QPainter, w: int):
        for rect, label, bg in [
            (self._cls_rect, "x", QColor(100, 22, 10)),
            (self._min_rect, "_", QColor(18, 55, 18)),
        ]:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(rect, 5, 5)
            p.setPen(QPen(BRASS_MID, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 5, 5)
            cf = QFont("Palatino Linotype", 9)
            p.setFont(cf)
            p.setPen(QPen(PARCHMENT_DIM))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _paint_candle_glow(self, p: QPainter, w: int, h: int):
        tg = QRadialGradient(w*0.42, h*0.28, min(w, h)*0.55)
        tg.setColorAt(0.0, QColor(255, 195, 85, 10 + self.flicker//2))
        tg.setColorAt(0.5, QColor(200, 130, 40, 4))
        tg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, QBrush(tg))

        vg = QRadialGradient(w*0.5, h*0.46, min(w, h)*0.42)
        vg.setColorAt(0.0,  QColor(0, 0, 0,  0))
        vg.setColorAt(0.65, QColor(0, 0, 0,  0))
        vg.setColorAt(1.0,  QColor(0, 0, 0, 80))
        p.fillRect(0, 0, w, h, QBrush(vg))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.pos()
        if self._cls_rect.contains(pos):
            self.close(); return
        if self._min_rect.contains(pos):
            self.showMinimized(); return
        if self._btn_rect.contains(pos):
            self._increment(); return
        if self._rst_rect.contains(pos):
            self._do_reset(); return
        self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        new_hover_btn = self._btn_rect.contains(pos)
        new_hover_rst = self._rst_rect.contains(pos)
        if new_hover_btn != self.hover_btn or new_hover_rst != self.hover_rst:
            self.hover_btn = new_hover_btn
            self.hover_rst = new_hover_rst
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor
                                    if (new_hover_btn or new_hover_rst)
                                    else Qt.CursorShape.ArrowCursor))
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._increment()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("The Tally Counter")
    window = TallyCounter()
    screen = app.primaryScreen().geometry()
    window.move((screen.width() - WIN_W) // 2, (screen.height() - WIN_H) // 2)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
