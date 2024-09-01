from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QVBoxLayout, QPushButton, QLabel

class FileFolderDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.save_path = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("ファイルまたはフォルダを選択してください")
        layout.addWidget(self.label)

        file_button = QPushButton("ファイルとして出力")
        file_button.clicked.connect(self.select_file)
        layout.addWidget(file_button)

        folder_button = QPushButton("選択フォルダへ出力")
        folder_button.clicked.connect(self.select_folder)
        layout.addWidget(folder_button)

        self.setLayout(layout)
        self.setWindowTitle("ファイル/フォルダ選択")

    def select_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "保存先ファイルを指定",
            "Untitled.pdf",
            "PDFファイル (*.pdf);;TARファイル (*.tar);;ZIPファイル (*.zip)",
            options=options
        )
        if file_path:
            self.save_path = file_path
            self.label.setText(f"選択されたフォルダ: {file_path}")
            self.accept()


    def select_folder(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "保存先フォルダを指定",
            "Untitled",
            "フォルダ選択",
            options=options
        )
        if folder_path:
            self.save_path = folder_path
            self.label.setText(f"選択されたフォルダ: {folder_path}")
            self.accept()


