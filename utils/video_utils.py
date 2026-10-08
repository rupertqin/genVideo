"""
视频和图片处理工具模块
提供图片缩放、位置设置、视频合成等功能
"""
import math

import numpy as np
from PIL import Image
from moviepy import CompositeVideoClip, VideoClip

# 静态图的插值方式（只算一次，可以用质量更好的 LANCZOS）
RESAMPLE_STATIC = Image.LANCZOS
# 逐帧动画的插值方式（每帧都要算，BILINEAR 速度与画质更平衡）
RESAMPLE_ANIMATED = Image.BILINEAR


def _position_ratios(position):
    """
    把 MoviePy 风格的位置参数换算成裁剪偏移比例 (x_ratio, y_ratio)。

    0.0 表示对齐左/上边缘，1.0 表示对齐右/下边缘，0.5 表示居中。
    """
    if isinstance(position, str):
        return {
            "center": (0.5, 0.5),
            "left": (0.0, 0.5),
            "right": (1.0, 0.5),
            "top": (0.5, 0.0),
            "bottom": (0.5, 1.0),
        }.get(position, (0.5, 0.5))

    if isinstance(position, (tuple, list)) and len(position) == 2:
        def axis(value):
            if value in ("left", "top"):
                return 0.0
            if value in ("right", "bottom"):
                return 1.0
            return 0.5

        return axis(position[0]), axis(position[1])

    return (0.5, 0.5)


def cover_geometry(img_size, video_size):
    """
    计算「覆盖」目标尺寸所需的缩放比例与结果尺寸。

    缩放比例取两个方向的较大值，保证图片两个方向都铺满目标区域
    （不足的部分由居中裁剪补齐，不会出现黑边）。

    参数:
        img_size (tuple): 图片尺寸 (width, height)
        video_size (tuple): 目标尺寸 (width, height)

    返回:
        tuple: (缩放比例, 缩放后宽度, 缩放后高度)
    """
    img_w, img_h = img_size
    video_w, video_h = video_size

    scale = max(video_w / img_w, video_h / img_h)
    new_w = max(video_w, int(math.ceil(img_w * scale)))
    new_h = max(video_h, int(math.ceil(img_h * scale)))

    return scale, new_w, new_h


def calculate_image_scale(img_size, video_size):
    """
    计算图片缩放比例（兼容旧接口）。

    返回:
        tuple: (缩放比例, 缩放后宽度, 缩放后高度)
    """
    return cover_geometry(img_size, video_size)


def fit_frame(image, video_size, position="center", resample=RESAMPLE_STATIC):
    """
    把一帧图像按「覆盖」方式缩放，再按 position 裁剪到目标尺寸。

    参数:
        image (np.ndarray): 源帧 (H, W, 3) 或 (H, W, 4)
        video_size (tuple): 目标尺寸 (width, height)
        position (str or tuple): 裁剪位置，支持 center/left/right/top/bottom
            或形如 ("left", "top") 的二元组
        resample: PIL 重采样方式

    返回:
        np.ndarray: (height, width, 3) 的 uint8 帧
    """
    video_w, video_h = int(video_size[0]), int(video_size[1])

    src = Image.fromarray(image)
    if src.mode != "RGB":
        src = src.convert("RGB")

    _, new_w, new_h = cover_geometry(src.size, (video_w, video_h))
    if (new_w, new_h) != src.size:
        src = src.resize((new_w, new_h), resample)

    x_ratio, y_ratio = _position_ratios(position)
    left = int(round((new_w - video_w) * x_ratio))
    top = int(round((new_h - video_h) * y_ratio))

    cropped = src.crop((left, top, left + video_w, top + video_h))
    return np.ascontiguousarray(np.asarray(cropped)[:, :, :3])


def resize_and_position_image(clip, video_size, position="center"):
    """
    把静态图片缩放 / 裁剪到目标尺寸，并只计算一次后逐帧复用。

    旧实现每帧都会做一次 ``clip.resized()``（PIL 重采样）加一次
    ``CompositeVideoClip``（PIL 转换与粘贴）。对静态图片来说每帧输入相同、
    结果也相同，属于纯重复计算；1080p 实测约 25 fps，改成预计算后约 240 fps。

    参数:
        clip (ImageClip): 图片片段（需要能 ``get_frame(0)`` 取到源图）
        video_size (tuple): 目标视频尺寸 (width, height)
        position (str or tuple): 裁剪位置，默认居中

    返回:
        VideoClip: 固定返回预计算帧的片段（尺寸为 video_size）
    """
    frame = fit_frame(clip.get_frame(0), video_size, position=position)
    result = VideoClip(lambda t: frame, duration=getattr(clip, "duration", None))
    result.size = (int(video_size[0]), int(video_size[1]))
    return result


def create_centered_video_frame(clip, video_size):
    """
    将片段居中合成到指定尺寸的视频帧中

    参数:
        clip: 视频片段对象
        video_size (tuple): 目标视频尺寸 (width, height)

    返回:
        CompositeVideoClip: 合成后的视频片段
    """
    return CompositeVideoClip([clip], size=video_size)


def resize_and_position_video(clip, video_size, position="center"):
    """
    根据目标视频尺寸调整视频大小并设置位置

    参数:
        clip (VideoClip): 视频片段对象
        video_size (tuple): 目标视频尺寸 (width, height)
        position (str or tuple): 位置设置，默认为 "center"

    返回:
        VideoClip: 缩放后的视频片段
    """
    video_w, video_h = video_size
    clip_w, clip_h = clip.size

    scale = max(video_w / clip_w, video_h / clip_h)
    new_w, new_h = int(clip_w * scale), int(clip_h * scale)

    resized_clip = clip.resized(new_size=(new_w, new_h))
    positioned_clip = resized_clip.with_position(position)

    final_clip = CompositeVideoClip([positioned_clip], size=video_size)
    final_clip = final_clip.with_duration(clip.duration)

    return final_clip
