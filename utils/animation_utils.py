"""
动画效果工具模块
提供图片动画效果配置和应用功能
"""
import numpy as np
from moviepy import CompositeVideoClip


class EasingCurve:
    """缓动曲线类，提供各种动画缓动函数"""

    @staticmethod
    def linear(t):
        """线性缓动"""
        return t

    @staticmethod
    def ease_in_quad(t):
        """二次缓入"""
        return t * t

    @staticmethod
    def ease_out_quad(t):
        """二次缓出"""
        return t * (2 - t)

    @staticmethod
    def ease_in_out_quad(t):
        """二次缓入缓出"""
        return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

    @staticmethod
    def ease_in_cubic(t):
        """三次缓入"""
        return t * t * t

    @staticmethod
    def ease_out_cubic(t):
        """三次缓出"""
        return (t - 1) * (t - 1) * (t - 1) + 1

    @staticmethod
    def ease_in_out_cubic(t):
        """三次缓入缓出"""
        return 4 * t * t * t if t < 0.5 else (t - 1) * (2 * t - 2) * (2 * t - 2) + 1


class AnimationConfig:
    """动画配置类"""

    # 动画类型常量
    ZOOM_IN = "zoom_in"           # 放大
    ZOOM_OUT = "zoom_out"         # 缩小
    PAN_LEFT = "pan_left"         # 向左平移
    PAN_RIGHT = "pan_right"       # 向右平移
    PAN_UP = "pan_up"             # 向上平移
    PAN_DOWN = "pan_down"         # 向下平移
    NONE = "none"                 # 无动画

    def __init__(self, animation_type=ZOOM_IN, intensity=0.1,
                 easing="ease_in_out_quad", duration=None):
        """
        初始化动画配置

        参数:
            animation_type (str): 动画类型
            intensity (float): 动画强度 (0.0-1.0)，控制动作幅度
            easing (str): 缓动曲线名称
            duration (float): 动画持续时间（秒），None 表示使用片段完整时长
        """
        self.animation_type = animation_type
        self.intensity = intensity
        self.easing = easing
        self.duration = duration

    def get_easing_function(self):
        """获取缓动函数"""
        return getattr(EasingCurve, self.easing, EasingCurve.linear)


def apply_animation(clip, config, video_size):
    """
    为图片片段应用动画效果

    注意：此函数应该在 resize_and_position_image 之前调用，
    因为它会返回一个已经合成好的 CompositeVideoClip

    参数:
        clip: MoviePy 图片片段对象（原始 ImageClip）
        config (AnimationConfig): 动画配置
        video_size (tuple): 视频尺寸 (width, height)

    返回:
        CompositeVideoClip: 应用动画后的合成片段
    """
    if config.animation_type == AnimationConfig.NONE:
        # 无动画，使用标准的缩放和居中
        video_w, video_h = video_size
        img_w, img_h = clip.size
        scale = max(video_w / img_w, video_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        resized_clip = clip.resized(new_size=(new_w, new_h))
        positioned_clip = resized_clip.with_position("center")
        return CompositeVideoClip([positioned_clip], size=video_size)

    easing_func = config.get_easing_function()

    if config.animation_type == AnimationConfig.ZOOM_IN:
        return _apply_zoom(clip, config, video_size, easing_func, zoom_in=True)

    elif config.animation_type == AnimationConfig.ZOOM_OUT:
        return _apply_zoom(clip, config, video_size, easing_func, zoom_in=False)

    elif config.animation_type in [AnimationConfig.PAN_LEFT, AnimationConfig.PAN_RIGHT,
                                    AnimationConfig.PAN_UP, AnimationConfig.PAN_DOWN]:
        return _apply_pan(clip, config, video_size, easing_func)

    # 默认返回无动画版本
    video_w, video_h = video_size
    img_w, img_h = clip.size
    scale = max(video_w / img_w, video_h / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    resized_clip = clip.resized(new_size=(new_w, new_h))
    positioned_clip = resized_clip.with_position("center")
    return CompositeVideoClip([positioned_clip], size=video_size)


def _apply_zoom(clip, config, video_size, easing_func, zoom_in=True):
    """
    应用缩放动画
    通过动态 resize 实现缩放效果
    """
    video_w, video_h = video_size
    img_w, img_h = clip.size

    # 计算基础缩放比例（确保图片覆盖视频区域）
    base_scale = max(video_w / img_w, video_h / img_h)

    # 计算动画缩放范围
    zoom_range = config.intensity * 0.3  # 最大 30% 的缩放
    start_scale = base_scale if zoom_in else base_scale * (1 + zoom_range)
    end_scale = base_scale * (1 + zoom_range) if zoom_in else base_scale

    # 使用 resize 的函数形式实现动态缩放
    def resize_func(t):
        progress = easing_func(min(t / clip.duration, 1.0))
        scale = start_scale + (end_scale - start_scale) * progress
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        return (new_w, new_h)

    # 调整图片大小（动态）
    resized_clip = clip.resized(resize_func)

    # 设置位置（保持居中）
    positioned_clip = resized_clip.with_position("center")

    # 合成到指定尺寸的视频帧中
    return CompositeVideoClip([positioned_clip], size=video_size)


def _apply_pan(clip, config, video_size, easing_func):
    """
    应用平移动画
    通过动态 position 实现平移效果
    平移幅度基于视频画面比例，确保所有图片动画效果一致
    """
    video_w, video_h = video_size
    img_w, img_h = clip.size

    # 计算基础缩放比例（确保图片覆盖视频区域）
    base_scale = max(video_w / img_w, video_h / img_h)
    # 额外缩放提供平移空间
    scale = base_scale * (1 + config.intensity * 0.5)
    new_w, new_h = int(img_w * scale), int(img_h * scale)

    # 平移幅度基于视频宽度的百分比（统一所有图片的动画效果）
    pan_percentage = config.intensity * 0.3  # 最大移动视频宽度的30%
    max_offset_x = video_w * pan_percentage / 2
    max_offset_y = video_h * pan_percentage / 2

    def position_func(t):
        progress = easing_func(min(t / clip.duration, 1.0))

        # 居中位置
        center_x = (video_w - new_w) / 2
        center_y = (video_h - new_h) / 2

        if config.animation_type == AnimationConfig.PAN_LEFT:
            x = center_x + max_offset_x * (1 - 2 * progress)
            y = center_y
        elif config.animation_type == AnimationConfig.PAN_RIGHT:
            x = center_x + max_offset_x * (2 * progress - 1)
            y = center_y
        elif config.animation_type == AnimationConfig.PAN_UP:
            x = center_x
            y = center_y + max_offset_y * (1 - 2 * progress)
        else:  # PAN_DOWN
            x = center_x
            y = center_y + max_offset_y * (2 * progress - 1)

        return (x, y)

    resized_clip = clip.resized(new_size=(new_w, new_h))
    positioned_clip = resized_clip.with_position(position_func)

    return CompositeVideoClip([positioned_clip], size=video_size)


def get_random_animation_config(intensity=0.1, easing="ease_in_out_quad"):
    """
    获取随机动画配置

    参数:
        intensity (float): 动画强度
        easing (str): 缓动曲线

    返回:
        AnimationConfig: 随机动画配置
    """
    import random
    animation_types = [
        AnimationConfig.ZOOM_IN,
        AnimationConfig.ZOOM_OUT,
        AnimationConfig.PAN_LEFT,
        AnimationConfig.PAN_RIGHT,
        AnimationConfig.PAN_UP,
        AnimationConfig.PAN_DOWN,
    ]

    animation_type = random.choice(animation_types)
    return AnimationConfig(animation_type, intensity, easing)
