import sys, math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QPolygonF, QCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSlider, QColorDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsPathItem,
)

W, H = 1000, 600
SHAPES = ["Persegi Panjang", "Persegi", "Lingkaran", "Oval", "Segitiga", "Trapesium"]
CURSORS = {"pen": Qt.CrossCursor, "shape": Qt.CrossCursor, "move": Qt.OpenHandCursor,
           "scale": Qt.SizeVerCursor, "rotate": Qt.SizeAllCursor,
           "fill": Qt.PointingHandCursor, "delete": Qt.ForbiddenCursor}


# tentukan garis
def make_polygon(shape, x1, y1, x2, y2):
    def oval(circle=False):
        cx, cy = (x1+x2)/2, (y1+y2)/2
        r = min(abs(x2-x1), abs(y2-y1))/2 if circle else None
        rx = ry = r if circle else (abs(x2-x1)/2, abs(y2-y1)/2)
        if not circle: rx, ry = abs(x2-x1)/2, abs(y2-y1)/2
        return [QPointF(cx + rx*math.cos(2*math.pi*i/36), cy + ry*math.sin(2*math.pi*i/36)) for i in range(36)]

    if shape == "Persegi":
        s = max(abs(x2-x1), abs(y2-y1))
        x2, y2 = x1 + s*(1 if x2>=x1 else -1), y1 + s*(1 if y2>=y1 else -1)
    pts = {
        "Persegi": [QPointF(x1,y1), QPointF(x2,y1), QPointF(x2,y2), QPointF(x1,y2)],
        "Persegi Panjang": [QPointF(x1,y1), QPointF(x2,y1), QPointF(x2,y2), QPointF(x1,y2)],
        "Segitiga": [QPointF((x1+x2)/2,y1), QPointF(x2,y2), QPointF(x1,y2)],
        "Trapesium": [QPointF(x1+(x2-x1)*.25,y1), QPointF(x1+(x2-x1)*.75,y1), QPointF(x2,y2), QPointF(x1,y2)],
        "Oval": oval(), "Lingkaran": oval(circle=True),
    }
    return QPolygonF(pts[shape])

# set kanvas  
class CanvasView(QGraphicsView):
    def __init__(self, app, scene):
        super().__init__(scene)
        self.app = app
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("white")))
        self.setMouseTracking(True)

    def mousePressEvent(self, e): self.app.on_press(self.mapToScene(e.pos())); super().mousePressEvent(e)
    def mouseMoveEvent(self, e): self.app.on_drag(self.mapToScene(e.pos())); super().mouseMoveEvent(e)
    def mouseReleaseEvent(self, e): self.app.on_release(self.mapToScene(e.pos())); super().mouseReleaseEvent(e)
    

class VectorPaintApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aplikasi Grafika ")
        self.tool = "pen"
        self.stroke_color = QColor("#000000")
        self.fill_color = None
        self.press_pos = self.drag_pos = QPointF(0, 0)
        self.active_item = self.preview_item = self.active_path = None

        self.scene = QGraphicsScene(0, 0, W, H)
        self.view = CanvasView(self, self.scene)
        self.view.setCursor(QCursor(CURSORS["pen"]))
        self._build_ui()

    def _build_ui(self):
        bar = QHBoxLayout()

        # Alat
        g = QGroupBox("Alat"); gl = QHBoxLayout(g)
        b = QPushButton("Pen"); b.clicked.connect(lambda: self.set_tool("pen")); gl.addWidget(b)
        gl.addWidget(QLabel("Kuas:"))
        self.brush_slider = QSlider(Qt.Horizontal); self.brush_slider.setRange(1, 20); self.brush_slider.setValue(3); self.brush_slider.setFixedWidth(80)
        gl.addWidget(self.brush_slider); bar.addWidget(g)

        # Bentuk
        g = QGroupBox("Bentuk"); gl = QHBoxLayout(g)
        self.shape_combo = QComboBox(); self.shape_combo.addItems(SHAPES)
        self.shape_combo.currentIndexChanged.connect(lambda _: self.set_tool("shape"))
        self.shape_combo.activated.connect(lambda _: self.set_tool("shape"))
        gl.addWidget(self.shape_combo); bar.addWidget(g)

        # Transformasi
        g = QGroupBox("Transformasi"); gl = QHBoxLayout(g)
        for label, tool in [("Geser","move"), ("Skala","scale"), ("Rotasi","rotate")]:
            b = QPushButton(label); b.clicked.connect(lambda _, t=tool: self.set_tool(t)); gl.addWidget(b)
        bar.addWidget(g)

        # Warna
        g = QGroupBox("Warna"); gl = QHBoxLayout(g)
        gl.addWidget(QLabel("Garis:"))
        self.btn_stroke = QPushButton("  "); self.btn_stroke.setStyleSheet(f"background:{self.stroke_color.name()};")
        self.btn_stroke.clicked.connect(self._pick_stroke); gl.addWidget(self.btn_stroke)
        
        gl.addWidget(QLabel("Isi:"))
        self.btn_fill = QPushButton("  "); self.btn_fill.setStyleSheet("background:#ffffff;")
        self.btn_fill.clicked.connect(self._pick_fill); gl.addWidget(self.btn_fill)
        bar.addWidget(g)

        # Edit
        g = QGroupBox("Edit"); gl = QHBoxLayout(g)
        for label, action in [("Isi Warna", lambda: self.set_tool("fill")),
                               ("Hapus Objek", lambda: self.set_tool("delete")),
                               ("Bersihkan", self.scene.clear)]:
            b = QPushButton(label); b.clicked.connect(action); gl.addWidget(b)
        bar.addWidget(g)
        bar.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(bar)
        root.addWidget(self.view)

    
    def set_tool(self, tool):
        self.tool = tool
        self.view.setCursor(QCursor(CURSORS.get(tool, Qt.CrossCursor)))

    def _pick_color(self, title, initial=None):
        c = QColorDialog.getColor(initial or QColor("#000000"), self, title)
        return c if c.isValid() else None

    def _pick_stroke(self):
        c = self._pick_color("Warna Garis", self.stroke_color)
        if c: self.stroke_color = c; self.btn_stroke.setStyleSheet(f"background:{c.name()};")

    def _pick_fill(self):
        c = self._pick_color("Warna Isi", self.fill_color)
        if c: self.fill_color = c; self.btn_fill.setStyleSheet(f"background:{c.name()};")

    def _pen(self, preview=False):
        p = QPen(self.stroke_color, self.brush_slider.value())
        if preview: p.setStyle(Qt.DashLine)
        return p

    # Tentukan Fill Color
    def _brush(self): return QBrush(self.fill_color) if self.fill_color else QBrush(Qt.black, Qt.NoBrush)

    def _item_at(self, pos): return self.scene.itemAt(pos, self.view.transform())

    # titik tengah untuk transformasi
    def _set_origin(self, item):
        if item: item.setTransformOriginPoint(item.boundingRect().center())

    def on_press(self, pos):
        self.press_pos = self.drag_pos = pos
        if self.tool == "pen":
            self.active_path = QPainterPath(pos)
            self.active_item = QGraphicsPathItem(self.active_path)
            self.active_item.setPen(self._pen())
            self.scene.addItem(self.active_item)
        elif self.tool == "shape":
            self.preview_item = QGraphicsPolygonItem()
            self.preview_item.setPen(self._pen(True)); self.preview_item.setBrush(self._brush())
            self.scene.addItem(self.preview_item)
        elif self.tool in ("move", "scale", "rotate"):
            self.active_item = self._item_at(pos); self._set_origin(self.active_item)
        elif self.tool == "fill":
            item = self._item_at(pos)
            if item and hasattr(item, "setBrush"): item.setBrush(self._brush())
        elif self.tool == "delete":
            item = self._item_at(pos)
            if item: self.scene.removeItem(item)

    def on_drag(self, pos):
        if self.tool == "pen" and self.active_item:
            self.active_path.lineTo(pos); self.active_item.setPath(self.active_path)
        elif self.tool == "shape" and self.preview_item:
            self.preview_item.setPolygon(make_polygon(self.shape_combo.currentText(), self.press_pos.x(), self.press_pos.y(), pos.x(), pos.y()))
        elif self.tool == "move" and self.active_item:
            self.active_item.moveBy(pos.x()-self.drag_pos.x(), pos.y()-self.drag_pos.y())
        elif self.tool == "scale" and self.active_item:
            f = 1.0 + (pos.x()-self.drag_pos.x())*0.005
            if f > 0: self._set_origin(self.active_item); self.active_item.setScale(self.active_item.scale()*f)
        elif self.tool == "rotate" and self.active_item:
            self._set_origin(self.active_item)
            self.active_item.setRotation(self.active_item.rotation() + (pos.x()-self.drag_pos.x())*0.4)
        self.drag_pos = pos

    def on_release(self, pos):
        if self.tool == "shape" and self.preview_item:
            poly = make_polygon(self.shape_combo.currentText(), self.press_pos.x(), self.press_pos.y(), pos.x(), pos.y())
            item = QGraphicsPolygonItem(poly); item.setPen(self._pen()); item.setBrush(self._brush())
            self.scene.addItem(item); self.scene.removeItem(self.preview_item); self.preview_item = None
        self.active_item = self.active_path = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = VectorPaintApp(); w.resize(W+40, H+120); w.show()
    sys.exit(app.exec())