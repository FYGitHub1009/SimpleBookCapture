import sys
import os, json
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QWidget, QGroupBox, QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox

class CustomQBookInfoForm(QWidget):
    def __init__(self, json_file):
        super().__init__()
        self.json_file = json_file
        with open(json_file,'r', encoding="utf-8") as f:
            bookinfo = json.load(f)
        self.initUI(bookinfo)

    def initUI(self, bookinfo):
        # メインレイアウトを設定
        mainLayout = QVBoxLayout()

        # グループボックスを作成してフォームをその中に配置
        groupBox = QGroupBox('書籍情報入力フォーム')

        # スタイルシートを使用して枠の太さを設定
        groupBox.setStyleSheet("""
            QGroupBox {
                border: 2px solid black;  /* 枠線の太さと色を指定 */
                border-radius: 5px;       /* 角を少し丸める */
                margin-top: 10px;         /* タイトルと枠線の間にスペースを設ける */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; /* タイトルの位置を中央に */
                padding: 0 3px;                /* タイトルと枠線の間にスペースを設ける */
            }
        """)

        # フォームのレイアウトを作成
        formLayout = QVBoxLayout()

        # 各入力フィールドの作成
        # 書籍ID
        idLayout = QHBoxLayout()
        self.idLabel = QLabel('書籍ID')
        self.idLabel.setFixedWidth(100)
        self.idEdit = QLineEdit()
        self.idEdit.setText(bookinfo['id'])
        self.idEdit.setEnabled(False)
        idLayout.addWidget(self.idLabel)
        idLayout.addWidget(self.idEdit)
        formLayout.addLayout(idLayout)
        
        # ISBN
        isbnLayout = QHBoxLayout()
        self.isbnLabel = QLabel('ISBN')
        self.isbnLabel.setFixedWidth(100)
        self.isbnEdit = QLineEdit()
        self.isbnEdit.setText(bookinfo['isbn'])
        isbnLayout.addWidget(self.isbnLabel)
        isbnLayout.addWidget(self.isbnEdit)
        formLayout.addLayout(isbnLayout)
        
        # 書籍名
        self.titleLabel = QLabel('書籍名')
        self.titleEdit = QTextEdit()
        self.titleEdit.setText(bookinfo['title'])
        formLayout.addWidget(self.titleLabel)
        formLayout.addWidget(self.titleEdit)

        # 著者
        authorLayout = QHBoxLayout()
        self.authorLabel = QLabel('著者')
        self.authorLabel.setFixedWidth(100)
        self.authorEdit = QLineEdit()
        self.authorEdit.setText(bookinfo['author'])
        authorLayout.addWidget(self.authorLabel)
        authorLayout.addWidget(self.authorEdit)
        formLayout.addLayout(authorLayout)
        
        # 出版社
        publisherLayout = QHBoxLayout()
        self.publisherLabel = QLabel('出版社')
        self.publisherLabel.setFixedWidth(100)
        self.publisherEdit = QLineEdit()
        self.publisherEdit.setText(bookinfo['publisher'])
        publisherLayout.addWidget(self.publisherLabel)
        publisherLayout.addWidget(self.publisherEdit)
        formLayout.addLayout(publisherLayout)
        
        # 発刊日
        pubdateLayout = QHBoxLayout()
        self.dateLabel = QLabel('発刊日')
        self.dateLabel.setFixedWidth(100)
        self.dateEdit = QLineEdit()
        self.dateEdit.setText(bookinfo['pubdate'])
        pubdateLayout.addWidget(self.dateLabel)
        pubdateLayout.addWidget(self.dateEdit)
        formLayout.addLayout(pubdateLayout)

        # 左右綴じ選択のためのコンボボックスとラベルを水平レイアウトで配置
        bindLayout = QHBoxLayout()
        self.bindLabel = QLabel('左右綴じ')
        self.bindLabel.setFixedWidth(100)
        self.bindComboBox = QComboBox()
        self.bindComboBox.addItems(['左綴じ', '右綴じ'])
        index = 0 if bookinfo['binder']=='left' else 1
        self.bindComboBox.setCurrentIndex(index)
        bindLayout.addWidget(self.bindLabel)
        bindLayout.addWidget(self.bindComboBox)
        formLayout.addLayout(bindLayout)
        
        # ページ数
        pagesLayout = QHBoxLayout()
        self.pagesLabel = QLabel('ページ数')
        self.pagesLabel.setFixedWidth(100)
        self.pagesEdit = QLineEdit()
        self.pagesEdit.setText(bookinfo['pages'])
        pagesLayout.addWidget(self.pagesLabel)
        pagesLayout.addWidget(self.pagesEdit)
        formLayout.addLayout(pagesLayout)
        
        # 価格
        priceLayout = QHBoxLayout()
        self.priceLabel = QLabel('価格')
        self.priceLabel.setFixedWidth(100)
        self.priceEdit = QLineEdit()
        self.priceEdit.setText(bookinfo['price'])
        priceLayout.addWidget(self.priceLabel)
        priceLayout.addWidget(self.priceEdit)
        formLayout.addLayout(priceLayout)
        
        # 更新日時
        updateLayout = QHBoxLayout()
        self.updateLabel = QLabel('更新日時')
        self.updateLabel.setFixedWidth(100)
        self.updateEdit = QLineEdit()
        self.updateEdit.setText(bookinfo['moddate'])
        updateLayout.addWidget(self.updateLabel)
        updateLayout.addWidget(self.updateEdit)
        formLayout.addLayout(updateLayout)

        # グループボックスにフォームレイアウトをセット
        groupBox.setLayout(formLayout)

        # グループボックスをメインレイアウトに追加
        mainLayout.addWidget(groupBox)
        
        # 反映ボタン
        buttonLayout = QHBoxLayout()
        self.submitButton = QPushButton('書籍情報を上書きする')
        self.submitButton.clicked.connect(self.on_submitButton_clicked)
        mainLayout.addWidget(self.submitButton)    
        #self.submitButton.setFixedWidth(self.width() // 3)
        # 左右に空白を追加してボタンを中央に配置
        #buttonLayout.addStretch(1)
        #buttonLayout.addWidget(self.submitButton)
        #buttonLayout.addStretch(1)
        # ボタンのレイアウトをフォームレイアウトに追加
        #mainLayout.addLayout(buttonLayout)        
        
        # メインレイアウトをウィジェットに設定
        self.setLayout(mainLayout)


    # 書籍情報の更新
    def update(self, bookinfo):
        self.idEdit.setText(bookinfo['id'])
        self.isbnEdit.setText(bookinfo['isbn'])
        self.titleEdit.setText(bookinfo['title'])
        self.authorEdit.setText(bookinfo['author'])
        self.publisherEdit.setText(bookinfo['publisher'])
        self.dateEdit.setText(bookinfo['pubdate'])
        index = 0 if bookinfo['binder']=='left' else 1
        self.bindComboBox.setCurrentIndex(index)
        self.pagesEdit.setText(bookinfo['pages'])
        self.priceEdit.setText(bookinfo['price'])
        self.updateEdit.setText(bookinfo['moddate'])



    # 上書きボタンクリック時の動作
    def on_submitButton_clicked(self):
        # JSONファイル読み取り
        json_file = self.json_file
        with open(json_file,'r', encoding="utf-8") as f:
            bookinfo = json.load(f)
        
        # ISBN
        isbn = self.isbnEdit.text()
        bookinfo['isbn'] = isbn
        
        # 書籍名
        title = self.titleEdit.toPlainText()
        bookinfo['title'] = title

        # 著者
        author = self.authorEdit.text()
        bookinfo['author'] = author
        
        # 出版社
        publisher = self.publisherEdit.text()
        bookinfo['publisher'] = publisher
        
        # 発刊日
        pubdate = self.dateEdit.text()
        bookinfo['pubdate'] = pubdate
        
        # 左右綴じ区分
        binder = 'left' if self.bindComboBox.currentIndex() == 0 else 'right'
        bookinfo['binder'] = binder

        # ページ数
        pages = self.pagesEdit.text()
        bookinfo['pages'] = pages
        
        # 価格
        price = self.priceEdit.text()
        bookinfo['price'] = price
        
        # 更新日時
        moddate = self.updateEdit.text()
        bookinfo['moddate'] = moddate
        
        # 上書き保存
        with open(json_file, 'w', encoding='utf-8') as fout:
            json.dump(bookinfo, fout, ensure_ascii=False, indent=4)

