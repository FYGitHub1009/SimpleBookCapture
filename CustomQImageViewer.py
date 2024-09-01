import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QGraphicsPolygonItem
from PyQt5.QtGui import QPixmap, QBrush, QColor, QPainter, QPolygonF
from PyQt5.QtCore import Qt, QPointF

class CustomQImageViewer(QGraphicsView):
    def __init__(self, image_path):
        super().__init__()

        self.image_path = image_path
        self.zoom_factor = 1.0

        # QGraphicsSceneの作成
        self.scene = QGraphicsScene()

        # 画像の読み込みと追加
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)
        self.load_image(self.image_path)

        # QGraphicsViewにシーンを設定
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        # ドラッグモードの設定
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # 最初のフィッティング
        self.fitInView(self.image_item, Qt.KeepAspectRatio)

    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        self.image_item.setPixmap(pixmap)

    def resizeEvent(self, event):
        # リサイズイベント時に画像を再フィッティング
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.scale(self.zoom_factor, self.zoom_factor)  # 現在のズームレベルを適用
        super().resizeEvent(event)

    def wheelEvent(self, event):
        # マウスホイールによる拡大縮小
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
            self.zoom_factor *= zoom_in_factor
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            self.zoom_factor *= zoom_out_factor

    def mouseDoubleClickEvent(self, event):
        # ダブルクリックでウィンドウサイズにフィット
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.zoom_factor = 1.0  # ズームレベルをリセット
        super().mouseDoubleClickEvent(event)

    
    def reset_image(self, image_path):
        self.image_path = image_path
        
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)

        pixmap = QPixmap(image_path)
        self.image_item.setPixmap(pixmap)
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.zoom_factor = 1.0
        self.scale(self.zoom_factor, self.zoom_factor)
