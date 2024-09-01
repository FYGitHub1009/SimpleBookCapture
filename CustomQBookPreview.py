import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QGraphicsPolygonItem
from PyQt5.QtGui import QPixmap, QBrush, QColor, QPainter, QPolygonF
from PyQt5.QtCore import Qt, QPointF

class CustomQBookPreview(QGraphicsView):
    def __init__(self, image_paths):
        super().__init__()
        
        # 左右綴じフラグ
        self.binder = 1.0

        self.image_paths = image_paths
        self.current_image_index = 0
        self.zoom_factor = 1.0

        # QGraphicsSceneの作成
        self.scene = QGraphicsScene()

        # 画像の読み込みと追加
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)
        self.load_image(self.image_paths[self.current_image_index])

        # QGraphicsViewにシーンを設定
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        # ドラッグモードの設定
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # ウィンドウの設定
        self.setWindowTitle("Image with Arrow Overlay")
        self.resize(800, 600)  # 初期ウィンドウサイズを設定

        # 最初のフィッティング
        self.fitInView(self.image_item, Qt.KeepAspectRatio)

    def load_image(self, image_path):
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)

        pixmap = QPixmap(image_path)
        self.image_item.setPixmap(pixmap)
        self.update_arrow_positions()

    def update_arrow_positions(self):
        arrow_height = self.image_item.pixmap().height() / 4
        arrow_width = arrow_height / 2

        # 左矢印の作成と追加
        left_arrow_points = [
            QPointF(0, arrow_height / 2),
            QPointF(arrow_width / 2, 0),
            QPointF(arrow_width / 2, arrow_height / 4),
            QPointF(arrow_width, arrow_height / 4),
            QPointF(arrow_width, 3 * arrow_height / 4),
            QPointF(arrow_width / 2, 3 * arrow_height / 4),
            QPointF(arrow_width / 2, arrow_height),
        ]
        left_arrow_polygon = QPolygonF(left_arrow_points)
        #if hasattr(self, 'left_arrow_item'):
        #    self.scene.removeItem(self.left_arrow_item)
        self.left_arrow_item = QGraphicsPolygonItem(left_arrow_polygon)
        self.left_arrow_item.setBrush(QBrush(QColor(255, 0, 0, 100)))  # 半透明の赤色
        self.left_arrow_item.setPos(0, (self.image_item.pixmap().height() - arrow_height) / 2)
        self.left_arrow_item.setAcceptHoverEvents(True)
        self.left_arrow_item.setFlag(QGraphicsPolygonItem.ItemIsSelectable)
        self.left_arrow_item.setVisible(False)  # 初期状態で非表示
        self.scene.addItem(self.left_arrow_item)

        # 右矢印の作成と追加
        right_arrow_points = [
            QPointF(arrow_width, arrow_height / 2),
            QPointF(arrow_width / 2, 0),
            QPointF(arrow_width / 2, arrow_height / 4),
            QPointF(0, arrow_height / 4),
            QPointF(0, 3 * arrow_height / 4),
            QPointF(arrow_width / 2, 3 * arrow_height / 4),
            QPointF(arrow_width / 2, arrow_height),
        ]
        right_arrow_polygon = QPolygonF(right_arrow_points)
        #if hasattr(self, 'right_arrow_item'):
        #    self.scene.removeItem(self.right_arrow_item)
        self.right_arrow_item = QGraphicsPolygonItem(right_arrow_polygon)
        self.right_arrow_item.setBrush(QBrush(QColor(0, 255, 0, 100)))  # 半透明の緑色
        self.right_arrow_item.setPos(self.image_item.pixmap().width() - arrow_width, (self.image_item.pixmap().height() - arrow_height) / 2)
        self.right_arrow_item.setAcceptHoverEvents(True)
        self.right_arrow_item.setFlag(QGraphicsPolygonItem.ItemIsSelectable)
        self.right_arrow_item.setVisible(False)  # 初期状態で非表示
        self.scene.addItem(self.right_arrow_item)

    def resizeEvent(self, event):
        # リサイズイベント時に画像を再フィッティング
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.scale(self.zoom_factor, self.zoom_factor)  # 現在のズームレベルを適用
        self.update_arrow_positions()  # 矢印の位置を更新
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        # マウスの位置をシーン座標に変換
        pos = self.mapToScene(event.pos())

        # シーンの幅を取得
        scene_width = self.scene.width()

        # 左端と右端の境界
        left_boundary = scene_width * 0.25
        right_boundary = scene_width * 0.75

        # 矢印の表示/非表示を切り替え
        if pos.x() < left_boundary:
            self.left_arrow_item.setVisible(True)
        else:
            self.left_arrow_item.setVisible(False)

        if pos.x() > right_boundary:
            self.right_arrow_item.setVisible(True)
        else:
            self.right_arrow_item.setVisible(False)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        # マウスの位置をシーン座標に変換
        pos = self.mapToScene(event.pos())

        # 左矢印のクリック
        if self.left_arrow_item.isUnderMouse():
            self.current_image_index = (self.current_image_index + int(-1*self.binder)) % len(self.image_paths)
            self.load_image(self.image_paths[self.current_image_index])
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.scale(self.zoom_factor, self.zoom_factor)  # 現在のズームレベルを適用

        # 右矢印のクリック
        if self.right_arrow_item.isUnderMouse():
            self.current_image_index = (self.current_image_index + int(1*self.binder)) % len(self.image_paths)
            self.load_image(self.image_paths[self.current_image_index])
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.scale(self.zoom_factor, self.zoom_factor)  # 現在のズームレベルを適用

        super().mousePressEvent(event)

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

    def enterEvent(self, event):
        self.setMouseTracking(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.left_arrow_item.setVisible(False)
        self.right_arrow_item.setVisible(False)
        self.setMouseTracking(False)
        super().leaveEvent(event)

    def reset(self, image_paths):
        self.image_paths = image_paths
        self.current_image_index = 0
        self.zoom_factor = 1.0 
        self.load_image(self.image_paths[self.current_image_index])
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.scale(self.zoom_factor, self.zoom_factor) 
