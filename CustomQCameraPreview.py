import sys
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMainWindow
from PyQt5.QtGui import QImage, QPixmap, QTransform
from PyQt5.QtCore import QTimer, Qt, QPoint
import numpy as np
from picamera2 import Picamera2

#def post_callback(request):
#    # Read the metadata we get back from every request
#    metadata = request.get_metadata()
#    # Put Awb to the end, as they only flash up sometimes
#    sorted_metadata = sorted(metadata.items(), key=lambda x: x[0] if "Awb" not in x[0] else f"Z{x[0]}")
#    # And print everything nicely
#    pretty_metadata = []
#    for k, v in sorted_metadata:
#        row = ""
#        try:
#            iter(v)
#            if k == "ColourCorrectionMatrix":
#                matrix = np.around(np.reshape(v, (-1, 3)), decimals=2)
#                row = f"{k}:\n{matrix}"
#            elif k == "Bcm2835StatsOutput":
#                continue
#            else:
#                row_data = [f'{x:.2f}' if type(x) is float else f'{x}' for x in v]
#                row = f"{k}: ({', '.join(row_data)})"
#        except TypeError:
#            if type(v) is float:
#                row = f"{k}: {v:.2f}"
#            else:
#                row = f"{k}: {v}"
#        pretty_metadata.append(row)
#    print('\n'.join(pretty_metadata))

class CustomQCameraPreview(QGraphicsView):
    def __init__(self, camera):
        super().__init__()
        
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        self.camera = camera
        self.zoom_factor = 1.0  # 初期ズームレベル
        self.max_zoom = 4.0  # 最大ズームレベル
        self.min_zoom = 1.0  # 最小ズームレベル
        
        self.scaler_crop_x = 0
        self.scaler_crop_y = 0
        self.drag_start_position = None
        self.rotation_angle = 0
        
        # メイン側で呼び出し
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ミリ秒ごとにフレームを更新

    def update_frame(self):
        frame = self.camera.capture_array()
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # Rotate the pixmap
        transform = QTransform().rotate(self.rotation_angle)
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        
        self.pixmap_item.setPixmap(rotated_pixmap)
        
        # fitInViewを使用して画像をビューのサイズに合わせる
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        
        # 現在のズーム倍率を出力
        #print(f"Zoom factor: {self.zoom_factor}")
    
    def resizeEvent(self, event):
        # ウィンドウサイズが変更されたときにもfitInViewを呼び出す
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        super().resizeEvent(event)

    def wheelEvent(self, event):
        # マウスホイールイベントを処理してズームレベルを変更
        if event.angleDelta().y() > 0:
            self.zoom_factor = min(self.zoom_factor * 1.1, self.max_zoom)  # ズームイン
        else:
            self.zoom_factor = max(self.zoom_factor / 1.1, self.min_zoom)  # ズームアウト
        
        # ScalerCropを更新してズームを適用
        self.update_scaler_crop()
        self.update_frame()  # フレームを更新してズームを反映

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.drag_start_position is not None:
            delta = event.pos() - self.drag_start_position
            dx, dy = self.apply_rotation_transform(delta.x(), delta.y())
            self.move_scaler_crop(-dx, -dy)  # ドラッグ方向を反転
            self.drag_start_position = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = None

    def mouseDoubleClickEvent(self, event):
        # ダブルクリックで画像を等倍に戻し、ScalerCropをリセット
        _, (_, _, sensor_width, sensor_height), _ = self.camera.camera_controls['ScalerCrop']
        self.camera.set_controls({"ScalerCrop": (0, 0, sensor_width, sensor_height)})
        self.zoom_factor = 1.0
        self.reset_view()

    def apply_rotation_transform(self, dx, dy):
        # 回転角度に応じてドラッグ方向を変換
        angle = self.rotation_angle % 360
        if angle == 90:
            return dy, -dx
        elif angle == 180:
            return -dx, -dy
        elif angle == 270:
            return -dy, dx
        else:  # 0度または360度
            return dx, dy

    def move_scaler_crop(self, dx, dy):
        _, (_, _, sensor_width, sensor_height), _ = self.camera.camera_controls['ScalerCrop']
        crop_width = int(sensor_width / self.zoom_factor)
        crop_height = int(sensor_height / self.zoom_factor)
        
        self.scaler_crop_x = max(0, min(self.scaler_crop_x + dx, sensor_width - crop_width))
        self.scaler_crop_y = max(0, min(self.scaler_crop_y + dy, sensor_height - crop_height))
        
        self.update_scaler_crop()

    def update_scaler_crop(self):
        _, (_, _, sensor_width, sensor_height), _ = self.camera.camera_controls['ScalerCrop']
        crop_width = int(sensor_width / self.zoom_factor)
        crop_height = int(sensor_height / self.zoom_factor)
        
        crop_x = self.scaler_crop_x
        crop_y = self.scaler_crop_y
        
        self.camera.set_controls({"ScalerCrop": (crop_x, crop_y, crop_width, crop_height)})
    
    def rotate_image(self, rotation_angle):
        # 画像を時計回りに90度回転
        #self.rotation_angle = (self.rotation_angle + 90) % 360
        self.rotation_angle = rotation_angle % 360
        
        # 画像を等倍に戻し、ScalerCropをリセット
        _, (_, _, sensor_width, sensor_height), _ = self.camera.camera_controls['ScalerCrop']
        self.camera.set_controls({"ScalerCrop": (0, 0, sensor_width, sensor_height)})
        self.zoom_factor = 1.0
        
        # シーンをクリアして再設定
        self.reset_view()

    def reset_view(self):
        self.scene.clear()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.update_frame()
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

#class MainWindow(QMainWindow):
#    def __init__(self, camera):
#        super().__init__()
#        
#        self.setWindowTitle("Camera Preview")
#        self.setMinimumSize(960, 540)
#        
#        self.view = CameraPreview(camera)
#        self.setCentralWidget(self.view)
#
#if __name__ == "__main__":
#    app = QApplication(sys.argv)
#    
#    # PiCamera2の初期化
#    camera = Picamera2()
#    camera_config = camera.create_preview_configuration(
#        main={"format": "BGR888", 'size': (1920, 1080)},
#        raw={'format': 'SRGGB10_CSI2P', 'size': (4608, 2592)}
#    )
#    camera.configure(camera_config)
#    
#    # post_callbackを設定
#    camera.post_callback = post_callback
#    
#    camera.start()
#    
#    # MainWindowにPiCamera2のインスタンスを渡す
#    main_window = MainWindow(camera)
#    main_window.show()
#    
#    sys.exit(app.exec_())


