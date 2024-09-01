import os
import cv2
import numpy as np
import json

# 画像変換
def transform(image_org, config_file):
    # コンフィグファイル読み込み
    with open(config_file,'r', encoding="utf-8") as f:
        config = json.load(f)
            
    # アクリル板の4点座標
    src = []
    for ivert, circle in enumerate(config["ImageTransform"]["AcrylicPoints"]):
        x, y = circle
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
    
    return image_trans
