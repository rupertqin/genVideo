"""
视频配置工具模块
提供常用视频尺寸预设、config.yaml 读取与配置管理
"""
import copy
import os
import re


class VideoSize:
    """视频尺寸预设类"""

    # 测试尺寸（快速预览）
    TEST_TINY = (320, 240)          # 极小测试尺寸
    TEST_SMALL = (480, 360)         # 小测试尺寸
    TEST_MEDIUM = (640, 480)        # 中等测试尺寸

    # 横屏尺寸
    HD_720P = (1280, 720)           # 720P 高清
    HD_1080P = (1920, 1080)         # 1080P 全高清
    UHD_4K = (3840, 2160)           # 4K 超高清

    # 竖屏尺寸（适合抖音、快手等短视频平台）
    PORTRAIT_SMALL = (180, 320)      # 竖屏测试尺寸
    PORTRAIT_TEST = (360, 640)      # 竖屏测试尺寸
    PORTRAIT_720P = (720, 1280)     # 竖屏 720P
    PORTRAIT_1080P = (1080, 1920)   # 竖屏 1080P

    # 方形尺寸（适合 Instagram 等）
    SQUARE_TEST = (480, 480)        # 方形测试尺寸
    SQUARE_720 = (720, 720)         # 方形 720
    SQUARE_1080 = (1080, 1080)      # 方形 1080

    # 宽屏尺寸
    WIDESCREEN_2K = (2560, 1440)    # 2K 宽屏
    CINEMA_4K = (4096, 2160)        # 电影 4K

    @classmethod
    def get_size(cls, preset_name):
        """
        根据预设名称获取视频尺寸

        参数:
            preset_name (str): 预设名称，如 'HD_720P', 'PORTRAIT_1080P' 等

        返回:
            tuple: (width, height) 或 None（如果预设不存在）
        """
        return getattr(cls, preset_name.upper(), None)

    @classmethod
    def list_presets(cls):
        """
        列出所有可用的预设

        返回:
            dict: {预设名称: (width, height)}
        """
        presets = {}
        for attr in dir(cls):
            if attr.isupper() and not attr.startswith('_'):
                value = getattr(cls, attr)
                if isinstance(value, tuple) and len(value) == 2:
                    presets[attr] = value
        return presets


def parse_video_size(size_input):
    """
    解析视频尺寸输入

    参数:
        size_input: 可以是以下几种形式：
            - tuple: (width, height) 直接指定宽高
            - str: 预设名称，如 'HD_720P', 'PORTRAIT_1080P'
            - str: 格式 'WIDTHxHEIGHT'，如 '1280x720'

    返回:
        tuple: (width, height)

    异常:
        ValueError: 无法解析输入时抛出
    """
    # 如果是 tuple，直接返回
    if isinstance(size_input, tuple) and len(size_input) == 2:
        return size_input

    # 如果是字符串
    if isinstance(size_input, str):
        # 尝试作为预设名称
        preset_size = VideoSize.get_size(size_input)
        if preset_size:
            return preset_size

        # 尝试解析 'WIDTHxHEIGHT' 格式
        if 'x' in size_input.lower():
            try:
                parts = size_input.lower().split('x')
                width = int(parts[0].strip())
                height = int(parts[1].strip())
                return (width, height)
            except (ValueError, IndexError):
                pass

    raise ValueError(
        f"无法解析视频尺寸: {size_input}\n"
        f"支持的格式:\n"
        f"  - tuple: (width, height)\n"
        f"  - 预设名称: {', '.join(VideoSize.list_presets().keys())}\n"
        f"  - 字符串格式: 'WIDTHxHEIGHT'，如 '1280x720'"
    )


def print_available_sizes():
    """打印所有可用的视频尺寸预设"""
    print("可用的视频尺寸预设:")
    print("-" * 50)

    presets = VideoSize.list_presets()

    # 分类显示
    categories = {
        "测试尺寸": ["TEST_TINY", "TEST_SMALL", "TEST_MEDIUM"],
        "横屏尺寸": ["HD_720P", "HD_1080P", "UHD_4K", "WIDESCREEN_2K", "CINEMA_4K"],
        "竖屏尺寸": ["PORTRAIT_TEST", "PORTRAIT_720P", "PORTRAIT_1080P"],
        "方形尺寸": ["SQUARE_TEST", "SQUARE_720", "SQUARE_1080"],
    }

    for category, preset_names in categories.items():
        print(f"\n{category}:")
        for name in preset_names:
            if name in presets:
                width, height = presets[name]
                print(f"  {name:20s} -> {width} x {height}")

    print("\n" + "-" * 50)
    print("使用方法:")
    print("  1. 使用预设: img_size='HD_720P' 或 img_size=VideoSize.HD_720P")
    print("  2. 自定义尺寸: img_size=(1280, 720)")
    print("  3. 字符串格式: img_size='1280x720'")


# ==============================================================
# config.yaml 配置
# ==============================================================

CONFIG_FILENAME = "config.yaml"

# 内置默认值：config.yaml 里没写的键都会回落到这里
DEFAULT_CONFIG = {
    "video": {
        "size": "HD_720P",
        "fps": 24,
        "duration": None,
        "transition": 1.0,
        "encoder": "libx264",
        "preset": "veryfast",
        "bitrate": "5000k",
        "animation": False,
        "layout": "fullscreen",
    },
    "media": {
        "images": "assets/images",
        "videos": None,
        "dir": None,
        "audio": "assets/audio/audio.wav",
        "output": "output/generated.mp4",
    },
    "layout": {
        "fullscreen": {"position": "center"},
        "card": {
            "inset": 0.07,
            "radius": 40,
            "shadow": 24,
            "background_blur": 24,
            "background_darken": 0.35,
            "title": None,
            "title_size": 60,
            "title_color": "#FFFFFF",
            "title_position": "top",
        },
        "hero": {
            "bg_color": "#EDF2F4",
            "hero_top": 0.0,
            "hero_h": 0.60,
            "hero_w": 0.60,
            "hero_position": None,
            "fade": True,
            "grid": True,
            "grid_size": None,
            "grid_color": "#1E2528",
            "grid_alpha": 0.05,
            "marks": True,
            "accent": "#5E8C7A",
            "title": None,
            "title_size": None,
            "title_color": "#1E252861",
            "title_font": None,
            "title_max_width": 0.8,
        },
    },
    "subtitle": {
        "enabled": True,
        "path": None,
        "font": None,
        "size": None,
        "bottom": 0.08,
        "max_width": 0.9,
        "line_spacing": 1.25,
        "stroke_width": 3,
        "strip_punct": False,
        "text_color": "#FFFFFF",
        "box_color": [0, 0, 0],
        "box_alpha": 150,
    },
}


def default_config_path():
    """默认配置文件路径（与本模块同目录的 config.yaml）"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def merge_config(base, override):
    """
    递归合并配置字典（override 覆盖 base），返回新字典，不修改入参。
    """
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path=None):
    """
    读取 config.yaml 并与内置默认值合并。

    参数:
        path (str): 配置文件路径，None 时取本模块同目录下的 config.yaml

    返回:
        dict: 完整配置字典；配置文件不存在时返回内置默认配置

    异常:
        RuntimeError: 缺少 PyYAML 或 YAML 解析失败时抛出（附带文件路径）
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    config_file = path or default_config_path()
    if not os.path.exists(config_file):
        return config

    try:
        import yaml  # type: ignore[import-untyped]  # PyYAML 不带类型信息
    except ImportError as exc:  # pragma: no cover - 取决于环境
        raise RuntimeError(
            f"读取 {os.path.basename(config_file)} 需要 PyYAML，请先执行: pip install pyyaml"
        ) from exc

    try:
        with open(config_file, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:
        raise RuntimeError(f"解析配置文件失败: {config_file}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"配置文件格式错误（顶层应为键值对）: {config_file}")

    return merge_config(config, data)


# 时长单位换算
_DURATION_UNITS = {
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "m": 60.0, "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hrs": 3600.0, "hour": 3600.0, "hours": 3600.0,
}

_DURATION_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([a-z]+)")


def parse_duration(value):
    """
    解析时长配置，统一返回秒数（float）。

    支持的写法:
        180 / 180.5        数字 -> 秒
        "180" / "180.5"    字符串数字 -> 秒
        "180s" / "3m" / "1.5h"   带单位（s/sec/m/min/h/hr 等）
        "3:00" / "03:00"         分:秒
        "00:03:00"               时:分:秒
        "00:03:00.250"           精确到毫秒
        "1:02:03.456"            时:分:秒.毫秒
        None / ""                不限制，返回 None

    参数:
        value: 时长配置值

    返回:
        float or None: 秒数（>= 0）

    异常:
        ValueError: 无法解析或为负数时抛出
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool 是 int 子类，先挡掉避免 True/False 被当成 1/0
        raise ValueError(f"无法解析时长: {value!r}")

    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip()
        if not text or text.lower() in ("null", "none", "off"):
            return None

        unit_match = _DURATION_UNIT_RE.fullmatch(text.lower())
        if unit_match:
            unit = unit_match.group(2)
            if unit not in _DURATION_UNITS:
                raise ValueError(f"无法解析时长: {value!r}（未知单位 {unit}）")
            seconds = float(unit_match.group(1)) * _DURATION_UNITS[unit]
        elif ":" in text:
            parts = text.split(":")
            if len(parts) > 3:
                raise ValueError(f"无法解析时长: {value!r}（最多 时:分:秒）")
            try:
                numbers = [float(part) for part in parts]
            except ValueError:
                raise ValueError(f"无法解析时长: {value!r}") from None
            seconds = 0.0
            for number in numbers:
                seconds = seconds * 60 + number
        else:
            try:
                seconds = float(text)
            except ValueError:
                raise ValueError(f"无法解析时长: {value!r}") from None

    if seconds < 0:
        raise ValueError(f"时长不能为负数: {value!r}")
    return seconds


def parse_color(value, alpha=None):
    """
    把配置里的颜色解析成 RGBA 元组。

    参数:
        value: "#RRGGBB" / "#RRGGBBAA" / [r, g, b] / [r, g, b, a] / None
        alpha (int): 只给出 RGB 时使用的透明度（0-255），None 表示 255

    返回:
        tuple or None: (r, g, b, a)；value 为 None 时返回 None

    异常:
        ValueError: 无法解析时抛出
    """
    if value is None:
        return None

    default_alpha = 255 if alpha is None else int(alpha)

    if isinstance(value, str):
        digits = value.strip().lstrip("#")
        if len(digits) == 6:
            rgb = tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))
            return rgb + (default_alpha,)
        if len(digits) == 8:
            return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4, 6))
        raise ValueError(f"无法解析颜色: {value!r}")

    if isinstance(value, (list, tuple)) and len(value) in (3, 4):
        channels = tuple(int(v) for v in value)
        return channels if len(channels) == 4 else channels + (default_alpha,)

    raise ValueError(f"无法解析颜色: {value!r}")


def subtitle_options(config=None):
    """
    从完整配置中取出字幕渲染参数（可直接传给 burn_subtitles）。

    参数:
        config (dict): load_config 的结果；None 时使用内置默认值

    返回:
        dict: 含 font_path / font_size / bottom_ratio / max_width_ratio /
              line_spacing / stroke_width / strip_punct / text_color / box_color
    """
    section = merge_config(DEFAULT_CONFIG["subtitle"], (config or {}).get("subtitle", {}))

    font_size = section.get("size")
    return {
        "font_path": section.get("font"),
        "font_size": int(font_size) if font_size else None,
        "bottom_ratio": float(section.get("bottom", 0.08)),
        "max_width_ratio": float(section.get("max_width", 0.9)),
        "line_spacing": float(section.get("line_spacing", 1.25)),
        "stroke_width": int(section.get("stroke_width", 3)),
        "strip_punct": bool(section.get("strip_punct", False)),
        "text_color": parse_color(section.get("text_color"), 255),
        "box_color": parse_color(section.get("box_color"), section.get("box_alpha", 150)),
    }
