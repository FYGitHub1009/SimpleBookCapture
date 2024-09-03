
# OpenCVインストール
sudo apt-get install -y python3-opencv

# ISBN読み取り用
sudo apt-get install -y libzbar0
pip install pyzbar --break-system-package
pip install xmltodict --break-system-package

# PDF出力
pip install img2pdf --break-system-package

# SE再生
sudo apt-get install -y python3-gst-1.0
pip install playsound --break-system-package

# フォルダ移動
cd ~

# SimpleBookCaptureダウンロード
git clone https://github.com/FYGitHub1009/SimpleBookCapture.git
