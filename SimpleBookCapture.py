import sys
import os

# Qt関係
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QTabWidget, QFrame
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout
from PyQt5.QtWidgets import QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QPainter, QPalette

# 各種ページクラス
from CameraSettingPage import CameraSettingPage
from BookShelfPage import BookShelfPage
from BookEditPage import BookEditPage


class SimpleBookCapture(QWidget):
    def __init__(self):
        # 初期化
        super().__init__()
        
        # メインWindow初期設定
        self.resize(int(1920*3/4), int(1080*3/4))
        self.move(100, 100)
        self.setWindowTitle('Simple Book Capture Ver.0.0.1')
        self.show()
        
        # Top垂直レイアウト
        topVBoxLayout = QVBoxLayout()
        self.setLayout(topVBoxLayout)
    
        # 最上位タブ
        self.topTabs = QTabWidget(self)
        topVBoxLayout.addWidget(self.topTabs)    
        
        # カメラ設定ページ
        settingPage = CameraSettingPage()
        self.topTabs.addTab(settingPage, "カメラ設定")

        # 本棚ページ
        bookShelfPage = BookShelfPage()
        self.topTabs.addTab(bookShelfPage, "ライブラリ")


    # 書籍編集ページ作成
    def add_bookEditPage(self, bookid):
        # 既存タブがないか確認
        for itab in range(self.topTabs.count()):
            title = self.topTabs.tabText(itab)
            if title == bookid:
                self.topTabs.setCurrentIndex(itab)
                return
        # 開いていない場合は新規で作成
        bookEditPage = BookEditPage(bookid)
        self.topTabs.addTab(bookEditPage, bookid)
        # 最終タブアクティブ化
        itab = self.topTabs.count() - 1
        self.topTabs.setCurrentIndex(itab)


    # 書籍編集ページ削除
    def del_bookEditPage(self, bookid):
        # 既存タブ検索
        for itab in range(self.topTabs.count()):
            title = self.topTabs.tabText(itab)
            if title == bookid:
                self.topTabs.removeTab(itab)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon = os.path.join('.', 'Resource', 'icon.png')
    app.setWindowIcon(QIcon(icon))
    ew = SimpleBookCapture()    
    sys.exit(app.exec_())
