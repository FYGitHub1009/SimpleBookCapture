import os, glob
import json
from datetime import datetime
import numpy as np
import cv2

# Qt関係
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
from PyQt5.QtWidgets import QTabWidget, QFrame
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout
from PyQt5.QtWidgets import QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtGui import QImage, QPixmap, QTransform
from PyQt5.QtCore import QPointF
# カスタムWidget
from CustomQWidgets import logControlSlider, controlSlider, QCircleLabel
from CustomQCameraPreview import CustomQCameraPreview
from CustomQImageViewer2 import CustomQImageViewer2

# PiCamera2関係
from picamera2 import Picamera2, Preview
from picamera2.previews.qt import QGlPicamera2
from libcamera import Transform

# PiCamera2グローバル変数
from GlobalVariables import picam2s, piconfigs, pimetadatas, configfiles

# 基本設定タブ
class BasicSettingTab(QTabWidget):
    # 初期化
    def __init__(self, camid):        
        # 初期化
        super().__init__()
        
        # カメラ番号
        self.camid = camid
        
        # タブページ
        basicTab = QWidget()
        self.addTab(basicTab, "基本設定")
        
        # フォームレイアウト
        formLayout = QFormLayout()
        basicTab.setLayout(formLayout)
        
        # ファイル命名規則のテキスト入力枠
        self.nameRule = QComboBox()
        self.nameRule.addItems(["年月日_時分秒_left", "年月日_時分秒_right"])
        self.nameRule.setCurrentIndex(camid)
        formLayout.addRow("ファイル名規則", self.nameRule)   
        
        # 保存形式のコンボボックス
        self.filetype = QComboBox()
        self.filetype.addItems(["jpg", "png"])
        formLayout.addRow("保存形式", self.filetype)
        
        # RAWとMeta保存のチェックボックス
        chkRowMeta = QCheckBox()
        chkRowMeta.setChecked(False)
        formLayout.addRow("RawとMetaの保存", chkRowMeta)
        chkRowMeta.setEnabled(False)

        # センサモードのコンボボックス
        self.sensorFormat = QComboBox()
        #self.sensorFormat.addItem("Default")
        self.sensorFormat.addItems([f'{x["format"].format} {x["size"]}' for x in picam2s[camid].sensor_modes])
        # 最大の解像度(4608x2592)に設定
        # プレビューとキャプチャの画角違い防止のため固定
        self.sensorFormat.setCurrentIndex(2)
        self.sensorFormat.setEnabled(False)
        formLayout.addRow("センサーモード", self.sensorFormat)
        
        # 画像幅のスピンボックス
        self.imageWidth = QSpinBox()
        self.imageWidth.setMaximum(self.current_sensor_mode["size"][0])
        self.imageWidth.setValue(self.current_sensor_mode["size"][0])
        
        # 画像高さのスピンボックス
        self.imageHeight = QSpinBox()
        self.imageHeight.setMaximum(self.current_sensor_mode["size"][1])
        self.imageHeight.setValue(self.current_sensor_mode["size"][1])
        
        # 画像サイズ反映ボタン
        self.resButton = QPushButton("反映")
        self.resButton.setEnabled(False)
        # 画像サイズ反映ボタンクリック時の動作
        self.resButton.clicked.connect(self.on_resButton_clicked)
        
        # 画像の縦横サイズを変更時は反映ボタンを有効化
        self.imageWidth.valueChanged.connect(lambda: self.resButton.setEnabled(True))
        self.imageHeight.valueChanged.connect(lambda: self.resButton.setEnabled(True))
        
        # 画像サイズ
        resolution = QWidget()
        resHLayout = QHBoxLayout()
        resolution.setLayout(resHLayout)
        resHLayout.addWidget(self.imageWidth)
        resHLayout.addWidget(QLabel("x"), alignment=Qt.AlignHCenter)
        resHLayout.addWidget(self.imageHeight)
        resHLayout.addWidget(QLabel(" "), alignment=Qt.AlignHCenter)
        resHLayout.addWidget(self.resButton)
        formLayout.addRow("画像サイズ", resolution)
        
        # 回転角度
        self.rotAngles = [0, 90, 180, 270]
        self.rotIndex = 0
        self.rotLabel = QLabel(f"{self.rotAngles[self.rotIndex]:3d}度")
        
        # 回転ボタン
        self.rotButton = QPushButton("")
        self.rotButton.setIcon(QIcon("./Resource/rotate.png"))
        # 回転ボタンクリック時の動作
        self.rotButton.clicked.connect(self.on_rotButton_clicked)

        # 回転変換
        rotation = QWidget()
        rotHLayout = QHBoxLayout()
        rotation.setLayout(rotHLayout)
        rotHLayout.addWidget(self.rotLabel, alignment=Qt.AlignHCenter)
        rotHLayout.addWidget(self.rotButton, alignment=Qt.AlignLeft)
        formLayout.addRow("回転変換", rotation)


    # カメラコンフィグ更新
    def update_basic_config(self):
        # カメラ停止
        picam2s[self.camid].stop()
        
        # 静止画コンフィグ更新
        piconfigs[self.camid]["still"]['main']['size'] = (self.imageWidth.value(), self.imageHeight.value())
        piconfigs[self.camid]["still"]['raw'] = self.current_sensor_mode
        
        # プレビューコンフィグ更新
        piconfigs[self.camid]["preview"]['main']['format'] = "BGR888"
        preview_width = self.imageWidth.value() if self.imageWidth.value() < 2000 else 2000
        preview_height = int(preview_width* (self.imageHeight.value() / self.imageWidth.value()))
        preview_height = preview_height if preview_height%2==0 else preview_height-1
        piconfigs[self.camid]["preview"]['main']['size'] = (preview_width, preview_height)
        piconfigs[self.camid]["preview"]['raw'] = self.current_sensor_mode
        
        # カメラコンフィグ設定
        picam2s[self.camid].configure(piconfigs[self.camid]["preview"])  
              
        # カメラ開始
        picam2s[self.camid].start()
    
    
    # 画像サイズの反映ボタンをクリック時の動作
    def on_resButton_clicked(self):
        # 静止画用コンフィグの画像サイズ更新
        piconfigs[self.camid]["still"]['main']['size'] = (self.imageWidth.value(), self.imageHeight.value())
        
        # プレビュー用コンフィグの画像サイズ更新
        piconfigs[self.camid]["preview"]['main']['format'] = "BGR888"
        preview_width = self.imageWidth.value() if self.imageWidth.value() < 2000 else 2000
        preview_height = int(preview_width* (self.imageHeight.value() / self.imageWidth.value()))
        preview_height = preview_height if preview_height%2==0 else preview_height-1
        piconfigs[self.camid]["preview"]['main']['size'] = (preview_width, preview_height)
        
        # カメラ停止
        picam2s[self.camid].stop()
        # プレビューコンフィグ更新
        picam2s[self.camid].configure(piconfigs[self.camid]["preview"])        
        # カメラ開始
        picam2s[self.camid].start()
        
        # 反映ボタン無効化
        self.resButton.setEnabled(False)
    
    
    # 回転ボタンをクリック時の動作
    def on_rotButton_clicked(self):
        self.rotIndex = (self.rotIndex + 1) % len(self.rotAngles)
        rotate_angle = self.rotAngles[self.rotIndex]
        self.rotLabel.setText(f"{rotate_angle:3d}度")
        
        # 親Wigetを辿って、カメラプレビューを回転する
        current_widget = self.parentWidget()
        while current_widget is not None:
            #print(f'Widget: {current_widget.__class__.__name__}')
            if current_widget.__class__.__name__ == "CameraSettingPage":
                current_widget.rotate_camera_preview(rotate_angle)
            current_widget = current_widget.parentWidget()
    
    
    # 現在のセンサモード
    @property
    def current_sensor_mode(self):
        configs = []
        # センサモード一覧
        for mode in picam2s[self.camid].sensor_modes:
            configs.append({"size": mode["size"], "format": mode["format"].format})
        # 選択中のセンサモードを返却
        return configs[self.sensorFormat.currentIndex()]        

    # 命名規則
    @property
    def save_name_rule(self):
        return self.nameRule.currentIndex()

    # ファイル拡張子
    @property
    def save_file_type(self):
        return self.filetype.currentText()

    # 回転変換の角度
    @property
    def rotate_angle(self):
        return self.rotAngles[self.rotIndex]


# 画像調整タブ
class ImageTuningTab(QTabWidget):
    # 初期化
    def __init__(self, camid):        
        # 初期化
        super().__init__()

        # カメラ番号
        self.camid = camid

        # タブページ
        tabPage = QWidget()
        self.addTab(tabPage, "画質調整")
        
        # フォームレイアウト
        formLayout = QFormLayout()
        tabPage.setLayout(formLayout)
        
        # 彩度の対数スライドバー
        # 0-32の範囲、0:グレースケール、1:ノーマル、デフォルト値
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Saturation"]
        self.saturateSlider = logControlSlider()
        self.saturateSlider.setSingleStep(0.1)
        # 最小値、最大値ガードある程度まともな値6を最大に
        self.saturateSlider.setMinimum(minVale)
        self.saturateSlider.setMaximum(6.0)
        # デフォルト値に設定
        self.saturateSlider.setValue(defVale, emit=True)
        # 変更時の動作
        self.saturateSlider.valueChanged.connect(lambda: picam2s[self.camid].set_controls({"Saturation":self.saturateSlider.value()}))
        formLayout.addRow("色の濃さ", self.saturateSlider)
        
        # コントラストの対数スライドバー
        # 0-32の範囲、0:コントラストなし、1:ノーマル、デフォルト値
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Contrast"]
        self.contrastSlider = logControlSlider()
        self.contrastSlider.setSingleStep(0.1)
        self.contrastSlider.setMinimum(minVale)
        self.contrastSlider.setMaximum(6.0)
        self.contrastSlider.setValue(defVale, emit=True)
        self.contrastSlider.valueChanged.connect(lambda: picam2s[self.camid].set_controls({"Contrast":self.contrastSlider.value()}))
        formLayout.addRow("コントラスト", self.contrastSlider)
        
        # シャープネスの対数スライドバー
        # 0-16の範囲、0:シャープネス処理なし、1:ノーマル、デフォルト値
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Sharpness"]
        self.sharpSlider = logControlSlider()
        self.sharpSlider.setSingleStep(0.1)
        self.sharpSlider.setMinimum(minVale)
        self.sharpSlider.setMaximum(maxVale)
        self.sharpSlider.setValue(defVale, emit=True)
        self.sharpSlider.valueChanged.connect(lambda: picam2s[self.camid].set_controls({"Sharpness":self.sharpSlider.value()}))
        formLayout.addRow("シャープネス", self.sharpSlider)
        
        # 明るさのスライドバー
        # -1.0-1.0の範囲、0:デフォルト値
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Brightness"]
        self.brightSlider = controlSlider()
        self.brightSlider.setSingleStep(0.1)
        self.brightSlider.setMinimum(minVale)
        self.brightSlider.setMaximum(maxVale)
        self.brightSlider.setValue(defVale, emit=True)
        self.brightSlider.valueChanged.connect(lambda: picam2s[self.camid].set_controls({"Brightness":self.brightSlider.value()}))
        formLayout.addRow("明るさ", self.brightSlider)
        
        # 画質調整に関するコントロール類の一括更新
        picam2s[camid].set_controls(self.controls_image_tuning)
    
        # リセットボタン
        self.resetButton = QPushButton("初期値に戻す")
        self.resetButton.clicked.connect(self.reset_image_tuning)
        formLayout.addRow("リセット", self.resetButton)
    
    
    @property
    # 画質調整に関するコントロール一覧
    def controls_image_tuning(self):
        return {
            # "ColourCorrectionMatrix": self.ccm.value(),
            "Saturation": self.saturateSlider.value(),
            "Contrast": self.contrastSlider.value(),
            "Sharpness": self.sharpSlider.value(),
            "Brightness": self.brightSlider.value(),
            # "NoiseReductionMode": self.noise_reduction.currentIndex()
        }
    
    # リセットボタンをクリック時の動作
    def reset_image_tuning(self):
        #　カメラ番号
        camid = self.camid
         
        # 彩度
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Saturation"]
        self.saturateSlider.setValue(defVale, emit=True)
    
        # コントラスト
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Contrast"]
        self.contrastSlider.setValue(defVale, emit=True)
        
        # シャープネス
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Sharpness"]
        self.sharpSlider.setValue(defVale, emit=True)
        
        # 明るさ
        minVale, maxVale, defVale = picam2s[camid].camera_controls["Brightness"]
        self.brightSlider.setValue(defVale, emit=True)

        # 画質調整に関するコントロール類の一括更新
        picam2s[camid].set_controls(self.controls_image_tuning)


# フォーカス設定ページ
class FocusSettingPage(QWidget):
    # 初期化
    def __init__(self, camid):        
        # 初期化
        super().__init__()
        
        # カメラ番号
        self.camid = camid
        
        # Top垂直レイアウト
        topVBoxLayout = QVBoxLayout()
        self.setLayout(topVBoxLayout)
        
        # AF/MF切り替えWidget
        focusWidget = QWidget()
        topVBoxLayout.addWidget(focusWidget)
        
        # AF/MF切り替え用フォームレイアウト
        formLayout = QFormLayout()
        focusWidget.setLayout(formLayout)
        
        # MF/AF切り替え
        formLayout.addRow("MF/AF切り替え", QLabel(""))
        
        # フォーカス方式
        # 0:Manualデフォルト, 1:Auto, 2:Continuous
        minVal, maxVal, defVal = picam2s[camid].camera_controls["AfMode"]
        self.focusMode = QComboBox()
        self.focusMode.addItems(["Manual", "Auto", "Continuous"])
        self.focusMode.setCurrentIndex(defVal)
        self.focusMode.currentIndexChanged.connect(self.on_focusmode_changed)
        formLayout.addRow("フォーカス方式", self.focusMode)

        # MF設定用Widget
        self.mfWidget = QWidget()
        topVBoxLayout.addWidget(self.mfWidget)
        
        # MF設定項目用フォームレイアウト
        mfLayout = QFormLayout()
        self.mfWidget.setLayout(mfLayout)
                
        # MF設定項目
        mfLayout.addRow("MF設定項目", QLabel(""))
        
        # レンズ位置
        # 0-32、1:デフォルト値
        minVal, maxVal, defVal = picam2s[camid].camera_controls["LensPosition"]
        self.lensSlider = controlSlider()
        self.lensSlider.setSingleStep(0.1)
        self.lensSlider.setMinimum(minVal)
        self.lensSlider.setMaximum(maxVal)
        self.lensSlider.setValue(defVal, emit=True)
        self.lensSlider.valueChanged.connect(self.on_lenspos_changed)
        mfLayout.addRow("レンズ位置", self.lensSlider)
        
        # リセットボタン
        self.mfResetButton = QPushButton("初期値に戻す")
        self.mfResetButton.clicked.connect(self.on_mfreset_clicked)
        mfLayout.addRow("リセット", self.mfResetButton)
        
        # AF設定用Widget
        self.afWidget = QWidget()
        topVBoxLayout.addWidget(self.afWidget)
        
        # AF設定項目用フォームレイアウト
        afLayout = QFormLayout()
        self.afWidget.setLayout(afLayout)
                
        # AF設定項目
        afLayout.addRow("AF設定項目", QLabel(""))
        
        # AFフレーム種類
        # 0:中央部、デフォルト値、1:AFフレーム指定
        minVal, maxVal, defVal = picam2s[camid].camera_controls["AfMetering"]
        afFrame = QComboBox()
        afFrame.addItems(["画像中央", "カスタム"])
        afFrame.setCurrentIndex(defVal)
        afLayout.addRow("AFフレーム種類", afFrame)
        afFrame.setEnabled(False)
                
        # AFフレーム範囲
        (minXOffset, minYOffset, minWidth, minHeight), \
        (maxXOffset, maxYOffset, maxWidth, maxHeight), \
        (defXOffset, defYOffset, defWidth, defHeight) = picam2s[camid].camera_controls["AfWindows"]
        #print(picam2s[camid].camera_controls["AfWindows"])
        #print((minXOffset, minYOffset, minWidth, minHeight))
        #print((maxXOffset, maxYOffset, maxWidth, maxHeight))
        #print((defXOffset, defYOffset, defWidth, defHeight))
        # XOffset
        XOffset = QSpinBox()
        XOffset.setMinimum(minXOffset)
        XOffset.setMaximum(maxXOffset)
        XOffset.setValue(defXOffset)
        XOffset.setEnabled(False)
        # YOffset
        YOffset = QSpinBox()
        YOffset.setMinimum(minYOffset)
        YOffset.setMaximum(maxYOffset)
        YOffset.setValue(defYOffset)
        YOffset.setEnabled(False)
        # Width
        Width = QSpinBox()
        Width.setMinimum(minWidth)
        Width.setMaximum(maxWidth)
        Width.setValue(defWidth)
        Width.setEnabled(False)
        # Height
        Height = QSpinBox()
        Height.setMinimum(minHeight)
        Height.setMaximum(maxHeight)
        Height.setValue(defHeight)
        Height.setEnabled(False)
        # カスタムAFフレーム
        # XOffset
        XOffsetWidget = QWidget()
        XOffsetHLayout = QHBoxLayout()
        XOffsetWidget.setLayout(XOffsetHLayout)
        XOffsetHLayout.addWidget(QLabel("オフセットX"))
        XOffsetHLayout.addWidget(XOffset)
        afLayout.addRow("AFフレーム範囲", XOffsetWidget)
        # YOffset
        YOffsetWidget = QWidget()
        YOffsetHLayout = QHBoxLayout()
        YOffsetWidget.setLayout(YOffsetHLayout)
        YOffsetHLayout.addWidget(QLabel("オフセットY"))
        YOffsetHLayout.addWidget(YOffset)
        afLayout.addRow("", YOffsetWidget)
        # Width
        WidthWidget = QWidget()
        WidthHLayout = QHBoxLayout()
        WidthWidget.setLayout(WidthHLayout)
        WidthHLayout.addWidget(QLabel("AFフレーム幅"))
        WidthHLayout.addWidget(Width)
        afLayout.addRow("", WidthWidget)
        # Height
        HeightWidget = QWidget()
        HeightHLayout = QHBoxLayout()
        HeightWidget.setLayout(HeightHLayout)
        HeightHLayout.addWidget(QLabel("AFフレーム高さ"))
        HeightHLayout.addWidget(Height)
        afLayout.addRow("", HeightWidget)
        
        # AF距離範囲
        # 0:Normal、デフォルト値、1:Macro、2:Full
        minVal, maxVal, defVal = picam2s[camid].camera_controls["AfRange"]
        afRange = QComboBox()
        afRange.addItems(["Normal", "Macro", "Full"])
        afRange.setCurrentIndex(defVal)     
        afLayout.addRow("AF距離範囲", afRange)
        afRange.setEnabled(False)
        
        # AFスピード
        # 0:Normal、1:Fast
        minVal, maxVal, defVal = picam2s[camid].camera_controls["AfSpeed"]
        afSpeed = QComboBox()
        afSpeed.addItems(["Normal", "Fast"])
        afSpeed.setCurrentIndex(defVal)     
        afLayout.addRow("AFスピード", afSpeed)
        afSpeed.setEnabled(False)
        
        # リセットボタン
        self.afResetButton = QPushButton("初期値に戻す")
        afLayout.addRow("リセット", self.afResetButton)
        self.afResetButton.setEnabled(False)
    
        # MF初期値のため無効化
        self.afWidget.setEnabled(False)


    # フォーカス方式変更時の動作
    def on_focusmode_changed(self):
        # 現在の選択項目
        index = self.focusMode.currentIndex()   
             
        # MF/AF設定項目の有効、無効化
        self.mfWidget.setEnabled(True if index==0 else False)
        self.afWidget.setEnabled(False if index==0 else True)
        
        # カメラコントロール更新
        picam2s[self.camid].set_controls({"AfMode":self.focusMode.currentIndex()})


    # レンズ位置スライダ変更時の動作
    def on_lenspos_changed(self):
        # MFの場合
        if self.focusMode.currentIndex()==0:
            # カメラコントロール更新
            picam2s[self.camid].set_controls({"LensPosition":self.lensSlider.value()})


    # MFリセットボタンをクリック時の動作
    def on_mfreset_clicked(self):
        # カメラ番号
        camid = self.camid
        # レンズ位置
        minVal, maxVal, defVal = picam2s[camid].camera_controls["LensPosition"]
        self.lensSlider.setValue(defVal, emit=True)


    @property
    # フォーカス設定に関するコントロール一覧
    def controls_focus_setting(self):
        return {
            "AfMode": self.focusMode.currentIndex(),
            "LensPosition": self.lensSlider.value()
        }


# 画像処理設定ページ
class TransformSetPage(QWidget):
    # 初期化
    def __init__(self, camid, imageTransView):        
        # 初期化
        super().__init__()
        
        # カメラ番号
        self.camid = camid
        
        # 画像変換ビュー
        self.image_file = None
        self.imageTransView = imageTransView
        
        # Top垂直レイアウト
        topVBoxLayout = QVBoxLayout()
        self.setLayout(topVBoxLayout)
        
        # サンプル画像選択ボタン
        selectImageButton = QPushButton("サンプル画像を選択する")
        selectImageButton.clicked.connect(self.on_selectImageButton_clicked)
        topVBoxLayout.addWidget(selectImageButton)
        
        # アクリル板切り出し設定Widget
        acrylicSetWidget = QWidget()
        topVBoxLayout.addWidget(acrylicSetWidget)
        
        # アクリル板設定のトップレイアウト
        acrylicSetVBoxLayout = QVBoxLayout()
        acrylicSetWidget.setLayout(acrylicSetVBoxLayout)
        
        # アクリル板切り出し有効化フラグ
        acrylicEnableWidget = QWidget()
        acrylicSetVBoxLayout.addWidget(acrylicEnableWidget)
        acrylicEnableHBoxLayout = QHBoxLayout()
        acrylicEnableWidget.setLayout(acrylicEnableHBoxLayout)
        self.acrylicEnableCheck = QCheckBox()
        self.acrylicEnableCheck.setChecked(True)
        acrylicEnableHBoxLayout.addWidget(self.acrylicEnableCheck)
        acrylicEnableHBoxLayout.addWidget(QLabel("アクリル板の範囲を切り出す"))
        acrylicEnableHBoxLayout.addStretch(1)
        
        # アクリル板4点ポリゴンの設定
        # 左上座標設定
        acrylicTopLeftWidget = QWidget()
        acrylicSetVBoxLayout.addWidget(acrylicTopLeftWidget)
        acrylicTopLeftHBoxLayout = QHBoxLayout()
        acrylicTopLeftWidget.setLayout(acrylicTopLeftHBoxLayout)
        acrylicTopLeftHBoxLayout.addStretch(1)
        redLabel = QCircleLabel(Qt.red)
        redLabel.setFixedSize(20, 20)
        acrylicTopLeftHBoxLayout.addWidget(redLabel)
        acrylicTopLeftHBoxLayout.addWidget(QLabel("左上:  "))
        acrylicTopLeftHBoxLayout.addWidget(QLabel("X座標"))
        self.acrylicTopLeftX = QSpinBox()
        acrylicTopLeftHBoxLayout.addWidget(self.acrylicTopLeftX)
        self.acrylicTopLeftX.setMinimum(0)
        self.acrylicTopLeftX.setMaximum(2592)
        #self.acrylicTopLeftX.setValue(500)
        self.acrylicTopLeftX.lineEdit().setAlignment(Qt.AlignRight)
        width = self.acrylicTopLeftX.fontMetrics().width("2592")
        self.acrylicTopLeftX.setFixedWidth(width + 50) 
        acrylicTopLeftHBoxLayout.addWidget(QLabel("  "))
        acrylicTopLeftHBoxLayout.addWidget(QLabel("Y座標"))
        self.acrylicTopLeftY = QSpinBox()
        acrylicTopLeftHBoxLayout.addWidget(self.acrylicTopLeftY)
        self.acrylicTopLeftY.setMinimum(0)
        self.acrylicTopLeftY.setMaximum(4608)
        #self.acrylicTopLeftY.setValue(500)
        self.acrylicTopLeftY.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicTopLeftY.setFixedWidth(width + 50) 
        
        # 右上座標
        acrylicTopRightWidget = QWidget()
        acrylicSetVBoxLayout.addWidget(acrylicTopRightWidget)
        acrylicTopRightHBoxLayout = QHBoxLayout()
        acrylicTopRightWidget.setLayout(acrylicTopRightHBoxLayout)
        acrylicTopRightHBoxLayout.addStretch(1)
        greenLabel = QCircleLabel(Qt.green)
        greenLabel.setFixedSize(20, 20)
        acrylicTopRightHBoxLayout.addWidget(greenLabel)
        acrylicTopRightHBoxLayout.addWidget(QLabel("右上:  "))
        acrylicTopRightHBoxLayout.addWidget(QLabel("X座標"))
        self.acrylicTopRightX = QSpinBox()
        acrylicTopRightHBoxLayout.addWidget(self.acrylicTopRightX)
        self.acrylicTopRightX.setMinimum(0)
        self.acrylicTopRightX.setMaximum(2592)
        #self.acrylicTopRightX.setValue(500)
        self.acrylicTopRightX.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicTopRightX.setFixedWidth(width + 50) 
        acrylicTopRightHBoxLayout.addWidget(QLabel("  "))
        acrylicTopRightHBoxLayout.addWidget(QLabel("Y座標"))
        self.acrylicTopRightY = QSpinBox()
        acrylicTopRightHBoxLayout.addWidget(self.acrylicTopRightY)
        self.acrylicTopRightY.setMinimum(0)
        self.acrylicTopRightY.setMaximum(4608)
        #self.acrylicTopRightY.setValue(500)
        self.acrylicTopRightY.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicTopRightY.setFixedWidth(width + 50) 
        
        # 右下座標
        acrylicBottomRightWidget = QWidget()
        acrylicSetVBoxLayout.addWidget(acrylicBottomRightWidget)
        acrylicBottomRightHBoxLayout = QHBoxLayout()
        acrylicBottomRightWidget.setLayout(acrylicBottomRightHBoxLayout)
        acrylicBottomRightHBoxLayout.addStretch(1)
        blueLabel = QCircleLabel(Qt.blue)
        blueLabel.setFixedSize(20, 20)
        acrylicBottomRightHBoxLayout.addWidget(blueLabel)
        acrylicBottomRightHBoxLayout.addWidget(QLabel("右下:  "))
        acrylicBottomRightHBoxLayout.addWidget(QLabel("X座標"))
        self.acrylicBottomRightX = QSpinBox()
        acrylicBottomRightHBoxLayout.addWidget(self.acrylicBottomRightX)
        self.acrylicBottomRightX.setMinimum(0)
        self.acrylicBottomRightX.setMaximum(2592)
        #self.acrylicBottomRightX.setValue(500)
        self.acrylicBottomRightX.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicBottomRightX.setFixedWidth(width + 50) 
        acrylicBottomRightHBoxLayout.addWidget(QLabel("  "))
        acrylicBottomRightHBoxLayout.addWidget(QLabel("Y座標"))
        self.acrylicBottomRightY = QSpinBox()
        acrylicBottomRightHBoxLayout.addWidget(self.acrylicBottomRightY)
        self.acrylicBottomRightY.setMinimum(0)
        self.acrylicBottomRightY.setMaximum(4608)
        #self.acrylicBottomRightY.setValue(500)
        self.acrylicBottomRightY.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicBottomRightY.setFixedWidth(width + 50) 
        
        # 左下座標
        acrylicBottomLeftWidget = QWidget()
        acrylicSetVBoxLayout.addWidget(acrylicBottomLeftWidget)
        acrylicBottomLeftHBoxLayout = QHBoxLayout()
        acrylicBottomLeftWidget.setLayout(acrylicBottomLeftHBoxLayout)
        acrylicBottomLeftHBoxLayout.addStretch(1)
        yellowLabel = QCircleLabel(Qt.yellow)
        yellowLabel.setFixedSize(20, 20)
        acrylicBottomLeftHBoxLayout.addWidget(yellowLabel)
        acrylicBottomLeftHBoxLayout.addWidget(QLabel("左下:  "))
        acrylicBottomLeftHBoxLayout.addWidget(QLabel("X座標"))
        self.acrylicBottomLeftX = QSpinBox()
        acrylicBottomLeftHBoxLayout.addWidget(self.acrylicBottomLeftX)
        self.acrylicBottomLeftX.setMinimum(0)
        self.acrylicBottomLeftX.setMaximum(2592)
        #self.acrylicBottomLeftX.setValue(500)
        self.acrylicBottomLeftX.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicBottomLeftX.setFixedWidth(width + 50) 
        acrylicBottomLeftHBoxLayout.addWidget(QLabel("  "))
        acrylicBottomLeftHBoxLayout.addWidget(QLabel("Y座標"))
        self.acrylicBottomLeftY = QSpinBox()
        acrylicBottomLeftHBoxLayout.addWidget(self.acrylicBottomLeftY)
        self.acrylicBottomLeftY.setMinimum(0)
        self.acrylicBottomLeftY.setMaximum(4608)
        #self.acrylicBottomLeftY.setValue(500)
        self.acrylicBottomLeftY.lineEdit().setAlignment(Qt.AlignRight)
        self.acrylicBottomLeftY.setFixedWidth(width + 50) 
        
        topVBoxLayout.addStretch(1)
        
        # サンプル画像変換ボタン
        transImageButton = QPushButton("サンプル画像を変換する")
        topVBoxLayout.addWidget(transImageButton)
        transImageButton.clicked.connect(self.on_transImageButton_clicked)


    def on_selectImageButton_clicked(self):
        # ファイル読み込みのダイアログ
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.image_file, _ = QFileDialog.getOpenFileName(self, "サンプル画像を開く", "", "JPEG Files (*.jpg);;All Files (*)", options=options)        
        if self.image_file :
            # アクリル板4点
            circles = []
            x = self.acrylicTopLeftX.value()
            y = self.acrylicTopLeftY.value()
            circles.append(QPointF(x, y))
            x = self.acrylicTopRightX.value()
            y = self.acrylicTopRightY.value()
            circles.append(QPointF(x, y))
            x = self.acrylicBottomRightX.value()
            y = self.acrylicBottomRightY.value()
            circles.append(QPointF(x, y))
            x = self.acrylicBottomLeftX.value()
            y = self.acrylicBottomLeftY.value()
            circles.append(QPointF(x, y))
            # 画像とアクリル板4点のロード
            self.imageTransView.loadImage(self.image_file, circles)


    def on_transImageButton_clicked(self):
        # オリジナル画像
        image_org = cv2.imread(self.image_file)
        
        # アクリル板切り出し、平面化
        # オリジナル画像内の4点位置
        src = []
        for ivert, circle in enumerate(self.imageTransView.ellipses):
            x, y = circle.scene_position()
            src.append((x, y))
        src = np.float32(src)
        
        # 300dpiで変換
        wmin = 100
        hmin = 100
        width = int(182/25.4*300)
        height = int((300-13-13)/25.4*300) 
                
        # 変換画像内の4点
        dst = np.float32([(wmin, hmin), (wmin+width, hmin), (wmin+width, hmin+height), (wmin, hmin+height)])
        
        # 射影変換
        M = cv2.getPerspectiveTransform(src, dst)
        image_trans = cv2.warpPerspective(image_org, M, (wmin+width+wmin,hmin+height+hmin), borderValue=(0, 0,0))
        
        # 一時出力
        trans_file = "image_trans.jpg"
        cv2.imwrite(trans_file, image_trans)
        
        self.image_file = trans_file
        self.imageTransView.loadImage(self.image_file)
        

# コントロールタブ
class CameraControlTab(QTabWidget):
    # 初期化
    def __init__(self, camid, imageTransView):        
        # 初期化
        super().__init__()

        # カメラ番号
        self.camid = camid

        # フォーカス設定ページ
        self.focusPage = FocusSettingPage(camid)
        self.addTab(self.focusPage, "フォーカス設定")

        # ズーム設定ページ
        #zoomPage = QWidget()
        #self.addTab(zoomPage, "ズーム設定")

        # AEC/AWBページ
        #aewbPage = QWidget()
        #self.addTab(aewbPage, "露出/WB設定")
        
        # メタ情報タブ
        self.metaInfo = QLabel(alignment=Qt.AlignTop)
        self.addTab(self.metaInfo, "メタ情報")
        
        # 画像処理タブ
        self.tranTab = TransformSetPage(camid, imageTransView)
        self.addTab(self.tranTab, "画像変換")


# 設定タブ
class CameraSettingPage(QWidget):
    # 初期化
    def __init__(self):        
        # 初期化
        super().__init__()  
        
        # カメラ選択のコンボボックス
        self.cameraSelect = QComboBox()
        model = QStandardItemModel()
        for index, item in enumerate(["Camera0", "Camera1"]):
            item = QStandardItem(item)
            if picam2s[index] is None:
                item.setEnabled(False)
            model.appendRow(item)
        self.cameraSelect.setModel(model)
        self.cameraSelect.currentIndexChanged.connect(self.on_cameraSelect_changed)
                
        # 設定ファイル選択ボタン
        self.selectButton = QPushButton("設定ファイル選択")
        self.selectButton.setIcon(QIcon("./Resource/files.png"))
        # クリック時の動作
        self.selectButton.clicked.connect(self.on_selectButton_clicked)
        
         # カメラ番号
        camid = self.cameraSelect.currentIndex()
        
        # 現在のコンフィグファイル名
        self.configName = QLabel("現在の設定ファイル名：なし(初期値)")
        
        # カメラプレビュー
        # QGlPicamera2回転できないので使用せず
        #preview_height =  int(1080*3/4)
        #preview_width = int(preview_height*0.8)
        #cameraPreview = QGlPicamera2(picam2s[camid], width=preview_width, height=preview_height, keep_ar=True)
        self.cameraPreview0 = CustomQCameraPreview(picam2s[0])
        self.cameraPreview1 = CustomQCameraPreview(picam2s[1])
        
        # 画像変換設定ビュー
        self.imageTransView = CustomQImageViewer2()
        
        # 基本設定タブ
        self.basicSettingTab = BasicSettingTab(camid)
        
        # 画質調整タブ
        self.imageTuningTab = ImageTuningTab(camid)
        
        # 撮影ボタン
        self.shutterButton = QPushButton("テスト撮影")
        self.shutterButton.setIcon(QIcon("./Resource/shutter.png"))
        # 撮影ボタンクリック時の動作
        self.shutterButton.clicked.connect(self.on_shutterButton_clicked)
        
        # 設定出力ボタン
        self.outputButton = QPushButton("設定ファイル出力")
        self.outputButton.setIcon(QIcon("./Resource/files.png"))
        self.outputButton.clicked.connect(self.on_outputButton_clicked)
        
        # その他の設定タブ
        # AF/MF、Pan/Zoom、AEC/AWBタブ
        self.controlTabs = CameraControlTab(camid, self.imageTransView)
        self.controlTabs.currentChanged.connect(self.on_controlTabs_changed)
        
        # Widget配置
        # 最上位水平レイアウト
        topHBoxLayout = QHBoxLayout()
        self.setLayout(topHBoxLayout)
 
        # 1列目(基本設定、画質調整、撮影ボタン、反映ボタン)
        leftWidget = QWidget()
        topHBoxLayout.addWidget(leftWidget, 1)
        
        # 垂直レイアウト
        leftVBoxLayout = QVBoxLayout()
        leftWidget.setLayout(leftVBoxLayout) 
        
        # 上部コントロール類のWidget
        ctrlWidget = QWidget()
        leftVBoxLayout.addWidget(ctrlWidget)
        # 水平レイアウト
        ctrlHBoxLayout = QHBoxLayout()
        ctrlWidget.setLayout(ctrlHBoxLayout)
        # カメラ選択のコンボボックス
        ctrlHBoxLayout.addWidget(self.cameraSelect, 2)
        # 選択ボタン
        ctrlHBoxLayout.addWidget(self.selectButton, 1)
        
        # 現在のコンフィグファイル表示
        leftVBoxLayout.addWidget(self.configName)
        
        # 下部の各種設定タブ 
        # 基本設定タブ
        leftVBoxLayout.addWidget(self.basicSettingTab)
        # 画質調整タブ
        leftVBoxLayout.addWidget(self.imageTuningTab)
        
        # 下部コントロール類のWidget
        ctrlWidget2 = QWidget()
        leftVBoxLayout.addWidget(ctrlWidget2)
        # 水平レイアウト
        ctrlHBoxLayout2 = QHBoxLayout()
        ctrlWidget2.setLayout(ctrlHBoxLayout2)
        # 撮影ボタン
        ctrlHBoxLayout2.addWidget(self.shutterButton)
        # 反映ボタン
        ctrlHBoxLayout2.addWidget(self.outputButton)
        
        # 2列目(各種コントロールタブ)
        topHBoxLayout.addWidget(self.controlTabs, 1)
        
        # 3列目(プレビュー画面)
        # QGLPreviewは回転できないので使えず
        topHBoxLayout.addWidget(self.cameraPreview0, 1)
        topHBoxLayout.addWidget(self.cameraPreview1, 1)
        self.cameraPreview1.hide()
        topHBoxLayout.addWidget(self.imageTransView, 1)
        self.imageTransView.hide()
        
        # 設定コンフィグ反映
        self.load_camera_configure(configfiles[camid])        
        # 回転反映
        QTimer.singleShot(1000, lambda:self.rotate_camera_preview(self.basicSettingTab.rotate_angle))
        
        # プレビュー開始
        picam2s[0].start()
        picam2s[1].start()
        
        # widgets更新タイマ
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_realtime_widgets)
        self.timer.start(30)


    # カメラプレビュー回転
    def rotate_camera_preview(self, rotate):
        # カメラ番号
        camid = self.cameraSelect.currentIndex()
        if camid == 0:
            self.cameraPreview0.rotate_image(rotate)
        else:
            self.cameraPreview1.rotate_image(rotate)
    
    
    # リアルタイム性のあるWidgetの更新
    def update_realtime_widgets(self):
        # AFの場合、レンズ位置更新
        #index = self.controlTabs.focusPage.focusMode.currentIndex()
        #if index != 0:
        #    # ちょっとメタデータからレンズ位置を取る
        #    #self.controlTabs.focusPage.lensSlider.setValue(defVal, emit=True)
        
        # カメラ番号
        camid = self.cameraSelect.currentIndex()
        
        # メタ情報更新
        self.controlTabs.metaInfo.setText(pimetadatas[camid])
        
        # アクリル板の4点座標を更新
        for ivert, circle in enumerate(self.imageTransView.ellipses):
            x, y = circle.scene_position()
            if ivert == 0:
                self.controlTabs.tranTab.acrylicTopLeftX.setValue(x)
                self.controlTabs.tranTab.acrylicTopLeftY.setValue(y)
            elif ivert == 1:
                self.controlTabs.tranTab.acrylicTopRightX.setValue(x)
                self.controlTabs.tranTab.acrylicTopRightY.setValue(y)
            elif ivert == 2:
                self.controlTabs.tranTab.acrylicBottomRightX.setValue(x)
                self.controlTabs.tranTab.acrylicBottomRightY.setValue(y)
            elif ivert == 3:
                self.controlTabs.tranTab.acrylicBottomLeftX.setValue(x)
                self.controlTabs.tranTab.acrylicBottomLeftY.setValue(y)
        
        pass

    # 撮影ボタンクリック時の動作
    def on_shutterButton_clicked(self):        
        # 撮影ボタン無効化
        self.shutterButton.setEnabled(False)
        
        # カメラ番号
        camid = self.cameraSelect.currentIndex()
        
        # ファイル名
        filetype = self.basicSettingTab.save_file_type
        namerule = self.basicSettingTab.save_name_rule
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{'left' if namerule==0 else 'right'}" + f".{filetype}"
        
        # 静止画撮影
        picam2s[camid].switch_mode_and_capture_file(piconfigs[camid]["still"], filename)
        
        # 回転変換
        qimage = QImage(filename)
        rotate_angle = self.basicSettingTab.rotate_angle
        transform = QTransform().rotate(rotate_angle)
        qimage = qimage.transformed(transform)
        
        # ファイル出力
        qimage.save(filename)
        
        '''
        # カメラ停止
        picam2s[camid].stop()
        # キャプチャコンフィグ
        picam2s[camid].configure(piconfigs[camid]["still"])
        # カメラ開始
        picam2s[camid].start()
        
        # Controls更新
        # デジタルズーム解除
        # ScalerCropをリセット、自動で戻っているようだが
        _, (_, _, sensor_width, sensor_height), _ = picam2s[camid].camera_controls['ScalerCrop']
        picam2s[camid].set_controls({"ScalerCrop": (0, 0, sensor_width, sensor_height)})
        
        # 自動で引き継がれていそう
        # 画質設定
        picam2s[camid].set_controls(self.imageTuningTab.controls_image_tuning)
        
        # フォーカス設定
        picam2s[camid].set_controls(self.controlTabs.focusPage.controls_focus_setting)
        
        # キャプチャ画像保存
        frame = picam2s[camid].capture_array()
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        qimage = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # 回転変換
        rotate_angle = self.basicSettingTab.rotate_angle
        transform = QTransform().rotate(rotate_angle)
        qimage = qimage.transformed(transform)
        
        # ファイル出力
        qimage.save(filename)
        
        # カメラ停止
        picam2s[camid].stop()
        # プレビューコンフィグ
        picam2s[camid].configure(piconfigs[camid]["preview"])
        # カメラ開始
        picam2s[camid].start()
        '''
        
        # 撮影ボタン有効化
        self.shutterButton.setEnabled(True)

    # コンフィグファイルの設定反映
    def load_camera_configure(self, config_file):
        # コンフィグファイル読み込み
        with open(config_file,'r', encoding="utf-8") as f:
            config = json.load(f)
        
        # 基本設定
        # 命名規則
        index = config["BasicSetting"]["nameRule"]
        self.basicSettingTab.nameRule.setCurrentIndex(index)
        
        # 保存形式
        index = config["BasicSetting"]["filetype"]
        self.basicSettingTab.filetype.setCurrentIndex(index)
        
        # 画像サイズ
        width, height = config["BasicSetting"]["ImageSize"]
        # 画像幅
        self.basicSettingTab.imageWidth.setValue(width)
        # 画像高さ
        self.basicSettingTab.imageHeight.setValue(height)
        
        # 回転角度
        rotIndex = config["BasicSetting"]["RoteIndex"]
        self.basicSettingTab.rotIndex = rotIndex
        text = f"{self.basicSettingTab.rotAngles[self.basicSettingTab.rotIndex]:3d}度"
        self.basicSettingTab.rotLabel.setText(text)
        
        # 基本設定の反映
        self.basicSettingTab.update_basic_config()
        
        # 画質調整
        # 彩度
        val = config["ImageTuning"]["Saturation"]
        self.imageTuningTab.saturateSlider.setValue(val, emit=True)
        
        # コントラスト
        val = config["ImageTuning"]["Contrast"]
        self.imageTuningTab.contrastSlider.setValue(val, emit=True)
        
        # シャープネス
        val = config["ImageTuning"]["Sharpness"]
        self.imageTuningTab.sharpSlider.setValue(val, emit=True)
        
        # 明るさ
        val = config["ImageTuning"]["Brightness"]
        self.imageTuningTab.brightSlider.setValue(val, emit=True)
        
        # 画質調整の反映
        # カメラ番号
        camid = self.cameraSelect.currentIndex()
        picam2s[camid].set_controls(self.imageTuningTab.controls_image_tuning)
        
        # フォーカス設定
        # フォーカス方式
        index = config["FocusSetting"]["AfMode"]
        self.controlTabs.focusPage.focusMode.setCurrentIndex(index)
        
        #　MF設定
        # レンズ位置
        val = config["FocusSetting"]["LensPosition"]
        self.controlTabs.focusPage.lensSlider.setValue(val, emit=True)
        
        # フォーカス設定の反映
        picam2s[camid].set_controls(self.controlTabs.focusPage.controls_focus_setting)
        
        # 画像変換
        # アクリル板の4点座標
        for ivert, circle in enumerate(config["ImageTransform"]["AcrylicPoints"]):
            x, y = circle
            if ivert == 0:
                self.controlTabs.tranTab.acrylicTopLeftX.setValue(x)
                self.controlTabs.tranTab.acrylicTopLeftY.setValue(y)
            elif ivert == 1:
                self.controlTabs.tranTab.acrylicTopRightX.setValue(x)
                self.controlTabs.tranTab.acrylicTopRightY.setValue(y)
            elif ivert == 2:
                self.controlTabs.tranTab.acrylicBottomRightX.setValue(x)
                self.controlTabs.tranTab.acrylicBottomRightY.setValue(y)
            elif ivert == 3:
                self.controlTabs.tranTab.acrylicBottomLeftX.setValue(x)
                self.controlTabs.tranTab.acrylicBottomLeftY.setValue(y)
        
        # コンフィグファイル名更新
        filename = os.path.basename(config_file)
        self.configName.setText("現在の設定ファイル名： " + filename)

    # 設定ファイル選択ボタンをクリック時の動作
    def on_selectButton_clicked(self):
        # 設定ファイルダイアログ
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        config_file, _ = QFileDialog.getOpenFileName(self, "設定ファイルを開く", "", "JSON Files (*.json);;All Files (*)", options=options)        
        if config_file:
            # カメラ設定読み込み、反映
            self.load_camera_configure(config_file)
        
        # カメラプレビュー回転リセット
        rotate_angle = self.basicSettingTab.rotate_angle
        self.rotate_camera_preview(rotate_angle)

    # コンフィグファイル書き出し
    def output_camera_configure(self, config_file):
        # カメラコンフィグ
        config = {}
        
        # 基本設定
        config["BasicSetting"] = {}
        
        # 命名規則
        config["BasicSetting"]["nameRule"] = self.basicSettingTab.nameRule.currentIndex()
        
        # 保存形式
        config["BasicSetting"]["filetype"] = self.basicSettingTab.filetype.currentIndex()
        
        # センサフォーマット
        config["BasicSetting"]["sensorFormat"] = self.basicSettingTab.current_sensor_mode
        
        # 画像サイズ
        # 画像幅
        width = self.basicSettingTab.imageWidth.value()
        # 画像高さ
        height = self.basicSettingTab.imageHeight.value()
        config["BasicSetting"]["ImageSize"] = [width, height]
        
        # 回転角度
        config["BasicSetting"]["RoteIndex"] = self.basicSettingTab.rotIndex
        
        # 画質調整
        config["ImageTuning"] = {}
        
        # 彩度
        config["ImageTuning"]["Saturation"] = self.imageTuningTab.saturateSlider.value()
        
        # コントラスト
        config["ImageTuning"]["Contrast"] = self.imageTuningTab.contrastSlider.value()
        
        # シャープネス
        config["ImageTuning"]["Sharpness"] = self.imageTuningTab.sharpSlider.value()
                
        # 明るさ
        config["ImageTuning"]["Brightness"] = self.imageTuningTab.brightSlider.value()
        
        # フォーカス設定
        config["FocusSetting"] = {}
        
        # フォーカス方式
        config["FocusSetting"]["AfMode"] = self.controlTabs.focusPage.focusMode.currentIndex()
        
        #　MF設定
        # レンズ位置
        config["FocusSetting"]["LensPosition"] = self.controlTabs.focusPage.lensSlider.value()
        
        # 画像変換設定
        config["ImageTransform"] = {}
        
        # アクリル板の4点座標を更新
        circles = []
        x = self.controlTabs.tranTab.acrylicTopLeftX.value()
        y = self.controlTabs.tranTab.acrylicTopLeftY.value()
        circles.append([x, y])
        x = self.controlTabs.tranTab.acrylicTopRightX.value()
        y = self.controlTabs.tranTab.acrylicTopRightY.value()
        circles.append([x, y])
        x = self.controlTabs.tranTab.acrylicBottomRightX.value()
        y = self.controlTabs.tranTab.acrylicBottomRightY.value()
        circles.append([x, y])
        x = self.controlTabs.tranTab.acrylicBottomLeftX.value()
        y = self.controlTabs.tranTab.acrylicBottomLeftY.value()
        circles.append([x, y])
        config["ImageTransform"]["AcrylicPoints"] = circles
        
        # 出力
        with open(config_file, 'w') as fout:
            json.dump(config, fout, indent=4)
        
        # コンフィグファイル名更新
        filename = os.path.basename(config_file)
        self.configName.setText("現在の設定ファイル名： " + filename)

    # 設定出力ボタンをクリック時の動作
    def on_outputButton_clicked(self):
        # ファイル保存ダイアログ
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self, "設定ファイルを保存", "", "JSON Files (*.json);;All Files (*)", options=options)
        if fileName:
            # 設定ファイル出力
            self.output_camera_configure(fileName)

    # 対象カメラ変更時の動作
    def on_cameraSelect_changed(self):
        # 現在選択Index
        index = self.cameraSelect.currentIndex()
        
        # カメラ番号の変更
        # 基本設定
        self.basicSettingTab.camid = index
        
        # 画質調整
        self.imageTuningTab.camid = index
        
        # フォーカス設定
        self.controlTabs.focusPage.camid = index
        
        # 初期値コンフィグ反映
        self.load_camera_configure(configfiles[index])
        
        # カメラプレビュー回転リセット
        rotate_angle = self.basicSettingTab.rotate_angle
        self.rotate_camera_preview(rotate_angle)        
        
        # プレビュー切り替え
        if index == 0:
            self.cameraPreview0.show()
            self.cameraPreview1.hide()
        else:
            self.cameraPreview0.hide()
            self.cameraPreview1.show()
        
        # 画像変換タブがアクティブの場合
        current_index = self.controlTabs.currentIndex()
        current_tab_name = self.controlTabs.tabText(current_index)
        if current_tab_name == "画像変換":
            self.cameraPreview0.hide()
            self.cameraPreview1.hide()
            self.imageTransView.show()
        
        
    # その他の設定のタブ変更に動作
    def on_controlTabs_changed(self, index):
        active_tab_name = self.controlTabs.tabText(index)
        if active_tab_name == "画像変換":
            self.cameraPreview0.hide()
            self.cameraPreview1.hide()
            self.imageTransView.show()
        else:
            self.imageTransView.hide()
            index = self.cameraSelect.currentIndex()
            if index == 0:
                self.cameraPreview0.show()
                self.cameraPreview1.hide()
            else:
                self.cameraPreview0.hide()
                self.cameraPreview1.show()
