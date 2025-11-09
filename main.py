import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QLabel
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, QPointF

# ========== 繪圖區類別 ==========
class DrawingArea(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(600, 600)
        self.setMouseTracking(True)
        self.points = []  # 儲存點座標
        self.current_pos = None

    def mouseMoveEvent(self, event):
        self.current_pos = event.pos()
        self.update()

    def mousePressEvent(self, event):
        # 滑鼠點擊：新增一個點
        if event.button() == Qt.LeftButton:
            self.points.append(event.pos())
            self.update()  # 觸發重繪

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 輔助十字線
        if hasattr(self, "current_pos"):
            pen = QPen(Qt.gray)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(self.current_pos.x(), 0, self.current_pos.x(), self.height())
            painter.drawLine(0, self.current_pos.y(), self.width(), self.current_pos.y())

        # 畫點 
        pen = QPen(Qt.red)
        pen.setWidth(8)
        painter.setPen(pen)
        for p in self.points:
            painter.drawPoint(p)

        # 顯示座標
        painter.setPen(Qt.darkBlue)
        for p in self.points:
            painter.drawText(p.x() + 5, p.y() - 5, f"({p.x():.0f}, {p.y():.0f})")

    def clear_points(self):
        # 清除畫布
        self.points.clear()
        self.current_pos = None
        self.update()

# ========== 主視窗類別 ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voronoi 初測版")
        self.setGeometry(100, 100, 650, 700)

        self.drawing_area = DrawingArea()
        self.label = QLabel("左鍵點擊畫點，按下「清除畫布」可重新開始。")

        # 清除按鈕
        self.clear_button = QPushButton("清除畫布")
        self.clear_button.clicked.connect(self.drawing_area.clear_points)

        # 版面配置
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.drawing_area)
        layout.addWidget(self.clear_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

# ========== 主程式入口 ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
