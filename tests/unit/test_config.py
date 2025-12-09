"""
config.py 模块的单元测试 - 修复版本
"""
import pytest
from config import VideoSize, parse_video_size, print_available_sizes


class TestVideoSize:
    """VideoSize 类的测试"""

    def test_get_size_valid_preset(self):
        """测试获取有效的预设尺寸"""
        # 测试横屏尺寸
        assert VideoSize.get_size('HD_720P') == (1280, 720)
        assert VideoSize.get_size('FULL_HD_1080P') == (1920, 1080)

        # 测试竖屏尺寸
        assert VideoSize.get_size('PORTRAIT_720P') == (720, 1280)
        assert VideoSize.get_size('PORTRAIT_1080P') == (1080, 1920)

        # 测试方形尺寸
        assert VideoSize.get_size('SQUARE_720') == (720, 720)

        # 测试测试尺寸
        assert VideoSize.get_size('TEST_SMALL') == (480, 360)

    def test_get_size_invalid_preset(self):
        """测试获取无效的预设尺寸"""
        assert VideoSize.get_size('INVALID_SIZE') is None
        assert VideoSize.get_size('') is None

    def test_list_presets(self):
        """测试列出所有预设"""
        presets = VideoSize.list_presets()

        # 检查包含关键预设
        assert 'HD_720P' in presets
        assert 'PORTRAIT_1080P' in presets
        assert 'SQUARE_720' in presets
        assert 'TEST_SMALL' in presets

        # 检查格式正确
        for name, size in presets.items():
            assert isinstance(name, str)
            assert isinstance(size, tuple)
            assert len(size) == 2
            assert all(isinstance(dim, int) for dim in size)
            assert size[0] > 0 and size[1] > 0

    def test_preset_categories(self):
        """测试预设分类"""
        presets = VideoSize.list_presets()

        # 测试尺寸
        test_sizes = ['TEST_TINY', 'TEST_SMALL', 'TEST_MEDIUM']
        for preset in test_sizes:
            assert preset in presets

        # 横屏尺寸
        landscape_sizes = ['HD_720P', 'FULL_HD_1080P', 'UHD_4K']
        for preset in landscape_sizes:
            assert preset in presets

        # 竖屏尺寸
        portrait_sizes = ['PORTRAIT_TEST', 'PORTRAIT_720P', 'PORTRAIT_1080P']
        for preset in portrait_sizes:
            assert preset in presets

        # 方形尺寸
        square_sizes = ['SQUARE_TEST', 'SQUARE_720', 'SQUARE_1080']
        for preset in square_sizes:
            assert preset in presets


class TestParseVideoSize:
    """parse_video_size 函数的测试"""

    def test_parse_tuple(self):
        """测试解析元组输入"""
        assert parse_video_size((1280, 720)) == (1280, 720)
        assert parse_video_size((1920, 1080)) == (1920, 1080)
        assert parse_video_size((360, 640)) == (360, 640)

    def test_parse_preset_string(self):
        """测试解析预设名称字符串"""
        assert parse_video_size('HD_720P') == (1280, 720)
        assert parse_video_size('PORTRAIT_1080P') == (1080, 1920)
        assert parse_video_size('SQUARE_720') == (720, 720)
        assert parse_video_size('TEST_SMALL') == (480, 360)

    def test_parse_wx_h_string(self):
        """测试解析 WIDTHxHEIGHT 格式字符串"""
        assert parse_video_size('1280x720') == (1280, 720)
        assert parse_video_size('1920x1080') == (1920, 1080)
        assert parse_video_size('360x640') == (360, 640)

        # 测试大小写不敏感
        assert parse_video_size('1280X720') == (1280, 720)
        assert parse_video_size('1920x1080') == (1920, 1080)

    def test_parse_invalid_input(self):
        """测试解析无效输入"""
        with pytest.raises(ValueError):
            parse_video_size('invalid_format')

        with pytest.raises(ValueError):
            parse_video_size('1280x')  # 不完整的格式

        with pytest.raises(ValueError):
            parse_video_size('x720')  # 不完整的格式

        with pytest.raises(ValueError):
            parse_video_size('abcxdef')  # 非数字

        with pytest.raises(ValueError):
            parse_video_size(['1280', '720'])  # 错误的类型

        with pytest.raises(ValueError):
            parse_video_size(123)  # 错误的类型

    def test_parse_edge_cases(self):
        """测试边界情况"""
        # 最小尺寸
        assert parse_video_size('1x1') == (1, 1)

        # 大尺寸
        assert parse_video_size('7680x4320') == (7680, 4320)

        # 带空格的字符串
        assert parse_video_size('1280 x 720') == (1280, 720)

    def test_error_message_content(self):
        """测试错误消息内容"""
        with pytest.raises(ValueError) as exc_info:
            parse_video_size('invalid')

        error_msg = str(exc_info.value)
        assert "无法解析视频尺寸" in error_msg
        assert "支持的格式" in error_msg
        assert "tuple" in error_msg
        assert "预设名称" in error_msg
        assert "WIDTHxHEIGHT" in error_msg


class TestPrintAvailableSizes:
    """print_available_sizes 函数的测试"""

    def test_function_execution(self, capsys):
        """测试函数正常执行"""
        print_available_sizes()
        captured = capsys.readouterr()

        # 检查输出包含关键信息
        assert "可用的视频尺寸预设" in captured.out
        assert "测试尺寸" in captured.out
        assert "横屏尺寸" in captured.out
        assert "竖屏尺寸" in captured.out
        assert "方形尺寸" in captured.out
        assert "HD_720P" in captured.out
        assert "1280 x 720" in captured.out
