import sys, os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem, QLabel
from PyQt5.QtGui import QPixmap, QMouseEvent, QWheelEvent, QPen, QColor, QPainter, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF

class DraggableEllipse(QGraphicsEllipseItem):
    def __init__(self, label, update_polygon_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)  # アイテムをドラッグ可能にする
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)  # アイテムを選択可能にする
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)  # アイテムの変化を検出できるようにする
        self.label = label  # この円の位置を表示するラベル
        self.update_polygon_callback = update_polygon_callback  # ポリゴン更新のコールバック
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # ドラッグ中に位置を更新
        self.updateLabelPosition()
        # ポリゴンを再描画
        self.update_polygon_callback()
    
    def updateLabelPosition(self):
        # 現在の位置をラベルに表示
        scene_position = self.sceneBoundingRect().center()
        self.label.setText(f"Circle Position: x={int(scene_position.x())}, y={int(scene_position.y())}")
        #print(f"Circle Position: x={int(scene_position.x())}, y={int(scene_position.y())}")
    
    def scene_position(self):
        scene_position = self.sceneBoundingRect().center()
        return int(scene_position.x()), int(scene_position.y())

class CustomQImageViewer2(QGraphicsView):
    def __init__(self, position_labels=None, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.circle_count = 0  # 円の数をカウントする変数
        self.position_labels = position_labels  # ラベルのリストの参照を保持
        self.ellipses = []  # 描かれた円を保持するリスト
        self.polygon_item = None  # ポリゴンを描画するアイテム
        self.zoom_factor = 1.0  # 初期のズームファクターを1.0に設定
        self.is_panning = False  # パニング状態を追跡
        self.pan_start_x = 0  # パニング開始時のX座標
        self.pan_start_y = 0  # パニング開始時のY座標
        self.position_labels = []
        for i in range(4):
            label = QLabel(f"Circle {i + 1} Position: ")
            self.position_labels.append(label)

        # 初期画像の読み込み
        image_file = os.path.join('.', 'Resource', 'preview.png')
        self.loadImage(image_file)  # 画像のパスを指定

        self.setAlignment(Qt.AlignCenter)
        self.setRenderHint(QPainter.Antialiasing)  # QPainterのAntialiasingを設定

    def loadImage(self, imagePath, circles=[]):
        pixmap = QPixmap(imagePath)
        self.scene.clear()
        self.ellipses = []
        self.circle_count = 0
        self.polygon_item = None
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.updateImageSize()
        for pos in circles:
            self.drawCircle(pos)
            self.circle_count += 1  # 円を描画した後でカウントを増やす
            if self.circle_count == 4:  # 4つの円が描かれたらポリゴンを描画
                self.drawPolygon()

    def resizeEvent(self, event):
        self.updateImageSize()
        super().resizeEvent(event)

    def updateImageSize(self):
        if self.pixmap_item is not None:
            # シーンの矩形を取得
            scene_rect = QRectF(0, 0, self.pixmap_item.pixmap().width(), self.pixmap_item.pixmap().height())
            self.resetTransform()  # 変換をリセット
            self.fitInView(scene_rect, Qt.KeepAspectRatio)  # ウィンドウにフィットさせる
            self.scale(self.zoom_factor, self.zoom_factor)  # 現在のズーム倍率を適用

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.zoom_factor *= zoom_in_factor
        else:
            self.zoom_factor *= zoom_out_factor

        # スケールをリセットして新しいズームファクターを適用
        self.updateImageSize()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            # ホイールボタンでのドラッグを開始
            self.is_panning = True
            self.setCursor(Qt.ClosedHandCursor)
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
        elif event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, DraggableEllipse):
                item.setSelected(True)
            elif self.circle_count < 4:  # 円の数が4つ未満なら描画
                scene_position = self.mapToScene(event.pos())
                self.drawCircle(scene_position)
                self.circle_count += 1  # 円を描画した後でカウントを増やす
                if self.circle_count == 4:  # 4つの円が描かれたらポリゴンを描画
                    self.drawPolygon()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_panning:
            # ホイールボタンを押しながらドラッグでシーンを移動
            delta_x = event.x() - self.pan_start_x
            delta_y = event.y() - self.pan_start_y
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta_x)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta_y)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            # ホイールボタンのドラッグを終了
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # ダブルクリックでズーム倍率を1に戻す
        self.zoom_factor = 1.0
        self.updateImageSize()

    def drawCircle(self, position: QPointF):
        # 色リストを定義
        colors = [QColor(Qt.red), QColor(Qt.green), QColor(Qt.blue), QColor(Qt.yellow)]
        
        # 円の半径を50に設定
        radius = 30
        if self.circle_count < len(self.position_labels):
            label = self.position_labels[self.circle_count]
            color = colors[self.circle_count % len(colors)]  # 色を順番に選択
            # 円を描画
            ellipse = DraggableEllipse(label, self.updatePolygon, position.x() - radius, position.y() - radius, radius * 2, radius * 2)
            ellipse.setPen(QPen(color, 2))  # 選択した色で円を描く
            ellipse.setBrush(QColor(color.red(), color.green(), color.blue(), 100))  # 半透明の塗りつぶし
            self.scene.addItem(ellipse)
            self.ellipses.append(ellipse)  # 円をリストに追加
            # 初期位置をラベルに表示
            ellipse.updateLabelPosition()

    def drawPolygon(self):
        if len(self.ellipses) == 4:
            points = [ellipse.sceneBoundingRect().center() for ellipse in self.ellipses]
            polygon = QPolygonF(points)
            
            if self.polygon_item:
                self.scene.removeItem(self.polygon_item)  # 既存のポリゴンがあれば削除
            
            self.polygon_item = QGraphicsPolygonItem(polygon)
            cyan = QColor(Qt.cyan)
            self.polygon_item.setPen(QPen(cyan, 2))  # ポリゴンの枠線を黒に設定
            self.polygon_item.setBrush(QColor(cyan.red(), cyan.green(), cyan.blue(), 50))  # 半透明の白で塗りつぶし
            self.scene.addItem(self.polygon_item)

    def updatePolygon(self):
        if self.polygon_item and len(self.ellipses) == 4:
            points = [ellipse.sceneBoundingRect().center() for ellipse in self.ellipses]
            polygon = QPolygonF(points)
            self.polygon_item.setPolygon(polygon)  # ポリゴンを更新


class SimpleBookCapture(QWidget):
    def __init__(self):
        super().__init__()
        
        # メインWindow初期設定
        self.resize(int(1920*3/4), int(1080*3/4))
        self.move(100, 100)
        self.setWindowTitle('Simple Book Capture Ver.0.0.1')

        # レイアウトを作成
        layout = QVBoxLayout()

        # 複数のラベルを作成して追加
        self.position_labels = []
        for i in range(4):
            label = QLabel(f"Circle {i + 1} Position: ")
            self.position_labels.append(label)
            layout.addWidget(label)
        
        # CustomQImageViewerインスタンスを作成してレイアウトに追加
        self.image_viewer = CustomQImageViewer(self.position_labels)
        layout.addWidget(self.image_viewer)
        
        # レイアウトをウィジェットにセット
        self.setLayout(layout)
        
        self.show()
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleBookCapture()
    sys.exit(app.exec_())
