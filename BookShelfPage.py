import os, glob, shutil
import json
import numpy as np

# Qt関係
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox
from PyQt5.QtWidgets import QTabWidget, QFrame
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout, QSplitter
from PyQt5.QtWidgets import QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, QSpinBox
from PyQt5.QtWidgets import QTextEdit, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QColor
from PyQt5.QtCore import QAbstractTableModel, QVariant, QSize
from PyQt5.QtWidgets import QTableView, QStyledItemDelegate, QHeaderView, QAbstractItemView, QStyle
# カスタムWidget
from CustomQBookPreview import CustomQBookPreview
from CustomQWidgets import yes_no_dialog
from CustomQDialog import FileFolderDialog

# 書籍一覧テーブル用モデル
class BookTableModel(QAbstractTableModel):
    def __init__(self, books):
        super(BookTableModel, self).__init__()
        self.books = books
        self.headers = ["書籍ID", "サムネイル", "タイトル", "著者", "出版社", "出版年月", "更新時間"]

    def rowCount(self, parent=None):
        return len(self.books)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        book = self.books[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return book['id']
            elif index.column() == 2:
                return book['title']
            elif index.column() == 3:
                return book['author']
            elif index.column() == 4:
                return book['publisher']
            elif index.column() == 5:
                return book['pubdate']
            elif index.column() == 6:
                return book['moddate']
        elif role == Qt.DecorationRole:
            if index.column() == 1:
                pixmap = QPixmap(book['thumbnail'])
                return pixmap.scaledToHeight(80, Qt.SmoothTransformation)

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
        return QVariant()


# サムネイル調整
class ThumbnailDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 選択されている場合の背景色を設定
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QBrush(QColor("#3399FF")))


        if index.column() == 1 and index.data(Qt.DecorationRole):
            pixmap = index.data(Qt.DecorationRole)
            # サムネイルを中央に配置
            x = option.rect.x() + (option.rect.width() - pixmap.width()) // 2
            y = option.rect.y() + (option.rect.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        else:
            super(ThumbnailDelegate, self).paint(painter, option, index)

    def sizeHint(self, option, index):
        if index.column() == 1:
            return QSize(100, 100)  # 高さ100pxに設定
        return super(ThumbnailDelegate, self).sizeHint(option, index)


# 書籍情報テーブル用モデル
class BookInfoModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.original_data = data
        self.headers = list(data[0].keys())
        self.transposed_data = self.transpose_data(data)

    def rowCount(self, parent=None):
        return len(self.headers)

    def columnCount(self, parent=None):
        return len(self.original_data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.transposed_data[index.row()][index.column()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return f"書籍 {section + 1}"
            elif orientation == Qt.Vertical:
                return self.headers[section]
        return None

    def transpose_data(self, data):
        keys = data[0].keys()
        transposed_data = [[str(book[key]) for book in data] for key in keys]
        return transposed_data


    def update_data(self, new_data):
        self.beginResetModel()
        self.original_data = new_data
        self.headers = list(new_data[0].keys())
        self.transposed_data = self.transpose_data(new_data)
        self.endResetModel()


# 本棚からすべての書籍情報を取得
def load_book_infos():
    # 書籍一覧
    book_infos = []
    for book_dir in sorted(glob.glob(os.path.join(".", "BookShelf", '*'))):
        # 書籍情報読み取り
        json_file = os.path.join(book_dir, "bookinfo.json")
        with open(json_file,'r', encoding="utf-8") as f:
            book_info = json.load(f)
        # サムネイル
        book_info["thumbnail"] = os.path.join(book_dir, "front_thumnail.jpg")
        # 追加
        book_infos.append(book_info)
    return book_infos


# 本棚ページ
class BookShelfPage(QWidget):
    # 初期化
    def __init__(self):
        # 初期化
        super().__init__()

        # 本棚フォルダ作成
        bookshelf =os.path.join(".", "BookShelf")
        if os.path.exists(bookshelf)==False:
            os.mkdir(bookshelf)

        # 新規作成ボタン
        newBookButton = QPushButton("新規作成")
        newBookButton.clicked.connect(self.on_newbutton_clicked)
        
        # 既存編集ボタン
        editBookButton = QPushButton("既存編集")
        editBookButton.clicked.connect(self.on_editBookButton_clicked)

        # 既存削除ボタン
        deleteBookButton = QPushButton("既存削除")
        deleteBookButton.clicked.connect(self.on_deleteBookButton_clicked)
        
        # エクスポートボタン
        exportBookButton = QPushButton("エクスポート")
        exportBookButton.clicked.connect(self.on_exportBookButton_clicked)

        # 検索ボックス
        searchEditBox = QLineEdit(self)
        searchEditBox.setPlaceholderText('タイトルを入力....')
        searchEditBox.setEnabled(False)

        # 検索ボタン
        searchBookButton = QPushButton("検索")
        searchBookButton.setIcon(QIcon("./Resource/serach.png"))

        # 更新ボタン
        reloadButton = QPushButton("更新")
        reloadButton.setIcon(QIcon("./Resource/reset.png"))
        reloadButton.clicked.connect(self.reload_bookshelf)
        
        # 書籍一覧テーブル
        self.bookShelf = QTableView()
        
        # 書籍情報一覧の読み込み
        self.book_infos = load_book_infos()
        
        # 書籍モデル
        self.books = BookTableModel(self.book_infos)
        
        # 書籍モデルセット
        self.bookShelf.setModel(self.books)
        
        # デリゲートを設定
        delegate = ThumbnailDelegate()
        self.bookShelf.setItemDelegateForColumn(1, delegate)
        # 行の高さを設定
        self.bookShelf.verticalHeader().setDefaultSectionSize(100)
        self.bookShelf.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # 列幅設定
        self.bookShelf.setColumnWidth(2, 250)
        self.bookShelf.setColumnWidth(3, 150)
        
        # 行クリック時の動作
        self.bookShelf.selectionModel().selectionChanged.connect(self.bookself_selection_changed)
        self.current_selected_row = -1

        # 行選択モードの設定
        self.bookShelf.setSelectionBehavior(QTableView.SelectRows)
        self.bookShelf.setSelectionMode(QAbstractItemView.SingleSelection)

        # オリジナルor変換済み画像の選択
        self.imageComboBox = QComboBox()
        self.imageComboBox.addItem("オリジナル画像")
        self.imageComboBox.addItem("変換済み画像")
        self.imageComboBox.setCurrentIndex(0)
        self.imageComboBox.currentIndexChanged.connect(self.on_imageComboBox_change)

        # プレビュー画像
        blank = "./Resource/preview.png"
        self.bookPreview = CustomQBookPreview([blank])

        # 書籍情報テーブル
        self.bookInfo = QTableView()

        # 書籍情報
        bookdata = [
            {"書籍ID": "", "タイトル": "", "著者": "", "出版社": "", "出版年月": ""},
        ]
        self.bookdata = BookInfoModel(bookdata)

        # モデル設定
        self.bookInfo.setModel(self.bookdata)

        # ヘッダー非表示
        self.bookInfo.horizontalHeader().setVisible(False)
        # 列幅設定
        #self.bookInfo.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bookInfo.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        # Widget配置
        # 最上位水平レイアウト
        topHBoxLayout = QHBoxLayout()
        self.setLayout(topHBoxLayout)
 
        # 左半分Widget
        leftWidget = QWidget()
        topHBoxLayout.addWidget(leftWidget, 4)
        
        # 垂直レイアウト
        leftVBoxLayout = QVBoxLayout()
        leftWidget.setLayout(leftVBoxLayout) 
        
        # 上部コントロール類のWidget
        ctrlWidget = QWidget()
        leftVBoxLayout.addWidget(ctrlWidget)
        # 水平レイアウト
        ctrlHBoxLayout = QHBoxLayout()
        ctrlWidget.setLayout(ctrlHBoxLayout)
        # 新規作成ボタン
        ctrlHBoxLayout.addWidget(newBookButton, 1)
        # 既存編集ボタン
        ctrlHBoxLayout.addWidget(editBookButton, 1)
        # 既存削除ボタン
        ctrlHBoxLayout.addWidget(deleteBookButton, 1)
        # エクスポートボタン
        ctrlHBoxLayout.addWidget(exportBookButton, 1)
        # 検索ボックス
        ctrlHBoxLayout.addWidget(searchEditBox, 3)
        # 検索ボタン
        ctrlHBoxLayout.addWidget(searchBookButton, 1)
        # 更新ボタン
        ctrlHBoxLayout.addWidget(reloadButton, 1)

        # 書籍一覧テーブル
        leftVBoxLayout.addWidget(self.bookShelf)

        # 右半分Widget
        rightWidget = QWidget()
        topHBoxLayout.addWidget(rightWidget, 2)

        # 垂直レイアウト
        rightVBoxLayout = QVBoxLayout()
        rightWidget.setLayout(rightVBoxLayout)
       
        # 画像種類
        rightVBoxLayout.addWidget(self.imageComboBox)

        # 垂直可変分割
        rightVSplitter = QSplitter(Qt.Vertical)
        rightVBoxLayout.addWidget(rightVSplitter)
        
        # プレビュー画面
        rightVSplitter.addWidget(self.bookPreview)

        # 書籍情報テーブル
        rightVSplitter.addWidget(self.bookInfo)
        
        # 分割幅の初期設定
        rightVSplitter.setSizes([540, 270])


    # 本棚テーブルの行をクリック時の動作
    def bookself_selection_changed(self, selected, deselected):
        # 同一行で違う列のセルをクリックした場合はスルー
        if selected.indexes():
            new_selected_row = selected.indexes()[0].row()
            if new_selected_row == self.current_selected_row:
                return
        
        # 行番号
        self.current_selected_row = new_selected_row
        row = self.current_selected_row

        # 書籍ID
        book_id = self.books.data(self.books.index(row, 0), Qt.DisplayRole)

        # 書籍情報
        book_info = [book_info for book_info in self.book_infos if book_info["id"]==book_id]
        book_info = book_info[0]
        
        # 画像種類
        postfix = "original" if self.imageComboBox.currentIndex() == 0 else "transformed"
        
        # プレビュー画面更新
        book_dir = os.path.join(".", "BookShelf", book_id)
        image_paths = []
        if book_info['binder']=="left":
            image_paths = [[os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg")] \
                            for prefix in book_info['ordered']]
        else:
            image_paths = [[os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg")] \
                            for prefix in book_info['ordered']]
        if len(image_paths) != 0:
            # 一次元配列にフラット化
            image_paths = np.array(image_paths).flatten()
            # 表紙と裏表紙を追加
            image_paths = np.insert(image_paths, 0, os.path.join(book_dir, f"front_{postfix}.jpg"))
            image_paths = np.append(image_paths, os.path.join(book_dir, f"back_{postfix}.jpg"))
        else:
            image_paths = [os.path.join(book_dir, f"front_{postfix}.jpg"), os.path.join(book_dir, f"back_{postfix}.jpg")]
        self.bookPreview.reset(image_paths)
        
        # 左右綴じフラグ
        if book_info['binder']=="left":
            self.bookPreview.binder = 1
        else:
            self.bookPreview.binder = -1
            
        # 書籍情報テーブル更新
        bookdata = [
            {"書籍ID":book_info['id'], "タイトル":book_info["title"], 
             "著者":book_info["author"], "出版社":book_info['publisher'], 
             "出版年月":book_info['pubdate']}
        ]
        self.bookdata.update_data(bookdata)
    
    
    # 新規ボタンクリック時の動作
    def on_newbutton_clicked(self):
        # 新規書籍ID
        book_dirs = [os.path.basename(bookdir) for bookdir in sorted(glob.glob(os.path.join(".", "BookShelf", "*")))]
        max_book_id = int(book_dirs[-1]) if len(book_dirs)>0 else 0
        bookid = f"{max_book_id+1:04d}"
        
        # 新規書籍フォルダ作成
        book_dirs = os.path.join(".", "BookShelf", bookid)
        os.mkdir(book_dirs)
        
        # 書籍情報作成
        json_file = os.path.join(".", "Resource", "blankinfo.json")
        with open(json_file,'r', encoding="utf-8") as f:
            book_info = json.load(f)
        
        # 書籍ID
        book_info['id'] = bookid
        
        # 出力
        json_file = os.path.join(book_dirs, "bookinfo.json")
        with open(json_file, 'w') as fout:
            json.dump(book_info, fout, indent=4)
            
        # 表紙をコピー
        src = os.path.join(".", "Resource", "front.jpg")
        dst = os.path.join(book_dirs, "front_original.jpg")
        shutil.copy(src, dst)
        # サムネイル
        qimage = QImage(dst)
        thum_height = 400
        thum_width = int(thum_height * qimage.width() / qimage.height())
        qthum = qimage.scaled(thum_width, thum_height, aspectRatioMode=Qt.KeepAspectRatio)
        qthum.save(dst.replace('original', 'thumnail'), 'JPEG', quality=100)
        # 裏表紙コピー
        src = os.path.join(".", "Resource", "back.jpg")
        dst = os.path.join(book_dirs, "back_original.jpg")
        shutil.copy(src, dst) 
        # サムネイル
        qimage = QImage(dst)
        thum_height = 400
        thum_width = int(thum_height * qimage.width() / qimage.height())
        qthum = qimage.scaled(thum_width, thum_height, aspectRatioMode=Qt.KeepAspectRatio)
        qthum.save(dst.replace('original', 'thumnail'), 'JPEG', quality=100)
        
        # 書籍編集ページの立ち上げ
        # 親Wigetを辿って、書籍編集ページ立ち上げ
        current_widget = self.parentWidget()
        while current_widget is not None:
            #print(f'Widget: {current_widget.__class__.__name__}')
            if current_widget.__class__.__name__ == "SimpleBookCapture":
                current_widget.add_bookEditPage(bookid)
            current_widget = current_widget.parentWidget()
        
        # 書籍リスト更新
        self.reload_bookshelf()


    # 既存ボタンクリック時の動作
    def on_editBookButton_clicked(self):
        # 選択行からbookidを取得
        indexes = self.bookShelf.selectionModel().selectedRows()
        if indexes:
            selected_row = indexes[0].row()
            bookinfo = self.books.books[selected_row]
            bookid = bookinfo['id']
            # 書籍編集ページの立ち上げ
            # 親Wigetを辿って、書籍編集ページ立ち上げ
            current_widget = self.parentWidget()
            while current_widget is not None:
                #print(f'Widget: {current_widget.__class__.__name__}')
                if current_widget.__class__.__name__ == "SimpleBookCapture":
                    current_widget.add_bookEditPage(bookid)
                current_widget = current_widget.parentWidget()


    # 既存削除ボタンクリック時の動作
    def on_deleteBookButton_clicked(self):
        # 選択行からbookidを取得
        indexes = self.bookShelf.selectionModel().selectedRows()
        if indexes:
            selected_row = indexes[0].row()
            bookinfo = self.books.books[selected_row]
            bookid = bookinfo['id']
            
            # 削除確認のダイアログ表示 
            ans = yes_no_dialog('フォルダ削除', '書籍フォルダを削除しますか？')
            if ans ==False:
                return
            
            # 書籍フォルダを削除
            book_dir = os.path.join(".", "BookShelf", bookid)
            shutil.rmtree(book_dir)
            
            # 書籍リスト更新
            self.reload_bookshelf()
            
            # 書籍編集ページの削除
            # 親Wigetを辿って、書籍編集ページ立ち上げ
            current_widget = self.parentWidget()
            while current_widget is not None:
                #print(f'Widget: {current_widget.__class__.__name__}')
                if current_widget.__class__.__name__ == "SimpleBookCapture":
                    current_widget.del_bookEditPage(bookid)
                current_widget = current_widget.parentWidget()


    # 書籍リストの再読み込み
    def reload_bookshelf(self):
        # 書籍情報一覧の読み込み
        self.book_infos = load_book_infos()
        
        # 書籍モデル
        self.books = BookTableModel(self.book_infos)
            
        # 書籍モデルセット
        self.bookShelf.setModel(self.books)
        
        # イベント関数
        self.bookShelf.selectionModel().selectionChanged.connect(self.bookself_selection_changed)


    # エクスポートボタンクリック時の動作
    def on_exportBookButton_clicked(self):
        # 選択行の確認
        indexes = self.bookShelf.selectionModel().selectedRows()
        if len(indexes)==0:
            return
        
        # エクスポート先を選択
        dialog = FileFolderDialog()
        dialog.exec_()
        if dialog.save_path is None:
            return
        
        # 書籍ID
        selected_row = indexes[0].row()
        bookinfo = self.books.books[selected_row]
        bookid = bookinfo['id']
        
        # 一時フォルダ作成
        tmp_dir = os.path.join(".", f"tmp{bookid}")
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.mkdir(tmp_dir)
        
        # 書籍情報を再読み込み
        json_file = os.path.join(".", "BookShelf", bookid, 'bookinfo.json')
        with open(json_file,'r', encoding="utf-8") as f:
            bookinfo = json.load(f)
        
        # 画像種類
        postfix = "original" if self.imageComboBox.currentIndex() == 0 else "transformed"
        
        # ページ順のファイルパス一覧を作成
        book_dir = os.path.join(".", "BookShelf", bookid)
        image_paths = []
        if bookinfo['binder']=="left":
            image_paths = [[os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg")] \
                            for prefix in bookinfo['ordered']]
        else:
            image_paths = [[os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg")] \
                            for prefix in bookinfo['ordered']]
        if len(image_paths) != 0:
            # 一次元配列にフラット化
            image_paths = np.array(image_paths).flatten()
            # 表紙と裏表紙を追加
            image_paths = np.insert(image_paths, 0, os.path.join(book_dir, f"front_{postfix}.jpg"))
            image_paths = np.append(image_paths, os.path.join(book_dir, f"back_{postfix}.jpg"))
        else:
            image_paths = [os.path.join(book_dir, f"front_{postfix}.jpg"), os.path.join(book_dir, f"back_{postfix}.jpg")]
        
        # ページ順にりネームしてコピー
        for i, image_file in enumerate(image_paths):
            src = image_file
            filename = f"{i:04d}_" + os.path.basename(image_file)
            dst = os.path.join(tmp_dir, filename)
            shutil.copy(src, dst)
        
        # フォルダ保存の場合
        if os.path.splitext(dialog.save_path)[1] == "":
            # 一時フォルダをリネームして移動する
            src = tmp_dir
            dst = dialog.save_path
            shutil.move(src, dst)
       
        # tar指定の場合 
        elif os.path.splitext(dialog.save_path)[1] == ".tar":
            filename = os.path.basename(dialog.save_path)
            filename = os.path.splitext(filename)[0]
            shutil.make_archive(base_name=filename, format="gztar", root_dir=tmp_dir)
            shutil.rmtree(tmp_dir)
        
        # zip指定の場合 
        elif os.path.splitext(dialog.save_path)[1] == ".zip":
            filename = os.path.basename(dialog.save_path)
            filename = os.path.splitext(filename)[0]
            shutil.make_archive(base_name=filename, format="zip", root_dir=tmp_dir)
            shutil.rmtree(tmp_dir)
        
        # pdf指定の場合 
        elif os.path.splitext(dialog.save_path)[1] == ".pdf":
            import img2pdf
            from PIL import Image
            image_files = sorted(glob.glob(os.path.join(tmp_dir, "*.jpg")))
            with open(dialog.save_path, "wb") as f:
                f.write(img2pdf.convert([Image.open(image_file).filename for image_file in image_files]))
            shutil.rmtree(tmp_dir)
        
        # 完了メッセージを表示
        QMessageBox.information(self, "エクスポート完了", "処理が完了しました。")


    # 画像種類変更時の動作
    def on_imageComboBox_change(self, index):
        # 画像種類
        postfix = "original" if index == 0 else "transformed"
        
        # プレビュー画面更新
        indexes = self.bookShelf.selectionModel().selectedRows()
        selected_row = indexes[0].row()
        book_info = self.books.books[selected_row]
        book_id = book_info['id']
        book_dir = os.path.join(".", "BookShelf", book_id)
        image_paths = []
        if book_info['binder']=="left":
            image_paths = [[os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg")] \
                            for prefix in book_info['ordered']]
        else:
            image_paths = [[os.path.join(book_dir, f"{prefix}_right_{postfix}.jpg"), 
                            os.path.join(book_dir, f"{prefix}_left_{postfix}.jpg")] \
                            for prefix in book_info['ordered']]
        if len(image_paths) != 0:
            # 一次元配列にフラット化
            image_paths = np.array(image_paths).flatten()
            # 表紙と裏表紙を追加
            image_paths = np.insert(image_paths, 0, os.path.join(book_dir, f"front_{postfix}.jpg"))
            image_paths = np.append(image_paths, os.path.join(book_dir, f"back_{postfix}.jpg"))
        else:
            image_paths = [os.path.join(book_dir, f"front_{postfix}.jpg"), os.path.join(book_dir, f"back_{postfix}.jpg")]
        
        self.bookPreview.reset(image_paths)

