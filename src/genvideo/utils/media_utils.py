"""
媒体文件处理工具模块
提供图片和视频路径获取、类型检测等功能
"""
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Union


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    VIDEO = "video"


@dataclass
class MediaItem:
    """媒体项目数据类"""
    path: str
    media_type: MediaType
    name: str
    
    @property
    def is_image(self) -> bool:
        return self.media_type == MediaType.IMAGE
    
    @property
    def is_video(self) -> bool:
        return self.media_type == MediaType.VIDEO
    
    @property
    def extension(self) -> str:
        return os.path.splitext(self.path)[1].lower()


# 支持的图片格式
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}

# 支持的视频格式
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"}


def get_media_paths(dir_path):
    """
    从指定目录获取媒体文件路径集合（图片和视频）

    参数:
        dir_path (str): 媒体目录路径

    返回:
        list: 按文件名排序的 MediaItem 列表
    """
    try:
        names = os.listdir(dir_path)
    except FileNotFoundError:
        return []
    
    media_items = []
    for name in names:
        ext = os.path.splitext(name)[1].lower()
        full_path = os.path.join(dir_path, name)
        
        if ext in IMAGE_EXTS:
            media_items.append(MediaItem(
                path=full_path,
                media_type=MediaType.IMAGE,
                name=name
            ))
        elif ext in VIDEO_EXTS:
            media_items.append(MediaItem(
                path=full_path,
                media_type=MediaType.VIDEO,
                name=name
            ))
    
    # 按文件名排序
    media_items.sort(key=lambda x: x.name)
    return media_items


def get_image_paths(dir_path):
    """
    从指定目录获取图片文件路径列表（兼容旧接口）

    参数:
        dir_path (str): 图片目录路径

    返回:
        list: 按文件名排序的图片文件路径列表
    """
    media_items = get_media_paths(dir_path)
    return [item.path for item in media_items if item.is_image]


def get_video_paths(dir_path):
    """
    从指定目录获取视频文件路径列表

    参数:
        dir_path (str): 视频目录路径

    返回:
        list: 按文件名排序的视频文件路径列表
    """
    media_items = get_media_paths(dir_path)
    return [item.path for item in media_items if item.is_video]


def get_audio_path():
    """
    查找项目根目录下的音频文件（兼容旧接口）

    返回:
        str or None: 音频文件路径，优先查找 .wav 文件，若未找到则查找 .mp3 文件
    """
    candidates = ["audio.wav", "audio.mp3"]
    for name in candidates:
        if os.path.exists(name):
            return name
    return None


# 目录里默认查找的音频文件名
AUDIO_FILENAMES = ("audio.wav", "audio.mp3")


def resolve_dir(configured, fallbacks=()):
    """
    返回第一个实际存在的目录，用于「配置目录 + 旧目录兼容」的场景。

    参数:
        configured (str): 首选目录（通常来自配置）
        fallbacks (tuple): 备用目录列表（按顺序尝试）

    返回:
        str or None: 存在的目录路径，都不存在时返回 None
    """
    for path in (configured, *fallbacks):
        if path and os.path.isdir(path):
            return path
    return None


def find_audio_in(path):
    """
    在给定的文件或目录中查找音频文件。

    参数:
        path (str): 音频文件完整路径；或存放音频的目录（在该目录里找 audio.wav / audio.mp3）

    返回:
        str or None: 音频文件路径，未找到时返回 None
    """
    if not path:
        return None
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for name in AUDIO_FILENAMES:
            candidate = os.path.join(path, name)
            if os.path.isfile(candidate):
                return candidate
    return None


def ensure_parent_dir(path):
    """
    确保目标文件的父目录存在（输出到 output/xxx.mp4 时自动建目录）。

    参数:
        path (str): 文件路径

    返回:
        str: 父目录路径；路径中没有目录部分时返回空字符串
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return parent


def is_video_file(path: str) -> bool:
    """
    判断文件是否为视频文件

    参数:
        path (str): 文件路径

    返回:
        bool: 是否为视频文件
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTS


def is_image_file(path: str) -> bool:
    """
    判断文件是否为图片文件

    参数:
        path (str): 文件路径

    返回:
        bool: 是否为图片文件
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in IMAGE_EXTS


def get_media_type(path: str) -> MediaType:
    """
    根据文件路径判断媒体类型

    参数:
        path (str): 文件路径

    返回:
        MediaType: 媒体类型
    """
    if is_video_file(path):
        return MediaType.VIDEO
    elif is_image_file(path):
        return MediaType.IMAGE
    else:
        raise ValueError(f"Unsupported media file type: {path}")
