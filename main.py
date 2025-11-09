import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, QPointF
from math import hypot

EPS = 1e-12

def dist(a, b):
    return hypot(a[0]-b[0], a[1]-b[1])

def ray_rectangle_intersection(cx, cy, vx, vy, width, height):
    """
    射線: (x, y) = (cx, cy) + t*(vx, vy), t > 0
    回傳與矩形 [0,width] x [0,height] 最近的正 t 所對應的交點 (x,y)，若沒有交點則回 None。
    """
    ts = []
    # 與 x = 0 和 x = width 的交 (若 vx != 0)
    if abs(vx) > EPS:
        t = (0.0 - cx) / vx
        if t > EPS:
            y = cy + vy * t
            if -EPS <= y <= height + EPS:
                ts.append((t, (0.0, y)))
        t = (width - cx) / vx
        if t > EPS:
            y = cy + vy * t
            if -EPS <= y <= height + EPS:
                ts.append((t, (width, y)))
    # 與 y = 0 和 y = height 的交 (若 vy != 0)
    if abs(vy) > EPS:
        t = (0.0 - cy) / vy
        if t > EPS:
            x = cx + vx * t
            if -EPS <= x <= width + EPS:
                ts.append((t, (x, 0.0)))
        t = (height - cy) / vy
        if t > EPS:
            x = cx + vx * t
            if -EPS <= x <= width + EPS:
                ts.append((t, (x, height)))
    if not ts:
        return None
    ts.sort(key=lambda it: it[0])
    return ts[0][1]

def line_rectangle_endpoints(px, py, vx, vy, width, height):
    """
    無限直線 (x,y) = (px,py) + t*(vx,vy), t 任意實數
    回傳該直線與矩形的兩個交點 (x1,y1),(x2,y2)（若少於兩個交點，回 None）。
    """
    ts = []
    # x = 0, width
    if abs(vx) > EPS:
        t = (0.0 - px) / vx
        y = py + vy * t
        if -EPS <= y <= height + EPS:
            ts.append((t, (0.0, y)))
        t = (width - px) / vx
        y = py + vy * t
        if -EPS <= y <= height + EPS:
            ts.append((t, (width, y)))
    # y = 0, height
    if abs(vy) > EPS:
        t = (0.0 - py) / vy
        x = px + vx * t
        if -EPS <= x <= width + EPS:
            ts.append((t, (x, 0.0)))
        t = (height - py) / vy
        x = px + vx * t
        if -EPS <= x <= width + EPS:
            ts.append((t, (x, height)))
    # 移除重複點（數值穩健處理）
    uniq = []
    for t, p in ts:
        if not any(abs(p[0]-q[0])<1e-6 and abs(p[1]-q[1])<1e-6 for _, q in uniq):
            uniq.append((t, p))
    if len(uniq) < 2:
        return None
    uniq.sort(key=lambda it: it[0])
    p1 = uniq[0][1]
    p2 = uniq[-1][1]
    return (p1, p2)

class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)
        self.points = []    # list of (x,y)
        self.lines = []     # list of (x1,y1,x2,y2)

    def clear(self):
        self.points = []
        self.lines = []
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.position().x(), event.position().y()
            self.points.append((x, y))
            self.update_voronoi()
            self.update()

    def circumcenter(self, A, B, C):
        D = 2*(A[0]*(B[1]-C[1]) + B[0]*(C[1]-A[1]) + C[0]*(A[1]-B[1]))
        if abs(D) < EPS:
            return None
        Ux = ((A[0]**2 + A[1]**2)*(B[1]-C[1]) + (B[0]**2 + B[1]**2)*(C[1]-A[1]) + (C[0]**2 + C[1]**2)*(A[1]-B[1])) / D
        Uy = ((A[0]**2 + A[1]**2)*(C[0]-B[0]) + (B[0]**2 + B[1]**2)*(A[0]-C[0]) + (C[0]**2 + C[1]**2)*(B[0]-A[0])) / D
        return (Ux, Uy)

    def update_voronoi(self):
        self.lines = []
        n = len(self.points)
        if n <= 1:
            return

        W, H = float(self.width()), float(self.height())
        T = max(W, H) * 10  # 延伸倍數

        # 兩點 -> 畫中垂線
        if n == 2:
            (x1, y1), (x2, y2) = self.points
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            dx, dy = x2 - x1, y2 - y1
            vx, vy = -dy, dx
            norm = (vx*vx + vy*vy)**0.5
            if norm < EPS:
                return
            vx /= norm
            vy /= norm
            # 正負方向延伸
            self.lines.append((mx - vx*T, my - vy*T, mx + vx*T, my + vy*T))
            return

        # 三點
        A, B, C = self.points[0], self.points[1], self.points[2]
        area = A[0]*(B[1]-C[1]) + B[0]*(C[1]-A[1]) + C[0]*(A[1]-B[1])
        if abs(area) < 1e-6:
            # 共線 -> 畫兩條中垂線
            pts_sorted = sorted(self.points, key=lambda p: (p[0], p[1]))
            (x1, y1), (x2, y2), (x3, y3) = pts_sorted
            midpoints = [((x1+x2)/2, (y1+y2)/2), ((x2+x3)/2, (y2+y3)/2)]
            for (x_start, y_start), (x_end, y_end) in [( (x1, y1), (x2, y2) ), ( (x2, y2), (x3, y3) )]:
                mx, my = (x_start + x_end)/2, (y_start + y_end)/2
                dx, dy = x_end - x_start, y_end - y_start
                norm = (dx*dx + dy*dy)**0.5
                if norm < EPS:
                    continue
                # 取垂直向量
                vx, vy = -dy/norm, dx/norm
                self.lines.append((mx - vx*T, my - vy*T, mx + vx*T, my + vy*T))
            return

        # 非共線 -> 計算外心，沿中垂線方向畫射線
        center = self.circumcenter(A, B, C)
        if center is None:
            return
        cx, cy = center
        triplets = [(A, B, C), (B, C, A), (C, A, B)]
        for p1, p2, other in triplets:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            vx, vy = -dy, dx
            norm = (vx*vx + vy*vy)**0.5
            if norm < EPS:
                continue
            vx /= norm
            vy /= norm
            # 選擇方向使距離第三點更大
            candidates = [(vx, vy), (-vx, -vy)]
            best_dir = None
            best_score = None
            for cvx, cvy in candidates:
                tx, ty = cx + cvx*T, cy + cvy*T
                d_min = min(dist((tx, ty), p1), dist((tx, ty), p2))
                d_other = dist((tx, ty), other)
                score = d_other - d_min
                if best_score is None or score > best_score:
                    best_score = score
                    best_dir = (cvx, cvy)
            dirx, diry = best_dir

            # 只延伸到畫布在該方向的邊界
            if abs(dirx) > abs(diry):
                # 水平方向主導
                if dirx > 0:
                    x_end = self.width()
                else:
                    x_end = 0
                y_end = cy + diry/dirx * (x_end - cx)
            else:
                # 垂直方向主導
                if diry > 0:
                    y_end = self.height()
                else:
                    y_end = 0
                x_end = cx + dirx/diry * (y_end - cy)
            self.lines.append((cx, cy, x_end, y_end))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 畫畫布邊界
        painter.setPen(QPen(Qt.gray, 2))
        painter.drawRect(0, 0, int(self.width())-1, int(self.height())-1)

        # 畫點與座標
        for x, y in self.points:
            painter.setPen(QPen(Qt.red, 6))
            painter.drawPoint(QPointF(x, y))
            painter.setPen(QPen(Qt.darkBlue, 1))
            painter.drawText(x + 5, y - 5, f"({int(round(x))},{int(round(y))})")

        # 畫 Voronoi 線段
        painter.setPen(QPen(Qt.blue, 2))
        for x1, y1, x2, y2 in self.lines:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voronoi Diagram (≤3 points) - robust directions")
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
        """
        讀取包含座標點的文字檔，可支援兩種格式：
        1. 含註解：以 # 開頭的行會被忽略
        2. 不含註解：純座標資料

        格式範例：
        # 這是註解
        # 3 點
        120 300
        400 150
        300 500
        """

        # 開啟檔案選擇對話框
        filename, _ = QFileDialog.getOpenFileName(
            self, "選擇文字檔", "", "Text Files (*.txt);;All Files (*)"
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
                    print("讀入點數為零，檔案測試停止")
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
                        x_str, y_str = pt_line.split()[:2]
                        x, y = float(x_str), float(y_str)
                        points.append((x, y))
                        count += 1
                    except:
                        continue

                if points:
                    # 顯示本組資料點數與座標
                    print(f"本組讀入 {len(points)} 點:")
                    for p in points:
                        print(f"  {p}")

                    # 更新畫布
                    self.canvas.points = points
                    self.canvas.update_voronoi()
                    self.canvas.update()

                    # 等待使用者按鍵暫停 (簡單方法：彈出訊息)
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "提示", "按 OK 繼續讀入下一組資料")

        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "錯誤", f"讀取檔案時發生錯誤：\n{e}")

    def save_file(self, filename):
        """
        將目前畫布上的點與線段輸出至文字檔
        點格式: P x y
        線段格式: E x1 y1 x2 y2
        都是整數，按 lexical order 排序
        """
        with open(filename, "w") as f:
            # --- 1. 輸出點 ---
            pts_sorted = sorted(self.points, key=lambda p: (p[0], p[1]))
            for x, y in pts_sorted:
                f.write(f"P {int(round(x))} {int(round(y))}\n")

            # --- 2. 處理線段端點字典序 ---
            lines_fixed = []
            for x1, y1, x2, y2 in self.lines:
                # 保證 x1 <= x2 或 x1==x2 且 y1 <= y2
                if (x1 > x2) or (x1 == x2 and y1 > y2):
                    x1, y1, x2, y2 = x2, y2, x1, y1
                lines_fixed.append((x1, y1, x2, y2))

            # --- 3. 排序線段 ---
            lines_sorted = sorted(lines_fixed, key=lambda e: (e[0], e[1], e[2], e[3]))

            # --- 4. 輸出線段 ---
            for x1, y1, x2, y2 in lines_sorted:
                f.write(f"E {int(round(x1))} {int(round(y1))} {int(round(x2))} {int(round(y2))}\n")

    def load_output_file(self):
        """
        讀取輸出文字檔 (P x y / E x1 y1 x2 y2)
        並將畫布更新，線段端點可超出畫布範圍
        """
        filename, _ = QFileDialog.getOpenFileName(
            self, "選擇輸出文字檔", "", "Text Files (*.txt);;All Files (*)"
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
                parts = s.split()
                if parts[0] == "P" and len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        points.append((x, y))
                    except:
                        continue
                elif parts[0] == "E" and len(parts) >= 5:
                    try:
                        x1 = float(parts[1])
                        y1 = float(parts[2])
                        x2 = float(parts[3])
                        y2 = float(parts[4])
                        # 保證端點字典序 (x1≤x2 或 x1=x2, y1≤y2)
                        if (x1 > x2) or (x1 == x2 and y1 > y2):
                            x1, y1, x2, y2 = x2, y2, x1, y1
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
