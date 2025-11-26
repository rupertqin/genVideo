"""
视频和图片处理工具模块
提供图片缩放、位置设置、视频合成等功能
"""
from moviepy import CompositeVideoClip


def resize_and_position_image(clip, video_size, position="center"):
    """
    根据目标视频尺寸调整图片大小并设置位置

    参数:
        clip (ImageClip): 图片片段对象
        video_size (tuple): 目标视频尺寸 (width, height)
        position (str or tuple): 位置设置，默认为 "center"，可以是 ("center", "center") 或其他位置参数

    返回:
        CompositeVideoClip: 合成后的视频片段
    """
    video_w, video_h = video_size
    img_w, img_h = clip.size

    # 计算缩放比例，确保图片完全覆盖视频区域
    scale = max(video_w / img_w, video_h / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)

    # 调整图片大小
    resized_clip = clip.resized(new_size=(new_w, new_h))

    # 设置位置
    positioned_clip = resized_clip.with_position(position)

    # 合成到指定尺寸的视频帧中
    return CompositeVideoClip([positioned_clip], size=video_size)


def calculate_image_scale(img_size, video_size):
    """
    计算图片缩放比例

    参数:
        img_size (tuple): 原始图片尺寸 (width, height)
        video_size (tuple): 目标视频尺寸 (width, height)

    返回:
        tuple: (缩放比例, 缩放后的宽度, 缩放后的高度)
    """
    img_w, img_h = img_size
    video_w, video_h = video_size

    # 计算缩放比例，确保图片完全覆盖视频区域
    scale = max(video_w / img_w, video_h / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)

    return scale, new_w, new_h


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
