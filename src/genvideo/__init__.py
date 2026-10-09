"""genVideo - 基于 MoviePy 和 PyAV 的智能图片/视频混合轮播视频生成器。

顶层只暴露轻量的公共 API；依赖 MoviePy 的重功能（如 ``create_slideshow``）
请从子模块显式导入：``from genvideo.generate import create_slideshow``。
"""

__version__ = "0.1.0"

from genvideo.config import (
    DEFAULT_CONFIG,
    VideoSize,
    load_config,
    merge_config,
    parse_color,
    parse_duration,
    parse_video_size,
    subtitle_options,
)

__all__ = [
    "__version__",
    "DEFAULT_CONFIG",
    "VideoSize",
    "load_config",
    "merge_config",
    "parse_color",
    "parse_duration",
    "parse_video_size",
    "subtitle_options",
]
