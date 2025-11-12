import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, QPointF
from math import hypot

EPS = 1e-12

# 距離函數 (hypotenuse)
def dist(a, b):
    return hypot(a[0]-b[0], a[1]-b[1])

# 畫布 
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)   
        self.points = []    # list of (x, y)
        self.lines = []     # list of (x1, y1, x2, y2)

    def clear(self):
        self.points = []
        self.lines = []
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 限制最多三個點 (初測)
            if len(self.points) >= 3:
                QMessageBox.warning(
                    self, 
                    "點擊超過限制", 
                    "目前僅支援 3 個點以內的 Voronoi diagram。\n請先清除畫布再繼續。"
                )
                return  # 不新增點，直接返回
            
            # 若未超過三點，正常新增 
            x, y = event.position().x(), event.position().y()   # 從 QPointF 物件中取資料
            self.points.append((x, y))
            self.update_voronoi()
            self.update()

    # 外心函數 
    def circumcenter(self):
        A, B, C = self.points[0], self.points[1], self.points[2]
        D = 2*(A[0]*(B[1]-C[1]) + B[0]*(C[1]-A[1]) + C[0]*(A[1]-B[1]))  # D = 平行四邊形面積
        # 認定為共線 -> 無外心
        if abs(D) < EPS:
            return None
        # 非共線 -> 計算外心 x, y 座標: Ux, Uy
        Ux = ((A[0]**2 + A[1]**2)*(B[1]-C[1]) + (B[0]**2 + B[1]**2)*(C[1]-A[1]) + (C[0]**2 + C[1]**2)*(A[1]-B[1])) / D
        Uy = ((A[0]**2 + A[1]**2)*(C[0]-B[0]) + (B[0]**2 + B[1]**2)*(A[0]-C[0]) + (C[0]**2 + C[1]**2)*(B[0]-A[0])) / D
        return (Ux, Uy)

    # voronoi函數 (計算分割線段)
    def update_voronoi(self):
        self.lines = []
        n = len(self.points)

        # 一點 -> 無反應
        if n <= 1:
            return

        T = 600 * 2  # 延伸倍數

        # 兩點 -> 畫中垂線 (從兩點中點以負斜率之倒數雙向延伸)
        if n == 2:
            (x1, y1), (x2, y2) = self.points
            # mx, my: 中點
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            # dx, dy: x軸和y軸的距離 (從點一往點二)
            dx, dy = x2 - x1, y2 - y1
            # 單位化
            norm = (dx*dx + dy*dy)**0.5
            if norm < EPS:
                return
            # vx, vy: 法向量(逆時針)
            vx, vy = -dy/norm, dx/norm
            # 正負方向延伸
            self.lines.append((mx - vx*T, my - vy*T, mx + vx*T, my + vy*T))
            return

        # 三點 (分兩種情況)
        center = self.circumcenter()
        if center is None:
            # 共線 -> 畫兩條中垂線
            # 排序
            pts_sorted = sorted(self.points, key=lambda p: (p[0], p[1])) 
            (x1, y1), (x2, y2), (x3, y3) = pts_sorted
            for (x_start, y_start), (x_end, y_end) in [( (x1, y1), (x2, y2) ), ( (x2, y2), (x3, y3) )]:
                mx, my = (x_start + x_end)/2.0, (y_start + y_end)/2.0
                dx, dy = x_end - x_start, y_end - y_start
                norm = (dx*dx + dy*dy)**0.5
                if norm < EPS:
                    continue
                vx, vy = -dy/norm, dx/norm
                self.lines.append((mx - vx*T, my - vy*T, mx + vx*T, my + vy*T))
            return

        # 非共線 -> 計算外心，沿中垂線方向畫射線
        cx, cy = center
        A, B, C = self.points[0], self.points[1], self.points[2]
        triplets = [(A, B, C), (B, C, A), (C, A, B)]
        for p1, p2, other in triplets:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            norm = (dx*dx + dy*dy)**0.5
            if norm < EPS:
                continue
            vx, vy = -dy/norm, dx/norm
            # 選擇方向 (距離第三點更遠)
            candidates = [(vx, vy), (-vx, -vy)]
            best_dir = None
            best_score = None
            # 兩個方向各自計算，挑選遠的
            for cvx, cvy in candidates:
                tx, ty = cx + cvx*T, cy + cvy*T
                # 離A, B近
                d_min = min(dist((tx, ty), p1), dist((tx, ty), p2)) 
                # 離C遠
                d_other = dist((tx, ty), other)
                # 綜合考慮
                score = d_other - d_min
                if best_score is None or score > best_score:
                    best_score = score
                    best_dir = (cvx, cvy)
            dirx, diry = best_dir

            # 延伸到畫布在該方向的邊界
            if abs(dirx) > abs(diry):
                # 主要水平
                if dirx > 0:
                    x_end = self.width()
                else:
                    x_end = 0
                y_end = cy + diry/dirx * (x_end - cx)
            else:
                # 主要垂直
                if diry > 0:
                    y_end = self.height()
                else:
                    y_end = 0
                x_end = cx + dirx/diry * (y_end - cy)
            self.lines.append((cx, cy, x_end, y_end))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)    # 平滑

        # 畫畫布邊界
        painter.setPen(QPen(Qt.gray, 2))
        painter.drawRect(0, 0, int(self.width()), int(self.height()))

        # 畫點與座標
        for x, y in self.points:
            painter.setPen(QPen(Qt.white, 4))
            painter.drawPoint(QPointF(x, y))
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(x + 5, y - 5, f"({int(round(x))},{int(round(y))})")

        # 畫 Voronoi 線段
        painter.setPen(QPen(Qt.blue, 2))
        for x1, y1, x2, y2 in self.lines:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voronoi Diagram (≤3 points)")
        self.canvas = Canvas()

        btn_clear = QPushButton("清空畫布")
        btn_clear.clicked.connect(self.canvas.clear)
        btn_load = QPushButton("讀取文字檔")
        btn_load.clicked.connect(self.load_file)
        btn_save = QPushButton("輸出文字檔")
        btn_save.clicked.connect(self.save_file)
        btn_load_out = QPushButton("讀取輸出檔")
        btn_load_out.clicked.connect(self.load_output_file)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(btn_clear)
        layout.addWidget(btn_load)
        layout.addWidget(btn_save)
        layout.addWidget(btn_load_out)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_file(self):
        # 開啟檔案選擇對話框
        filename, _ = QFileDialog.getOpenFileName(
            self, "選擇文字檔", "", "Text Files (*.txt)"
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()

            idx = 0
            while idx < len(lines):
                line = lines[idx].strip()
                idx += 1

                # 跳過空行與註解
                if not line or line.startswith("#"):
                    continue

                # 解析 n
                try:
                    n = int(line)
                except ValueError:
                    continue

                # 若 n = 0，停止讀檔
                if n == 0:
                    QMessageBox.information(self, "提示", "檔案測試結束")
                    break

                # 讀取 n 個座標點
                points = []
                count = 0
                while count < n and idx < len(lines):
                    pt_line = lines[idx].strip()
                    idx += 1
                    if not pt_line or pt_line.startswith("#"):
                        continue
                    try:
                        x_str, y_str = pt_line.split()
                        x, y = float(x_str), float(y_str)
                        points.append((x, y))
                        count += 1
                    except:
                        continue

                # 若超過 3 點就警告並跳過
                if len(points) > 3:
                    QMessageBox.warning(
                        self,
                        "測資超出限制",
                        f"目前僅支援 3 個點以內的 Voronoi diagram。\n"
                        f"本組資料有 {len(points)} 個點，將略過此組資料。"
                    )
                    continue  # 不更新畫布    

                if points:
                    # 更新畫布
                    self.canvas.points = points
                    self.canvas.update_voronoi()
                    self.canvas.update()

                    # 等待使用者按鍵暫停              
                    QMessageBox.information(self, "提示", "按 OK 繼續下一組資料")

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"讀取檔案時發生錯誤：\n{e}")

    def save_file(self):
        # 讓使用者選擇要儲存的檔案名稱
        filename, _ = QFileDialog.getSaveFileName(
            self, "儲存輸出檔案", "", "Text Files (*.txt)"
        )

        # 若使用者取消就直接離開
        if not filename:
            return

        try:
            # 從畫布取得點與線
            pts = self.canvas.points
            lines = self.canvas.lines

            with open(filename, "w", encoding="utf-8") as f:
                # 點排序並輸出 
                pts_sorted = sorted(pts, key=lambda p: (p[0], p[1]))
                for x, y in pts_sorted:
                    f.write(f"P {int(round(x))} {int(round(y))}\n")

                # 線段則排序後輸出 
                if lines:
                    lines_fixed = []
                    for x1, y1, x2, y2 in lines:
                        # 讓每條線的端點順序一致 (lexical order)
                        if (x1 > x2) or (x1 == x2 and y1 > y2):
                            x1, y1, x2, y2 = x2, y2, x1, y1
                        lines_fixed.append((x1, y1, x2, y2))

                    lines_sorted = sorted(lines_fixed, key=lambda e: (e[0], e[1], e[2], e[3]))
                    for x1, y1, x2, y2 in lines_sorted:
                        f.write(f"E {int(round(x1))} {int(round(y1))} {int(round(x2))} {int(round(y2))}\n")

            QMessageBox.information(self, "成功", f"已儲存至 {filename}")

        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"無法儲存檔案：{e}")

    def load_output_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "選擇輸出文字檔", "", "Text Files (*.txt)"
        )
        if not filename:
            return

        points = []
        lines = []

        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                types = s.split()
                if types[0] == "P" and len(types) == 3:
                    try:
                        x = float(types[1])
                        y = float(types[2])
                        points.append((x, y))
                    except:
                        continue
                elif types[0] == "E" and len(types) == 5:
                    try:
                        x1 = float(types[1])
                        y1 = float(types[2])
                        x2 = float(types[3])
                        y2 = float(types[4])
                        lines.append((x1, y1, x2, y2))
                    except:
                        continue

        # 更新畫布
        self.canvas.points = points
        self.canvas.lines = lines
        self.canvas.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())