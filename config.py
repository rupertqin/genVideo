"""
视频配置工具模块
提供常用视频尺寸预设和配置管理
"""


class VideoSize:
    """视频尺寸预设类"""

    # 测试尺寸（快速预览）
    TEST_TINY = (320, 240)          # 极小测试尺寸
    TEST_SMALL = (480, 360)         # 小测试尺寸
    TEST_MEDIUM = (640, 480)        # 中等测试尺寸

    # 横屏尺寸
    HD_720P = (1280, 720)           # 720P 高清
    FULL_HD_1080P = (1920, 1080)    # 1080P 全高清
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
        "横屏尺寸": ["HD_720P", "FULL_HD_1080P", "UHD_4K", "WIDESCREEN_2K", "CINEMA_4K"],
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
