"""
图片和媒体文件处理工具模块
提供图片路径获取和音频文件路径查找功能
"""
import os


def get_image_paths(dir_path):
    """
    从指定目录获取图片文件路径集合

    参数:
        dir_path (str): 图片目录路径

    返回:
        list: 按文件系统读取顺序排列的图片文件路径列表
    """
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}
    try:
        names = os.listdir(dir_path)
    except FileNotFoundError:
        return []
    paths = [os.path.join(dir_path, name) for name in names
             if os.path.splitext(name)[1].lower() in exts]
    return paths


def get_audio_path():
    """
    查找项目根目录下的音频文件

    返回:
        str or None: 音频文件路径，优先查找 .wav 文件，若未找到则查找 .mp3 文件
    """
    candidates = ["audio.wav", "audio.mp3"]
    for name in candidates:
        if os.path.exists(name):
            return name
    return None
