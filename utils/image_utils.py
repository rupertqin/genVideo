"""
图片和媒体文件处理工具模块
提供图片路径获取和音频文件路径查找功能
兼容旧版接口，内部使用 media_utils
"""
import os
from utils.media_utils import (
    get_media_paths as _get_media_paths,
    get_image_paths as _get_image_paths,
    get_video_paths as _get_video_paths,
    get_audio_path,
    MediaType,
    MediaItem,
    IMAGE_EXTS,
    VIDEO_EXTS,
    is_video_file,
    is_image_file,
    get_media_type
)


def get_image_paths(dir_path):
    """
    从指定目录获取图片文件路径列表

    参数:
        dir_path (str): 图片目录路径

    返回:
        list: 按文件名排序的图片文件路径列表
    """
    return _get_image_paths(dir_path)


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
