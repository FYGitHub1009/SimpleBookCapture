import os
import json, shutil
from datetime import datetime
import numpy as np

import xmltodict
from PIL import Image
import pyzbar.pyzbar as pyzbar
import urllib

from playsound import playsound

# Qt関係
from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGroupBox, QMenu, QMessageBox
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtWidgets import QPushButton, QComboBox
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTableView, QStyledItemDelegate, QHeaderView, QStyle, QAbstractItemView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap, QBrush, QColor
from PyQt5.QtCore import QRect, QMimeData, QModelIndex, QPoint
from PyQt5.QtGui import QImage, QPixmap, QTransform
from PyQt5 import QtWidgets, QtCore, QtGui
# カスタムWidget
from CustomQImageViewer import CustomQImageViewer
from CustomQCameraPreview import CustomQCameraPreview
from CustomQBookInfoForm import CustomQBookInfoForm
from CustomQWidgets import yes_no_dialog

# PiCamera2グローバル変数
from GlobalVariables import picam2s, piconfigs, pimetadatas, configfiles

# 画像変換
import cv2
import ImageTransform

# QImage->PILImage変換
def qimage_to_pilimage(qimage):
    # QImageのデータを取得
    buffer = qimage.bits().asstring(qimage.byteCount())
    # QImageのフォーマットを確認
    if qimage.format() == QImage.Format_RGB32:
        image = Image.frombuffer('RGBA', (qimage.width(), qimage.height()), buffer, 'raw', 'BGRA', 0, 1)
    elif qimage.format() == QImage.Format_ARGB32:
        image = Image.frombuffer('RGBA', (qimage.width(), qimage.height()), buffer, 'raw', 'BGRA', 0, 1)
    elif qimage.format() == QImage.Format_RGB888:
        image = Image.frombuffer('RGB', (qimage.width(), qimage.height()), buffer, 'raw', 'RGB', 0, 1)
    else:
        raise ValueError(f"Unsupported QImage format: {qimage.format()}")
    
    return image

hicon = 200
hrow = 220

class ThumbnailDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 選択されている場合の背景色を設定
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QBrush(QColor("#3399FF")))

        pixmap = index.data(Qt.DecorationRole)
        if isinstance(pixmap, QPixmap):
            rect = option.rect
            target_rect = QRect(
                rect.x() + (rect.width() - pixmap.width()) // 2,
                rect.y() + (rect.height() - pixmap.height()) // 2,
                pixmap.width(),
                pixmap.height()
            )
            painter.drawPixmap(target_rect, pixmap)
        else:
            super().paint(painter, option, index)


class ThumbnailTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data, parent=None, *args):
        super().__init__(parent, *args)
        self._data = data

    def columnCount(self, parent=None) -> int:
        return 4  # 1列目: 左ファイル名, 2列目: 左サムネイル, 3列目: 右ファイル名, 4列目: 右サムネイル

    def rowCount(self, parent=None) -> int:
        return len(self._data)

    def headerData(self, column: int, orientation, role: QtCore.Qt.ItemDataRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return ('左ファイル名', '左ページ', '右ファイル名', '右ページ')[column]
        return None

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole):
        if not index.isValid():
            return None

        if index.row() >= len(self._data):
            return None

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() in {0, 2}:  # ファイル名を表示
                return self._data[index.row()][index.column()]

        if role == QtCore.Qt.DecorationRole:
            if index.column() == 1:  # 左のサムネイルを表示
                image_path = self._data[index.row()][1]
            elif index.column() == 3:  # 右のサムネイルを表示
                image_path = self._data[index.row()][3]
            else:
                return None

            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                return pixmap.scaledToHeight(hicon, Qt.SmoothTransformation)
                #return pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemIsDropEnabled
        if index.row() < len(self._data):
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
        return QtCore.Qt.ItemIsEnabled

    def supportedDropActions(self) -> bool:
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def relocateRow(self, row_source, row_target) -> None:
        row_a, row_b = max(row_source, row_target), min(row_source, row_target)
        self.beginMoveRows(QtCore.QModelIndex(), row_a, row_a, QtCore.QModelIndex(), row_b)
        self._data.insert(row_target, self._data.pop(row_source))
        self.endMoveRows()

    def insertRow(self, position, left_file_name, left_image_path, right_file_name, right_image_path):
        self.beginInsertRows(QtCore.QModelIndex(), position, position)
        self._data.insert(position, (left_file_name, left_image_path, right_file_name, right_image_path))
        self.endInsertRows()

    def removeRow(self, position):
        self.beginRemoveRows(QtCore.QModelIndex(), position, position)
        self._data.pop(position)
        self.endRemoveRows()


class ThumbnailTableView(QTableView):
    class DropmarkerStyle(QtWidgets.QProxyStyle):
        def drawPrimitive(self, element, option, painter, widget=None):
            if element == self.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
                option_new = QtWidgets.QStyleOption(option)
                option_new.rect.setLeft(0)
                if widget:
                    option_new.rect.setRight(widget.width())
                option = option_new
            super().drawPrimitive(element, option, painter, widget)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().hide()
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setStyle(self.DropmarkerStyle())
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def dropEvent(self, event):
        if (event.source() is not self or
            (event.dropAction() != QtCore.Qt.MoveAction and
             self.dragDropMode() != QtWidgets.QAbstractItemView.InternalMove)):
            super().dropEvent(event)

        selection = self.selectedIndexes()
        from_index = selection[0].row() if selection else -1
        to_index = self.indexAt(event.pos()).row()
        if (0 <= from_index < self.model().rowCount() and
            0 <= to_index < self.model().rowCount() and
            from_index != to_index):
            self.model().relocateRow(from_index, to_index)
            event.accept()
        super().dropEvent(event)
    
    def open_context_menu(self, position: QPoint):
        # 新規ページはスルー
        #selected_index = self.currentIndex()
        #if selected_index.isValid():
        #    row = selected_index.row()
        #    leftfile = self.model().item(row, 0).text()
        #    if leftfile in ["left.png", "right.png"]:
        #        return
        # 右クリックメニュー作成
        print("IN")
        menu = QMenu()
        delete_action = menu.addAction("削除")
        delete_action.triggered.connect(self.delete_selected_row)
        menu.exec_(self.viewport().mapToGlobal(position))
    
    def delete_selected_row(self):
        selected_index = self.currentIndex()
        if selected_index.isValid():
            row = selected_index.row()
            self.model().removeRow(row)
            if row > 0:
                self.selectRow(row - 1)
            elif self.model().rowCount() > 0:
                self.selectRow(row)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        model = self.model()
        row = index.row()
        leftfile = model.data(model.index(row, 0), QtCore.Qt.DisplayRole)
        if leftfile == "left.png":
            return
        filename = leftfile.replace('left', '{left | right}').replace('_thumnail', '')
        menu = QtWidgets.QMenu(self)
        info_action = menu.addAction(filename)
        delete_action = menu.addAction("見開き2ページ削除")
        
        action = menu.exec_(self.viewport().mapToGlobal(position))

        if action == delete_action:
            self.remove_row(row)

    def remove_row(self, row):
        self.model().removeRow(row)

# コンボボックス選択肢モデル作成
def get_combobox_model(disableIndex=[]):
    model = QStandardItemModel()
    for index, item in enumerate(["カメラ0", "カメラ1", "オリジナル画像", "無効化(黒画像)", "変換済み画像"]):
        item = QStandardItem(item)
        if index in disableIndex:
            item.setEnabled(False)
        model.appendRow(item)
    return model


# 書籍情報を取得
def load_book_info(bookid):
    # 書籍フォルダ
    book_dir = os.path.join(".", "BookShelf", bookid)
    # 書籍情報読み取り
    json_file = os.path.join(book_dir, "bookinfo.json")
    with open(json_file,'r', encoding="utf-8") as f:
        bookInfo = json.load(f)
    return bookInfo


# 本棚ページ
class BookEditPage(QWidget):
    # 初期化
    def __init__(self, bookid):
        # 初期化
        super().__init__()
        
        # 書籍ID
        self.bookid = bookid
        
        # 書籍情報読み取り
        self.bookinfo = load_book_info(bookid)
        
        # 書籍情報、カバー撮影モード変更ボタン
        self.infoCoverButton = QPushButton("書籍情報\nカバー設定")
        self.infoCoverButton.setFixedHeight(70)
        self.infoCoverButton.clicked.connect(self.on_infoCoverButton_clicked)
        
        # 見開きプレビューテーブル
        self.thumbnailTable = ThumbnailTableView()
        
        # 無効化時に灰色にするためのスタイルシートを設定
        self.thumbnailTable.setStyleSheet("""
            QTableView:disabled {
                background-color: lightgray;
                color: gray;
            }""")
        
        # 撮影済みファイル一覧
        book_dir = os.path.join(".", "BookShelf", bookid)
        thumbnails = [(f"{prefix}_left_thumnail.jpg",  os.path.join(book_dir, f"{prefix}_left_thumnail.jpg"),
                       f"{prefix}_right_thumnail.jpg", os.path.join(book_dir, f"{prefix}_right_thumnail.jpg")) \
                     for prefix in self.bookinfo["ordered"]]
        # カメラプレビュー追加
        thumbnails.append(("left.png",  os.path.join(".", "Resource", "left.png"),
                           "right.png", os.path.join(".", "Resource", "right.png")))
        
        # 見開きプレビュー要素モデル
        self.thumbnailModel = ThumbnailTableModel(thumbnails)
        self.thumbnailTable.setModel(self.thumbnailModel)
        
        # サムネイル配置用デリゲート
        delegate = ThumbnailDelegate()
        self.thumbnailTable.setItemDelegateForColumn(1, delegate)
        self.thumbnailTable.setItemDelegateForColumn(3, delegate)
        
        # 行高さ設定
        for row in range(len(thumbnails)):
            self.thumbnailTable.setRowHeight(row, hrow)
        
        # 列幅設定
        #width = int(hicon*0.8*2)
        #self.thumbnailTable.setFixedWidth(width)
        # 1列目の幅を設定
        #self.thumbnailTable.setColumnWidth(0, width//2)
        # 2列目の幅を自動調整
        #self.thumbnailTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # 列幅調整
        self.adjust_column_widths()
        
        # 列の非表示設定
        self.thumbnailTable.hideColumn(0)
        self.thumbnailTable.hideColumn(2)
        
        # 行番号非表示
        self.thumbnailTable.verticalHeader().setVisible(False)
        
        # 行クリック時の動作
        self.thumbnailTable.clicked.connect(self.on_thumbnailtable_clicked)
        
        # 最終行を初期選択にしておく
        last_row = self.thumbnailModel.rowCount() - 1
        last_index = self.thumbnailModel.index(last_row, 0)
        self.thumbnailTable.selectRow(last_row)
        self.thumbnailTable.scrollTo(last_index)
        
        # 左コンボボックス
        self.leftComboBox = QComboBox()
        self.leftComboBox.setFixedWidth(200)
        model = get_combobox_model([2,4])
        self.leftComboBox.setModel(model)
        self.leftComboBox.setCurrentIndex(0)
        self.leftComboBox.currentIndexChanged.connect(self.on_leftcombobox_changed)

        # 右コンボボックス
        self.rightComboBox = QComboBox()
        self.rightComboBox.setFixedWidth(200)
        model = get_combobox_model([2,4])
        self.rightComboBox.setModel(model)
        self.rightComboBox.setCurrentIndex(1)
        self.rightComboBox.currentIndexChanged.connect(self.on_rightcombobox_changed)

        # 撮影ボタン
        self.shutterButton = QPushButton("")
        self.shutterButton.setIcon(QIcon("./Resource/shutter.png"))
        self.shutterButton.clicked.connect(self.on_shutterbutton_clicked)
        
        # 左ページプレビュー
        self.leftPagePreview = CustomQImageViewer("./Resource/left.png")
        self.leftPagePreview.hide()
        
        # 右ページプレビュー
        self.rightPagePreview = CustomQImageViewer("./Resource/right.png")
        self.rightPagePreview.hide()
        
        # 左カメラプレビュー
        self.leftCameraPreview = CustomQCameraPreview(picam2s[0])
        
        # 右カメラプレビュー
        self.rightCameraPreview = CustomQCameraPreview(picam2s[1])
        
        # 左ページ画像変換ビュー
        #self.leftTransform = CustomQImageViewer2()
        #self.leftTransform.hide()
        
        # 右ページ画像変換ビュー
        #self.rightTransform = CustomQImageViewer2()
        #self.rightTransform.hide()
        
        # 書籍情報入力フォーム
        bookinfo = os.path.join(".", "BookShelf", self.bookid, 'bookinfo.json')
        self.bookInfoForm = CustomQBookInfoForm(bookinfo)

        # バーコード読み取りボタン
        self.isbnButton = QPushButton("バーコードから読み取り")
        self.isbnButton.clicked.connect(self.on_isbnButton_clicked)
        
        # 表紙or裏表紙の撮影区分
        self.coverComboBox = QComboBox()
        self.coverComboBox.addItems(['表紙設定', '裏表紙設定'])
        
        # 書籍情報の設定Widget
        self.bookInfoSetting = QWidget()
        self.bookInfoSetting.hide()
        
        # 書籍情報設定用のレイアウト
        bookSettingVLayout = QVBoxLayout()
        self.bookInfoSetting.setLayout(bookSettingVLayout)
        
        # 表紙or裏表紙の撮影区分
        bookSettingVLayout.addWidget(self.coverComboBox)

        # バーコード読み取りボタン
        bookSettingVLayout.addWidget(self.isbnButton)

        # 書籍情報入力フォーム
        bookSettingVLayout.addWidget(self.bookInfoForm)
    
        # Widget配置
        # 最上位水平レイアウト
        topHBoxLayout = QHBoxLayout()
        self.setLayout(topHBoxLayout)

        # 左半分Widget
        leftWidget = QWidget()
        topHBoxLayout.addWidget(leftWidget)
        topHBoxLayout.setStretch(0, 0)
        
        # 垂直レイアウト
        leftVBoxLayout = QVBoxLayout()
        leftWidget.setLayout(leftVBoxLayout)
        
        # 書籍情報とカバー撮影
        leftVBoxLayout.addWidget(self.infoCoverButton)
        
        # 見開きプレビュー一覧
        leftVBoxLayout.addWidget(self.thumbnailTable)
                
        # 右半分Widget
        rightWidget = QWidget()
        topHBoxLayout.addWidget(rightWidget)
        topHBoxLayout.setStretch(1, 1)
        
        # 垂直レイアウト
        rightVBoxLayout = QVBoxLayout()
        rightWidget.setLayout(rightVBoxLayout)
        
        # コントロール類Widget
        ctrlWidget = QWidget()
        ctrlWidget.setFixedHeight(60)
        rightVBoxLayout.addWidget(ctrlWidget)
        # 水平レイアウト
        ctrlHBoxLayout = QHBoxLayout()
        ctrlWidget.setLayout(ctrlHBoxLayout)
        # 左コンボボックス
        ctrlHBoxLayout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        ctrlHBoxLayout.addWidget(self.leftComboBox)
        # 撮影ボタン
        ctrlHBoxLayout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        ctrlHBoxLayout.addWidget(self.shutterButton)
        ctrlHBoxLayout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        # 右コンボボックス
        ctrlHBoxLayout.addWidget(self.rightComboBox)
        ctrlHBoxLayout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # プレビューWidget
        previewWidget = QWidget()
        rightVBoxLayout.addWidget(previewWidget)
        
        # 水平レイアウト
        previewHBoxLayout = QHBoxLayout()
        previewWidget.setLayout(previewHBoxLayout)
        
        # 左ページプレビュー
        previewHBoxLayout.addWidget(self.leftPagePreview)
        previewHBoxLayout.addWidget(self.leftCameraPreview)
        previewHBoxLayout.addWidget(self.bookInfoSetting)
        
        # 右ページプレビュー
        previewHBoxLayout.addWidget(self.rightPagePreview)
        previewHBoxLayout.addWidget(self.rightCameraPreview)
        
        # カメラプレビュー回転用タイマ
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera_preview)
        self.timer.start(30)


    # 見開きプレビューテーブルの行をクリック時の動作
    def on_thumbnailtable_clicked(self, index: QModelIndex):
        # 行番号
        row = index.row()
        # 各種Widget更新
        # 左ファイル名
        leftfile = self.thumbnailModel.data(self.thumbnailModel.index(row, 0), QtCore.Qt.DisplayRole)
        # 既存ページの場合
        if leftfile not in ["left.png", "right.png"]:
            # 左コンボボックス
            # 選択肢クリア
            self.leftComboBox.clear()
            model = get_combobox_model([0, 1, 3])
            self.leftComboBox.setModel(model)
            # オリジナル画像をデフォルトに設定
            self.leftComboBox.setCurrentIndex(2)
            # 左ファイルパス
            leftfile = os.path.join(".", "BookShelf", self.bookid, leftfile.replace('thumnail', 'original'))
            # 左ページプレビュー更新
            self.leftPagePreview.reset_image(leftfile)
            # 表示、非表示
            self.leftPagePreview.show()
            self.leftCameraPreview.hide()
        else:
            # 新規ページの場合
            # 左コンボボックス
            # 選択肢クリア
            self.leftComboBox.clear()
            model = get_combobox_model([2])
            self.leftComboBox.setModel(model)
            # カメラプレビュー表示
            self.leftPagePreview.hide()
            self.leftCameraPreview.show()
            
        # 右ファイル名
        rightfile = self.thumbnailModel.data(self.thumbnailModel.index(row, 2), QtCore.Qt.DisplayRole)
        if rightfile not in ["left.png", "right.png"]:
            # 右コンボボックス
            # 選択肢クリア
            self.rightComboBox.clear()
            model = get_combobox_model([0, 1, 3])
            self.rightComboBox.setModel(model)
            # オリジナル画像をデフォルトに設定
            self.rightComboBox.setCurrentIndex(2)
            # 右ファイルパス
            rightfile = os.path.join(".", "BookShelf", self.bookid, rightfile.replace('thumnail', 'original'))
            # 右ページプレビュー更新
            self.rightPagePreview.reset_image(rightfile)
            # 表示、非表示
            self.rightPagePreview.show()
            self.rightCameraPreview.hide()
        else:
            # 右コンボボックス
            # 選択肢クリア
            self.rightComboBox.clear()
            model = get_combobox_model([2])
            self.rightComboBox.setModel(model)
            self.rightComboBox.setCurrentIndex(1)
            # カメラプレビュー表示
            self.rightPagePreview.hide()
            self.rightCameraPreview.show()
            
        # シャッターボタン設定
        if leftfile =="left.png" or rightfile == "right.png":
            self.shutterButton.setEnabled(True)
        else:
            self.shutterButton.setEnabled(False)

        # 書籍情報json更新
        self.update_bookinfo_ordered()


    # 左コンボボックス選択変更時の動作
    def on_leftcombobox_changed(self, index):
        # カメラ0、カメラ1
        if index in [0, 1]:
            self.leftCameraPreview.camera = picam2s[index]
        
        # オリジナル画、変換済み画像
        if index in [2, 4]:
            # 見開きプレビューの選択行
            selection_model = self.thumbnailTable.selectionModel()
            selected_indexes = selection_model.selectedRows()
            if selected_indexes:
                 # 左ファイル名
                filename = None
                
                # 先頭の選択行のみ対象で
                row = selected_indexes[0].row()
                model = self.thumbnailTable.model()
                filename = model.data(model.index(row, 0), QtCore.Qt.DisplayRole)
            
                # 左ファイルパス
                leftfile = os.path.join(".", "BookShelf", self.bookid, filename)
                                
                # オリジナル画像の場合
                if index == 2:
                    leftfile = leftfile.replace('_thumnail', '_original')
                
                # 変換済み画像の場合
                if index == 4:
                    leftfile = leftfile.replace('_thumnail', '_transformed')
                    if not os.path.exists(leftfile):
                        file_org = leftfile.replace('_transformed', '_original')
                        image_org = cv2.imread(file_org)
                        image_trans = ImageTransform.transform(image_org, configfiles[0])
                        cv2.imwrite(leftfile, image_trans)
                
                # 左ページプレビュー更新
                self.leftPagePreview.reset_image(leftfile)
            else:
                # 行選択できていない場合スルー
                return
        
        # ブランク画像
        if index == 3:
            # 左ファイルパス
            leftfile = os.path.join(".", "Resource", "left.png")
            # 左ページプレビュー更新
            self.leftPagePreview.reset_image(leftfile)
        
        # 非表示、表示切り替え
        if index in [0, 1]:
            self.leftCameraPreview.show()
            self.leftPagePreview.hide()
        elif index in [2, 3, 4]:
            # 非表示、表示切り替え
            self.leftCameraPreview.hide()
            self.leftPagePreview.show()


    # 右コンボボックス選択変更時の動作
    def on_rightcombobox_changed(self, index):
        # カメラ0、カメラ1
        if index in [0, 1]:
            self.rightCameraPreview.camera = picam2s[index]
            
        # オリジナル画像、変換済み画像
        if index in [2, 4]:
            # 見開きプレビューの選択行
            selection_model = self.thumbnailTable.selectionModel()
            selected_indexes = selection_model.selectedRows()
            if selected_indexes:
                 # 右ファイル名
                filename = None
                
                # 先頭の選択行のみ対象で
                row = selected_indexes[0].row()
                model = self.thumbnailTable.model()
                filename = model.data(model.index(row, 2), QtCore.Qt.DisplayRole)
            
                # 左ファイルパス
                rightfile = os.path.join(".", "BookShelf", self.bookid, filename)
                
                # オリジナル画像の場合
                if index == 2:
                    rightfile = rightfile.replace('_thumnail', '_original')
                
                # 変換済み画像の場合
                if index == 4:
                    rightfile = rightfile.replace('_thumnail', '_transformed')
                    if not os.path.exists(rightfile):
                        file_org = rightfile.replace('_transformed', '_original')
                        image_org = cv2.imread(file_org)
                        image_trans = ImageTransform.transform(image_org, configfiles[1])
                        cv2.imwrite(rightfile, image_trans)
                
                # 右ページプレビュー更新
                self.rightPagePreview.reset_image(rightfile)
            else:
                # 行選択できていない場合スルー
                return

        # ブランク画像
        if index == 3:
            # 右ファイルパス
            rightfile = os.path.join(".", "Resource", "right.png")
            # 右ページプレビュー更新
            self.rightPagePreview.reset_image(rightfile)

        # 非表示、表示切り替え
        if index in [0, 1]:
            self.rightCameraPreview.show()
            self.rightPagePreview.hide()
        elif index in [2, 3, 4]:
            # 非表示、表示切り替え
            self.rightCameraPreview.hide()
            self.rightPagePreview.show()


    # 右コンボボックス選択変更時の動作
    # 書籍情報設定時
    def on_rightcombobox_changed2(self, index):
        # カメラ0、カメラ1
        if index in [0, 1]:
            self.rightCameraPreview.camera = picam2s[index]

        # オリジナル画像、変換済み画像
        if index in [2, 4]:
            # 表紙or裏表紙
            cover = 'front' if self.coverComboBox.currentIndex()==0 else 'back'
            
            # ファイルパス
            rightfile = os.path.join(".", "BookShelf", self.bookid, f"{cover}_original.jpg")
            
            # 変換済み画像の場合
            if index == 4:
                rightfile = rightfile.replace('_original', '_transformed')
                if not os.path.exists(rightfile):
                    file_org = rightfile.replace('_transformed', '_original')
                    image_org = cv2.imread(file_org)
                    image_trans = ImageTransform.transform(image_org, configfiles[1])
                    cv2.imwrite(rightfile, image_trans)
            
            # 右ページプレビュー更新
            self.rightPagePreview.reset_image(rightfile)
        
        # ブランク画像
        if index == 3:
            # 右ファイルパス
            rightfile = os.path.join(".", "Resource", "right.png")
            # 右ページプレビュー更新
            self.rightPagePreview.reset_image(rightfile)

        # 非表示、表示切り替え
        if index in [0, 1]:
            self.rightCameraPreview.show()
            self.rightPagePreview.hide()
            self.shutterButton.setEnabled(True)
        elif index in [2, 3, 4]:
            # 非表示、表示切り替え
            self.rightCameraPreview.hide()
            self.rightPagePreview.show()
            self.shutterButton.setEnabled(False)


    # シャッターボタンクリック時の動作
    def on_shutterbutton_clicked(self):
        # タイムスタンプ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ファイル形式はいったんJPG固定
        filetype = "jpg"

        # 左ページについて
        leftfile = os.path.join(".", "BookShelf", self.bookid, timestamp + f"_left_original.{filetype}")
        
        # カメラ0, 1
        if self.leftComboBox.currentIndex() in [0, 1]:
            # カメラ番号
            camid = self.leftComboBox.currentIndex()
            # 静止画撮影
            picam2s[camid].switch_mode_and_capture_file(piconfigs[camid]["still"], leftfile)
            # 回転変換
            qimage = QImage(leftfile)
            rotate_angle = self.leftCameraPreview.rotation_angle
            transform = QTransform().rotate(rotate_angle)
            qimage = qimage.transformed(transform)
            # オリジナル画像を保存
            qimage.save(leftfile, 'JPEG', quality=100)
            # サムネイル画像
            thum_height = 400
            thum_width = int(thum_height * qimage.width() / qimage.height())
            qthum = qimage.scaled(thum_width, thum_height, aspectRatioMode=Qt.KeepAspectRatio)
            qthum.save(leftfile.replace('original', 'thumnail'), 'JPEG', quality=100)
            # 変換済み画像
            image_org = cv2.imread(leftfile)
            imaeg_trans = ImageTransform.transform(image_org, configfiles[camid])
            cv2.imwrite(leftfile.replace('original', 'transformed'), imaeg_trans)
        # ブランク画像
        elif self.leftComboBox.currentIndex() == 3:
            # ブランク画像をコピー
            leftblank = os.path.join(".", "Resource", "left.png")
            shutil.copy(leftblank, leftfile)
            shutil.copy(leftblank, leftfile.replace('original', 'thumnail'))
        
        # 右ページについて
        rightfile = os.path.join(".", "BookShelf", self.bookid, timestamp + f"_right_original.{filetype}")
        
        # カメラ0, 1
        if self.rightComboBox.currentIndex() in [0, 1]:
            # カメラ番号
            camid = self.rightComboBox.currentIndex()
            # 静止画撮影
            picam2s[camid].switch_mode_and_capture_file(piconfigs[camid]["still"], rightfile)
            # 回転変換
            qimage = QImage(rightfile)
            rotate_angle = self.rightCameraPreview.rotation_angle
            transform = QTransform().rotate(rotate_angle)
            qimage = qimage.transformed(transform)
            # オリジナル画像を保存
            qimage.save(rightfile, 'JPEG', quality=100)
            # サムネイル画像
            thum_height = 400
            thum_width = int(thum_height * qimage.width() / qimage.height())
            qthum = qimage.scaled(thum_width, thum_height, aspectRatioMode=Qt.KeepAspectRatio)
            qthum.save(rightfile.replace('original', 'thumnail'), 'JPEG', quality=100)
            # 変換済み画像
            image_org = cv2.imread(rightfile)
            imaeg_trans = ImageTransform.transform(image_org, configfiles[camid])
            cv2.imwrite(rightfile.replace('original', 'transformed'), imaeg_trans)
        # ブランク画像
        if self.rightComboBox.currentIndex() == 3:
            # ブランク画像をコピー
            rightblank = os.path.join(".", "Resource", "right.png")
            shutil.copy(rightblank, rightfile)
            shutil.copy(rightblank, rightfile.replace('original', 'thumnail'))
        
        # 見開きプレビューへ追加
        selected_index = self.thumbnailTable.currentIndex()
        row = selected_index.row() if selected_index.isValid() else self.model.rowCount()
        leftfile = leftfile.replace('original', 'thumnail')
        leftname = os.path.basename(leftfile)
        rightfile = rightfile.replace('original', 'thumnail')
        rightname = os.path.basename(rightfile)
        self.thumbnailModel.insertRow(row, leftname, leftfile, rightname, rightfile)
        # 行の高さを再設定
        self.thumbnailTable.setRowHeight(row, hrow)

        # 書籍情報json更新
        self.update_bookinfo_ordered()
        
        # 新規ページを選択中にしておく
        # どうも位置が近いと移動しない
        # 一旦選択行の番号を保存
        selected_index = self.thumbnailTable.currentIndex()
        row = selected_index.row() if selected_index.isValid() else self.model.rowCount() 
        # 先頭へ強制移動
        last_row = 0 
        last_index = self.thumbnailModel.index(last_row, 0)
        self.thumbnailTable.selectRow(last_row)
        self.thumbnailTable.scrollTo(last_index, QAbstractItemView.PositionAtBottom)    
        # 選択行へ移動
        last_row = row 
        last_index = self.thumbnailModel.index(last_row, 0)
        self.thumbnailTable.selectRow(last_row)
        self.thumbnailTable.scrollTo(last_index, QAbstractItemView.PositionAtBottom)
        
        # シャッター音
        # どうも初回の音がでない？
        se = os.path.join('.', 'Resource', 'shutter.mp3')
        playsound(se)


    # 書籍情報(ページ並び順)の更新
    def update_bookinfo_ordered(self):
        # 書籍フォルダ
        book_dir = os.path.join(".", "BookShelf", self.bookid)
        # 書籍情報読み取り
        json_file = os.path.join(book_dir, "bookinfo.json")
        with open(json_file,'r', encoding="utf-8") as f:
            bookInfo = json.load(f)
        self.bookinfo = bookInfo
        
        # 書籍情報json更新
        ordered = []
        for row in range(self.thumbnailModel.rowCount()):
            leftfile = self.thumbnailModel.data(self.thumbnailModel.index(row, 0), QtCore.Qt.DisplayRole)
            filename = os.path.basename(leftfile)
            prefix = os.path.splitext(filename)[0].replace("_left_thumnail", "")
            if prefix in ["left", "right"]:
                continue
            ordered.append(prefix)
        self.bookinfo["ordered"] = ordered
        
        # 更新日時
        moddate = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.bookinfo["moddate"] = moddate
         
        # 書籍情報更新
        book_dir = os.path.join(".", "BookShelf", self.bookid)
        json_file = os.path.join(book_dir, "bookinfo.json")
        with open(json_file, 'w') as fout:
            json.dump(self.bookinfo, fout, indent=4)


    # シャッターボタンクリック時の動作
    # 書籍情報設定時
    def on_shutterbutton_clicked2(self):
        # ファイル名
        filename = 'front_original.jpg' if self.coverComboBox.currentIndex() == 0 else 'back_original.jpg'
        filename = os.path.join(".", "BookShelf", self.bookid, filename)
        
        # 上書き確認
        ans = yes_no_dialog()
        if ans == False:
            return

        # カメラ番号
        camid = self.rightComboBox.currentIndex()
        # 静止画撮影
        picam2s[camid].switch_mode_and_capture_file(piconfigs[camid]["still"], filename)
        # 回転変換
        qimage = QImage(filename)
        rotate_angle = self.rightCameraPreview.rotation_angle
        transform = QTransform().rotate(rotate_angle)
        qimage = qimage.transformed(transform)
        # 上書き保存
        qimage.save(filename, 'JPEG', quality=100)
        
        # サムネイル画像
        thum_height = 400
        thum_width = int(thum_height * qimage.width() / qimage.height())
        qthum = qimage.scaled(thum_width, thum_height, aspectRatioMode=Qt.KeepAspectRatio)
        qthum.save(filename.replace('original', 'thumnail'), 'JPEG', quality=100)
        
        # 変換済み画像
        image_org = cv2.imread(filename)
        imaeg_trans = ImageTransform.transform(image_org, configfiles[camid])
        cv2.imwrite(filename.replace('original', 'transformed'), imaeg_trans)
        
        # シャッター音
        se = os.path.join('.', 'Resource', 'shutter.mp3')
        playsound(se)


    # 見開きプレビューの列幅調整
    def adjust_column_widths(self):
        # 列幅をサムネイルの幅に基づいて設定
        total_width = 0
        for col in [1, 3]:
            max_width = 0
            for row in range(self.thumbnailModel.rowCount()):
                index = self.thumbnailModel.index(row, col)
                pixmap = self.thumbnailModel.data(index, Qt.DecorationRole)
                if isinstance(pixmap, QPixmap):
                    max_width = max(max_width, pixmap.width())
            # 追加のマージンを考慮して列幅を設定
            column_width = max_width + 50
            self.thumbnailTable.setColumnWidth(col, column_width)
            total_width += column_width

        # 縦スクロールバーの幅を追加
        if self.thumbnailTable.verticalScrollBar().isVisible():
            total_width += self.thumbnailTable.verticalScrollBar().width()
            
        # テーブル全体の幅を設定
        self.thumbnailTable.setMinimumWidth(total_width)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_column_widths()


    def update_camera_preview(self):
        # 左カメラプレビュー回転
        camid = self.leftComboBox.currentIndex()
        if camid in [0, 1]:
            # コンフィグファイル読み込み
            config_file = configfiles[camid]
            with open(config_file,'r', encoding="utf-8") as f:
                config = json.load(f)
            
            # 回転角度
            rotate_angle = config["BasicSetting"]["RoteIndex"]*90 % 360
            
            # 回転角度が異なれば
            if rotate_angle != self.leftCameraPreview.rotation_angle:
                self.leftCameraPreview.rotate_image(rotate_angle)
        
        # 右カメラプレビュー
        camid = self.rightComboBox.currentIndex()
        if camid in [0, 1]:
            # コンフィグファイル読み込み
            config_file = configfiles[camid]
            with open(config_file,'r', encoding="utf-8") as f:
                config = json.load(f)
            
            # 回転角度
            rotate_angle = config["BasicSetting"]["RoteIndex"]*90 % 360
            
            # 回転角度が異なれば
            if rotate_angle != self.rightCameraPreview.rotation_angle:
                self.rightCameraPreview.rotate_image(rotate_angle)


    # 書籍情報ボタンクリック時の動作
    def on_infoCoverButton_clicked(self):
        # 書籍情報設定モードに変更
        if self.infoCoverButton.text() == "書籍情報\nカバー設定":
            # Widget類の表示設定
            # 書籍情報設定Widgetを表示
            self.leftPagePreview.hide()
            self.leftCameraPreview.hide()
            self.bookInfoSetting.show()
            
            # 左コンボボックス無効化
            self.leftComboBox.setEnabled(False)
            
            # 右コンボボックスの選択肢を更新
            model = get_combobox_model([0,3])
            self.rightComboBox.setModel(model)
            self.rightComboBox.setCurrentIndex(1)
            
            # 右コンボボックスのイベント関数を切り替え
            self.rightComboBox.currentIndexChanged.disconnect(self.on_rightcombobox_changed)
            self.rightComboBox.currentIndexChanged.connect(self.on_rightcombobox_changed2)
            
            # 撮影ボタンクリック時の動作を切り替え
            self.shutterButton.clicked.disconnect(self.on_shutterbutton_clicked)
            self.shutterButton.clicked.connect(self.on_shutterbutton_clicked2)
            
            # 見開きプレビュー
            self.thumbnailTable.setEnabled(False)
            
            # 見開きページスキャンモードに戻る
            self.infoCoverButton.setText('見開きページを\nスキャンする')
        
        # 見開きスキャンモードに変更
        elif self.infoCoverButton.text() == "見開きページを\nスキャンする":
            # 見開きページスキャンモードに戻る
            self.infoCoverButton.setText('書籍情報\nカバー設定')
            
            # 右コンボボックスのイベント関数を切り替え
            self.rightComboBox.currentIndexChanged.disconnect(self.on_rightcombobox_changed2)
            self.rightComboBox.currentIndexChanged.connect(self.on_rightcombobox_changed)
            
            # 撮影ボタンクリック時の動作を切り替え
            self.shutterButton.clicked.disconnect(self.on_shutterbutton_clicked2)
            self.shutterButton.clicked.connect(self.on_shutterbutton_clicked)
            
            # 見開きプレビュー有効化
            self.thumbnailTable.setEnabled(True)
            
            # Widget類の表示設定
            # 書籍情報設定Widgetを非表示
            self.bookInfoSetting.hide()
            
            # 行番号
            indexes = self.thumbnailTable.selectedIndexes()
            selected_rows = set()
            for index in indexes:
                selected_rows.add(index.row())
            row = list(selected_rows)[0]
            
            # 左ファイル名
            leftfile = self.thumbnailModel.data(self.thumbnailModel.index(row, 0), QtCore.Qt.DisplayRole)
            
            # 右ファイル名
            rightfile = self.thumbnailModel.data(self.thumbnailModel.index(row, 2), QtCore.Qt.DisplayRole)
            
            # 既存ページの場合
            if leftfile not in ["left.png", "right.png"]:
                 # 左ファイルパス
                leftfile = os.path.join(".", "BookShelf", self.bookid, leftfile)
                print(leftfile)
                # 左ページプレビュー更新
                self.leftPagePreview.reset_image(leftfile)
                # 左の画像プレビューを表示
                self.leftPagePreview.show()
                # 左のカメラプレビュー非表示
                self.leftCameraPreview.hide()
                # 右も同様
                rightfile = os.path.join(".", "BookShelf", self.bookid, rightfile)
                print(rightfile)
                self.rightPagePreview.reset_image(rightfile)
                self.rightPagePreview.show()
                self.rightCameraPreview.hide()
                
                # 左コンボボックス有効化
                self.leftComboBox.setEnabled(True)
                self.leftComboBox.clear()
                model = get_combobox_model([0, 1, 3])
                self.leftComboBox.setModel(model)
                self.leftComboBox.setCurrentIndex(2)
            
                # 右コンボボックスの選択肢を更新
                self.rightComboBox.clear()
                model = get_combobox_model([0, 1, 3])
                self.rightComboBox.setModel(model)
                self.rightComboBox.setCurrentIndex(2)
            else:
                # 左右のカメラプレビューを表示
                self.leftPagePreview.hide()
                self.leftCameraPreview.show()
                self.rightPagePreview.hide()
                self.rightCameraPreview.show()
                
                # 左コンボボックス有効化
                self.leftComboBox.setEnabled(True)
                self.leftComboBox.clear()
                model = get_combobox_model([2])
                self.leftComboBox.setModel(model)
                self.leftComboBox.setCurrentIndex(0)
            
                # 右コンボボックスの選択肢を更新
                self.rightComboBox.clear()
                model = get_combobox_model([2])
                self.rightComboBox.setModel(model)
                self.rightComboBox.setCurrentIndex(1)
        
        return 


    # ISBNボタンクリック時の動作
    def on_isbnButton_clicked(self):
        # 右コンボボックスの選択行
        index = self.rightComboBox.currentIndex()
            
        # カメラプレビューの場合
        if index in [0, 1]:
            # カメラ番号
            camid = self.rightComboBox.currentIndex()
            # 静止画撮影
            book_dir = os.path.join(".", "BookShelf", self.bookid)
            filename = os.path.join(book_dir, "tmp.jpg")
            picam2s[camid].switch_mode_and_capture_file(piconfigs[camid]["still"], filename)
            # 回転変換
            qimage = QImage(filename)
            rotate_angle = self.rightCameraPreview.rotation_angle
            transform = QTransform().rotate(rotate_angle)
            qimage = qimage.transformed(transform)
            # PIL変換
            pimage = qimage_to_pilimage(qimage)
            # 一時ファイル削除
            os.remove(filename)
        else:
            # 表紙or裏表紙
            cover = 'front' if self.coverComboBox.currentIndex()==0 else 'back'
            # オリジナルor変換済み
            post = 'original' if self.rightComboBox.currentIndex()==2 else 'transformed'
            # ファイル名
            filename = os.path.join(".", "BookShelf", self.bookid, f"{cover}_{post}.jpg")
            # 読み込み
            qimage = QImage(filename)
            # PIL変換
            pimage = qimage_to_pilimage(qimage)

        # ISBN読み取り
        isbn = [x.data.decode() for x in pyzbar.decode(pimage) if x.data.decode().startswith('97')]
        
        # 読み取り不可の場合
        if len(isbn) == 0:
            # エラーメッセージ表示
            QMessageBox.critical(self, "読み取りエラー", "バーコードの読み取りに失敗しました。", QMessageBox.Ok)
            return
        else:
            isbn = isbn[0]
        
        # 国会図書館API
        url = f'http://iss.ndl.go.jp/api/opensearch?isbn={isbn}'
        urlopen = urllib.request.urlopen(url)
        bookdata = xmltodict.parse(urlopen.read().decode('utf-8'))
        
        # 必要項目取得
        title = bookdata['rss']['channel']['item']['dc:title']
        author = bookdata['rss']['channel']['item']['author']
        publisher = bookdata['rss']['channel']['item']['dc:publisher']
        pubdate = bookdata['rss']['channel']['item']['dcterms:issued']
        isbn = isbn
        price = bookdata['rss']['channel']['item']['dcndl:price']
        pages = bookdata['rss']['channel']['item']['dc:extent']
        moddate = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 書籍json更新
        # JSONファイル読み取り
        json_file = os.path.join(".", "BookShelf", self.bookid, 'bookinfo.json')
        with open(json_file,'r', encoding="utf-8") as f:
            bookinfo = json.load(f)
        # 項目更新
        bookinfo['isbn'] = isbn
        bookinfo['title'] = title
        bookinfo['author'] = author
        bookinfo['publisher'] = publisher
        bookinfo['pubdate'] = pubdate
        bookinfo['price'] = price
        bookinfo['pages'] = pages
        bookinfo['moddate'] = moddate
        # 上書き保存
        with open(json_file, 'w', encoding='utf-8') as fout:
            json.dump(bookinfo, fout, ensure_ascii=False, indent=4)
        
        # 書籍情報入力フォームの更新
        self.bookInfoForm.update(bookinfo)
        
