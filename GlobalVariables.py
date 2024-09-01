import numpy as np

# カメラインスタンス
from picamera2 import Picamera2
picam2s = [Picamera2(0), Picamera2(1)]

# コンフィグ作成
piconfigs = []
for camid in [0, 1]:
    # 静止画用コンフィグ
    still_config = picam2s[camid].create_still_configuration()    
    # プレビューコンフィグ
    preview_config = picam2s[camid].create_preview_configuration()
    # 保存
    piconfigs.append({"still":still_config, "preview":preview_config})

#for camid in [0]:
#    print(piconfigs[camid]["still"])
#    print(piconfigs[camid]["preview"])

# メタデータ表示
pimetadatas = ["", ""]

meta_keys = [
    "AeLocked",
    "AfPauseState",
    "AfState",
    "AnalogueGain",
    "ColourCorrectionMatrix",
    "ColourGains",
    "ColourTemperature",
    "DigitalGain",
    "ExposureTime",
    "FocusFoM",
    "FrameDuration",
    "LensPosition",
    "Lux",
    "ScalerCrop",
    "SensorBlackLevels",
    "SensorTemperature",
    "SensorTimestamp"
]

# post_callbackを設定
def post_callback0(request):
    # Read the metadata we get back from every request
    metadata = request.get_metadata()
    # Put Awb to the end, as they only flash up sometimes
    sorted_metadata = sorted(metadata.items(), key=lambda x: x[0] if "Awb" not in x[0] else f"Z{x[0]}")
    # And print everything nicely
    pretty_metadata = ["camera0"]
    for k, v in sorted_metadata:
        # まれになにか大量のビット列が入ってくる
        if k not in meta_keys:
            continue
        row = ""
        try:
            iter(v)
            if k == "ColourCorrectionMatrix":
                matrix = np.around(np.reshape(v, (-1, 3)), decimals=2)
                row = f"{k}:\n{matrix}"
            else:
                row_data = [f'{x:.2f}' if type(x) is float else f'{x}' for x in v]
                row = f"{k}: ({', '.join(row_data)})"
        except TypeError:
            if type(v) is float:
                row = f"{k}: {v:.2f}"
            else:
                row = f"{k}: {v}"
        pretty_metadata.append(row)
    #print('\n'.join(pretty_metadata))
    pimetadatas[0] = '\n'.join(pretty_metadata)
picam2s[0].post_callback = post_callback0

def post_callback1(request):
    # Read the metadata we get back from every request
    metadata = request.get_metadata()
    # Put Awb to the end, as they only flash up sometimes
    sorted_metadata = sorted(metadata.items(), key=lambda x: x[0] if "Awb" not in x[0] else f"Z{x[0]}")
    # And print everything nicely
    pretty_metadata = ["camera1"]
    for k, v in sorted_metadata:
        # まれになにか大量のビット列が入ってくる
        if k not in meta_keys:
            continue
        row = ""
        try:
            iter(v)
            if k == "ColourCorrectionMatrix":
                matrix = np.around(np.reshape(v, (-1, 3)), decimals=2)
                row = f"{k}:\n{matrix}"
            else:
                row_data = [f'{x:.2f}' if type(x) is float else f'{x}' for x in v]
                row = f"{k}: ({', '.join(row_data)})"
        except TypeError:
            if type(v) is float:
                row = f"{k}: {v:.2f}"
            else:
                row = f"{k}: {v}"
        pretty_metadata.append(row)
    #print('\n'.join(pretty_metadata))
    pimetadatas[1] = '\n'.join(pretty_metadata)
picam2s[1].post_callback = post_callback1


# 初期コンフィグの反映
import os, json
configfiles = [
    os.path.join(".", "Configure", "camera0_configure_recommend.json"),
    os.path.join(".", "Configure", "camera1_configure_recommend.json")]
    
for camid in [0, 1]:
    # コンフィグファイル読み込み
    config_file = configfiles[camid]
    with open(config_file,'r', encoding="utf-8") as f:
        config = json.load(f)
    
    # 画像サイズ
    width, height = config["BasicSetting"]["ImageSize"]
    
    # センサフォーマット
    sensorFormat = config["BasicSetting"]["sensorFormat"]
    sensorFormat['size'] = tuple(sensorFormat['size'])
    print(sensorFormat)
    
    # 静止画コンフィグ更新
    piconfigs[camid]["still"]['main']['size'] = (width, height)
    piconfigs[camid]["still"]['raw'] = sensorFormat
    # プレビューコンフィグ更新
    piconfigs[camid]["preview"]['main']['format'] = "BGR888"
    preview_width = width if width < 2000 else 2000
    preview_height = int(preview_width* (height / width))
    preview_height = preview_height if preview_height%2==0 else preview_height-1
    piconfigs[camid]["preview"]['main']['size'] = (preview_width, preview_height)
    piconfigs[camid]["preview"]['raw'] = sensorFormat

    # カメラコンフィグ設定
    picam2s[camid].configure(piconfigs[camid]["preview"])  

    # 画質調整
    # 彩度
    saturat = config["ImageTuning"]["Saturation"]
    # コントラスト
    contrast = config["ImageTuning"]["Contrast"]
    # シャープネス
    sharp = config["ImageTuning"]["Sharpness"]
    # 明るさ
    bright = config["ImageTuning"]["Brightness"]
    # コントロール更新
    picam2s[camid].set_controls({
        "Saturation": saturat,
        "Contrast": contrast,
        "Sharpness": sharp,
        "Brightness": bright
    })

    # フォーカス設定
    # フォーカス方式
    focusMode = config["FocusSetting"]["AfMode"]
    
    #　MF設定
    # レンズ位置
    lens = config["FocusSetting"]["LensPosition"]
    
    # フォーカス設定の反映
    picam2s[camid].set_controls({
            "AfMode": focusMode,
            "LensPosition": lens
    })
    



