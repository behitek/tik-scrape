from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QLabel, QApplication

from ui.theme import PALETTE


class FullSizePopup(QLabel):
    def __init__(self, pixmap: QPixmap):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        scaled = pixmap.scaled(600, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
        self.setFixedSize(scaled.size())
        self.setStyleSheet(f"border: 2px solid {PALETTE['border_lt']}; background: {PALETTE['bg_deep']};")


class ImageThumb(QLabel):
    THUMB_SIZE = 120
    BORDER_SELECTED = PALETTE["teal"]
    BORDER_NORMAL = PALETTE["border_lt"]

    def __init__(self, thumb_pixmap: QPixmap, full_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.thumb_pixmap = thumb_pixmap
        self.full_pixmap = full_pixmap
        self.selected = False
        self._popup: FullSizePopup | None = None

        self.setFixedSize(self.THUMB_SIZE + 6, self.THUMB_SIZE + 6)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()

    def _refresh(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw thumbnail centered
        x = (self.width() - self.thumb_pixmap.width()) // 2
        y = (self.height() - self.thumb_pixmap.height()) // 2
        painter.drawPixmap(x, y, self.thumb_pixmap)

        # Selection overlay
        teal = QColor(PALETTE["teal"])
        if self.selected:
            overlay = QColor(teal)
            overlay.setAlpha(50)
            painter.fillRect(0, 0, self.width(), self.height(), overlay)
            pen = QPen(teal, 3)
        else:
            pen = QPen(QColor(self.BORDER_NORMAL), 1)

        painter.setPen(pen)
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)

        # Checkmark badge for selected
        if self.selected:
            badge = QColor(teal)
            badge.setAlpha(210)
            painter.setBrush(badge)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.width() - 18, 3, 14, 14)
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawLine(self.width() - 14, 10, self.width() - 11, 13)
            painter.drawLine(self.width() - 11, 13, self.width() - 6, 7)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected = not self.selected
            self._refresh()
            # notify parent row to update count
            parent = self.parent()
            while parent:
                if hasattr(parent, "on_selection_changed"):
                    parent.on_selection_changed()
                    break
                parent = parent.parent()

    def enterEvent(self, event):
        self._show_popup()

    def leaveEvent(self, event):
        self._hide_popup()

    def _show_popup(self):
        self._hide_popup()
        self._popup = FullSizePopup(self.full_pixmap)
        cursor_pos = self.mapToGlobal(QPoint(self.width() + 4, 0))
        screen = QApplication.primaryScreen().availableGeometry()
        px = cursor_pos.x()
        py = cursor_pos.y()
        if px + self._popup.width() > screen.right():
            px = cursor_pos.x() - self.width() - self._popup.width() - 4
        if py + self._popup.height() > screen.bottom():
            py = screen.bottom() - self._popup.height()
        self._popup.move(px, py)
        self._popup.show()

    def _hide_popup(self):
        if self._popup:
            self._popup.close()
            self._popup = None
