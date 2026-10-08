"""
动画效果工具模块
提供图片动画效果配置和应用功能
"""
import math

import numpy as np
from PIL import Image
from moviepy import VideoClip

from utils.video_utils import RESAMPLE_ANIMATED, fit_frame


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
    为静态图片片段应用缩放 / 平移动画。

    实现方式：源图先缩放到动画过程中需要的最大尺寸（只算一次），
    之后逐帧只做「裁一个窗口」：

    - 平移：窗口恒等于输出尺寸，纯 numpy 切片，无 PIL 参与；
    - 缩放：窗口尺寸随进度变化，每帧一次 PIL 缩放（Ken Burns 必需）；
    - 无动画 / 未知类型：等价于静态的覆盖裁剪。

    这样避免了对每一帧都重新缩放整张图（旧实现每帧都要
    ``clip.resized()`` + ``CompositeVideoClip``，即两次 PIL 全画幅运算）。

    参数:
        clip: MoviePy 图片片段对象（需要能 ``get_frame(0)`` 取到源图）
        config (AnimationConfig): 动画配置
        video_size (tuple): 视频尺寸 (width, height)

    返回:
        VideoClip: 应用动画后的片段
    """
    frame_function = _build_frame_function(clip, config, video_size)
    result = VideoClip(frame_function, duration=getattr(clip, "duration", None))
    result.size = (int(video_size[0]), int(video_size[1]))
    return result


def _cover_array(source, video_size, scale, resample=RESAMPLE_ANIMATED):
    """
    把源图缩放到给定比例，返回 (ndarray, 宽, 高)，用作动画的取值底板。
    """
    image = Image.fromarray(source)
    if image.mode != "RGB":
        image = image.convert("RGB")

    img_w, img_h = image.size
    new_w = max(int(video_size[0]), int(math.ceil(img_w * scale)))
    new_h = max(int(video_size[1]), int(math.ceil(img_h * scale)))
    if (new_w, new_h) != image.size:
        image = image.resize((new_w, new_h), resample)

    return np.asarray(image)[:, :, :3], new_w, new_h


def _build_frame_function(clip, config, video_size):
    """构造 ``frame(t) -> ndarray`` 的动画帧函数"""
    video_w, video_h = int(video_size[0]), int(video_size[1])
    duration = getattr(clip, "duration", None) or 1.0
    source = clip.get_frame(0)
    easing = config.get_easing_function()

    animation_type = config.animation_type
    intensity = max(0.0, float(config.intensity))

    is_zoom = animation_type in (AnimationConfig.ZOOM_IN, AnimationConfig.ZOOM_OUT)
    is_pan = animation_type in (AnimationConfig.PAN_LEFT, AnimationConfig.PAN_RIGHT,
                                AnimationConfig.PAN_UP, AnimationConfig.PAN_DOWN)

    if not is_zoom and not is_pan:
        # 无动画 / 未知类型：静态覆盖裁剪，只算一次
        static_frame = fit_frame(source, (video_w, video_h))
        return lambda t: static_frame

    img_h, img_w = source.shape[:2]
    base_scale = max(video_w / img_w, video_h / img_h)

    if is_zoom:
        zoom_range = intensity * 0.3          # 最大 30% 的缩放
        max_scale = base_scale * (1 + zoom_range)
    else:
        zoom_range = 0.0
        max_scale = base_scale * (1 + intensity * 0.5)   # 额外缩放提供平移空间

    cover, cover_w, cover_h = _cover_array(source, (video_w, video_h), max_scale)

    def progress_at(t):
        return easing(min(max(t / duration, 0.0), 1.0))

    if is_zoom:
        start_scale = base_scale if animation_type == AnimationConfig.ZOOM_IN else base_scale * (1 + zoom_range)
        end_scale = base_scale * (1 + zoom_range) if animation_type == AnimationConfig.ZOOM_IN else base_scale

        def window(t):
            scale = start_scale + (end_scale - start_scale) * progress_at(t)
            ratio = max_scale / scale
            win_w = video_w * ratio
            win_h = video_h * ratio
            return win_w, win_h, (cover_w - win_w) / 2.0, (cover_h - win_h) / 2.0

    else:
        # 平移幅度按视频尺寸的百分比算，保证不同图片的观感一致
        pan_percentage = intensity * 0.3
        margin_x = cover_w - video_w
        margin_y = cover_h - video_h
        max_offset_x = min(margin_x / 2.0, video_w * pan_percentage / 2.0)
        max_offset_y = min(margin_y / 2.0, video_h * pan_percentage / 2.0)

        def window(t):
            progress = progress_at(t)
            if animation_type == AnimationConfig.PAN_LEFT:
                dx, dy = max_offset_x * (1 - 2 * progress), 0.0
            elif animation_type == AnimationConfig.PAN_RIGHT:
                dx, dy = max_offset_x * (2 * progress - 1), 0.0
            elif animation_type == AnimationConfig.PAN_UP:
                dx, dy = 0.0, max_offset_y * (1 - 2 * progress)
            else:  # PAN_DOWN
                dx, dy = 0.0, max_offset_y * (2 * progress - 1)
            return video_w, video_h, margin_x / 2.0 + dx, margin_y / 2.0 + dy

    def frame_function(t):
        win_w, win_h, left, top = window(t)
        win_w = min(cover_w, max(video_w, int(round(win_w))))
        win_h = min(cover_h, max(video_h, int(round(win_h))))

        x0 = max(0, min(int(round(left)), cover_w - win_w))
        y0 = max(0, min(int(round(top)), cover_h - win_h))
        crop = cover[y0:y0 + win_h, x0:x0 + win_w]

        if win_w == video_w and win_h == video_h:
            return crop  # 纯 numpy 切片（平移路径）

        return np.asarray(
            Image.fromarray(crop).resize((video_w, video_h), RESAMPLE_ANIMATED)
        )

    return frame_function


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
