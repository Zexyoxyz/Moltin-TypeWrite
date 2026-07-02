# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
Graph View — visualizes the note link graph.
Uses basic QPainter for a lightweight implementation (no external deps).
Phase 2: Upgrade to Cytoscape.js via QWebEngineView for full interactivity.
"""

import math
import random
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent


class GraphCanvas(QDialog):
    """Simple force-directed graph drawn with QPainter."""

    def __init__(self, graph_data: dict[str, list[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph View — Moltin TypeWriter")
        self.resize(900, 700)
        self.setObjectName("graph_view")

        # Extract nodes and edges
        all_nodes = set(graph_data.keys())
        for targets in graph_data.values():
            all_nodes.update(targets)

        self.nodes = list(all_nodes)
        self.edges = [
            (src, tgt)
            for src, targets in graph_data.items()
            for tgt in targets
            if tgt in all_nodes
        ]

        # Assign random initial positions
        self.positions: dict[str, list[float]] = {}
        cx, cy = 450, 350
        for i, node in enumerate(self.nodes):
            angle = (2 * math.pi * i) / max(len(self.nodes), 1)
            r = min(250, 50 * math.sqrt(len(self.nodes)))
            self.positions[node] = [
                cx + r * math.cos(angle) + random.uniform(-20, 20),
                cy + r * math.sin(angle) + random.uniform(-20, 20),
            ]

        # Force-directed layout timer
        self._step = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._layout_step)
        self._timer.start(16)  # ~60 fps

        self._selected: str | None = None
        self._dragging: str | None = None
        self._drag_offset = QPointF(0, 0)

    def _layout_step(self):
        if self._step > 200:
            self._timer.stop()
            return
        self._step += 1

        n = len(self.nodes)
        if n < 2:
            return

        forces: dict[str, list[float]] = {node: [0.0, 0.0] for node in self.nodes}
        k = 80.0
        damping = 0.8

        # Repulsion
        for i, a in enumerate(self.nodes):
            for b in self.nodes[i+1:]:
                dx = self.positions[a][0] - self.positions[b][0]
                dy = self.positions[a][1] - self.positions[b][1]
                dist = max(math.sqrt(dx*dx + dy*dy), 1)
                f = k * k / dist
                fx, fy = f * dx / dist, f * dy / dist
                forces[a][0] += fx
                forces[a][1] += fy
                forces[b][0] -= fx
                forces[b][1] -= fy

        # Attraction (edges)
        for src, tgt in self.edges:
            if src not in self.positions or tgt not in self.positions:
                continue
            dx = self.positions[tgt][0] - self.positions[src][0]
            dy = self.positions[tgt][1] - self.positions[src][1]
            dist = max(math.sqrt(dx*dx + dy*dy), 1)
            f = dist * dist / k
            fx, fy = f * dx / dist, f * dy / dist
            forces[src][0] += fx
            forces[src][1] += fy
            forces[tgt][0] -= fx
            forces[tgt][1] -= fy

        # Apply
        temperature = max(0.5, 10.0 * (1 - self._step / 200))
        for node in self.nodes:
            if node == self._dragging:
                continue
            f = forces[node]
            mag = math.sqrt(f[0]**2 + f[1]**2)
            if mag > temperature:
                f[0] = f[0] / mag * temperature
                f[1] = f[1] / mag * temperature
            self.positions[node][0] = max(60, min(840, self.positions[node][0] + f[0] * damping))
            self.positions[node][1] = max(30, min(660, self.positions[node][1] + f[1] * damping))

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#0a0c10"))

        if not self.nodes:
            painter.setPen(QColor("#4a4e62"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No links found in this vault")
            return

        # Edges
        edge_pen = QPen(QColor("#2d2260"), 1.5)
        painter.setPen(edge_pen)
        for src, tgt in self.edges:
            if src in self.positions and tgt in self.positions:
                sx, sy = self.positions[src]
                tx, ty = self.positions[tgt]
                painter.drawLine(int(sx), int(sy), int(tx), int(ty))

        # Nodes
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        for node in self.nodes:
            x, y = int(self.positions[node][0]), int(self.positions[node][1])
            is_selected = node == self._selected
            r = 14 if is_selected else 10

            # Node circle
            if is_selected:
                painter.setBrush(QBrush(QColor("#9d7ef5")))
                painter.setPen(QPen(QColor("#c4abff"), 2))
            else:
                painter.setBrush(QBrush(QColor("#3d2d7a")))
                painter.setPen(QPen(QColor("#7c5cbf"), 1))

            painter.drawEllipse(x - r, y - r, r * 2, r * 2)

            # Label
            painter.setPen(QColor("#c0c3cf" if not is_selected else "#ffffff"))
            # Truncate long names
            label = node if len(node) <= 18 else node[:16] + "…"
            painter.drawText(x - 40, y + r + 14, 80, 14,
                             Qt.AlignmentFlag.AlignCenter, label)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        for node, (nx, ny) in self.positions.items():
            if abs(pos.x() - nx) < 12 and abs(pos.y() - ny) < 12:
                self._selected = node
                self._dragging = node
                self._drag_offset = QPointF(pos.x() - nx, pos.y() - ny)
                self.update()
                return
        self._selected = None
        self._dragging = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            pos = event.position()
            self.positions[self._dragging] = [
                pos.x() - self._drag_offset.x(),
                pos.y() - self._drag_offset.y(),
            ]
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = None


class GraphView(QDialog):
    """Wrapper dialog for the graph canvas."""

    def __init__(self, graph_data: dict[str, list[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph View — Moltin TypeWriter")
        self.resize(920, 740)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  ◆  Knowledge Graph")
        header.setFixedHeight(36)
        header.setStyleSheet("background:#111318; color:#9d7ef5; font-size:13px; font-weight:700; padding-left:12px;")
        layout.addWidget(header)

        # Canvas
        canvas = GraphCanvas(graph_data, self)
        layout.addWidget(canvas, 1)

        # Footer
        footer = QLabel("  Drag nodes to rearrange · Ctrl+click a node to open note")
        footer.setFixedHeight(28)
        footer.setStyleSheet("background:#0a0c10; color:#4a4e62; font-size:11px; padding-left:12px;")
        layout.addWidget(footer)
