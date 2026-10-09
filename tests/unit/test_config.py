"""
config.py 模块的单元测试 - 修复版本
"""
import os

import pytest
from genvideo.config import (
    DEFAULT_CONFIG,
    VideoSize,
    default_config_path,
    load_config,
    merge_config,
    parse_color,
    parse_duration,
    parse_video_size,
    print_available_sizes,
    subtitle_options,
)


class TestVideoSize:
    """VideoSize 类的测试"""

    def test_get_size_valid_preset(self):
        """测试获取有效的预设尺寸"""
        # 测试横屏尺寸
        assert VideoSize.get_size('HD_720P') == (1280, 720)
        assert VideoSize.get_size('HD_1080P') == (1920, 1080)

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
        landscape_sizes = ['HD_720P', 'HD_1080P', 'UHD_4K']
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


class TestMergeConfig:
    """merge_config 函数的测试"""

    def test_override_scalar(self):
        """标量被覆盖"""
        merged = merge_config({"a": 1, "b": 2}, {"b": 9})
        assert merged == {"a": 1, "b": 9}

    def test_nested_merge(self):
        """嵌套字典逐层合并，未提到的键保留"""
        base = {"sub": {"size": None, "bottom": 0.08, "stroke": 3}}
        merged = merge_config(base, {"sub": {"bottom": 0.2}})
        assert merged["sub"] == {"size": None, "bottom": 0.2, "stroke": 3}

    def test_does_not_mutate_inputs(self):
        """不修改入参"""
        base = {"sub": {"bottom": 0.08}}
        override = {"sub": {"bottom": 0.2}}
        merge_config(base, override)
        assert base == {"sub": {"bottom": 0.08}}
        assert override == {"sub": {"bottom": 0.2}}

    def test_empty_override(self):
        """空覆盖返回原配置的副本"""
        base = {"a": 1}
        assert merge_config(base, None) == base
        assert merge_config(base, {}) == base

    def test_non_dict_replaces_dict(self):
        """覆盖值不是字典时直接替换"""
        assert merge_config({"sub": {"a": 1}}, {"sub": None}) == {"sub": None}


class TestLoadConfig:
    """load_config 函数的测试"""

    def test_missing_file_returns_defaults(self, tmp_path):
        """配置文件不存在时返回内置默认配置"""
        config = load_config(str(tmp_path / "nope.yaml"))
        assert config == DEFAULT_CONFIG

    def test_default_path_points_to_shipped_config(self):
        """默认路径指向项目内的 config.yaml"""
        assert default_config_path().endswith("config.yaml")
        assert os.path.exists(default_config_path())

    def test_shipped_config_is_loadable(self):
        """仓库自带的 config.yaml 能正常解析，且各区块的键齐全

        不断言具体取值：config.yaml 是给用户改的，取值可以自定义。
        """
        config = load_config(default_config_path())
        for section, defaults in DEFAULT_CONFIG.items():
            assert section in config, f"缺少区块: {section}"
            assert set(defaults) <= set(config[section]), f"{section} 缺少键"

    def test_partial_override_merges_with_defaults(self, tmp_path):
        """只写部分键时其余键回落默认值"""
        path = tmp_path / "config.yaml"
        path.write_text("subtitle:\n  size: 48\n  bottom: 0.2\n", encoding="utf-8")

        config = load_config(str(path))
        assert config["subtitle"]["size"] == 48
        assert config["subtitle"]["bottom"] == 0.2
        assert config["subtitle"]["stroke_width"] == DEFAULT_CONFIG["subtitle"]["stroke_width"]
        assert config["video"] == DEFAULT_CONFIG["video"]

    def test_empty_file_returns_defaults(self, tmp_path):
        """空配置文件等同默认"""
        path = tmp_path / "config.yaml"
        path.write_text("", encoding="utf-8")
        assert load_config(str(path)) == DEFAULT_CONFIG

    def test_invalid_yaml_raises(self, tmp_path):
        """YAML 语法错误时抛出带路径的 RuntimeError"""
        path = tmp_path / "config.yaml"
        path.write_text("subtitle: [未闭合\n", encoding="utf-8")

        with pytest.raises(RuntimeError) as exc:
            load_config(str(path))
        assert "config.yaml" in str(exc.value)

    def test_non_mapping_top_level_raises(self, tmp_path):
        """顶层不是键值对时抛错"""
        path = tmp_path / "config.yaml"
        path.write_text("- a\n- b\n", encoding="utf-8")

        with pytest.raises(RuntimeError):
            load_config(str(path))


class TestParseDuration:
    """parse_duration 函数的测试"""

    @pytest.mark.parametrize("value,expected", [
        (180, 180.0),
        (180.5, 180.5),
        (0, 0.0),
        ("180", 180.0),
        ("180.5", 180.5),
        (" 180 ", 180.0),
        ("180s", 180.0),
        ("3m", 180.0),
        ("1.5h", 5400.0),
        ("2 min", 120.0),
        ("1hr", 3600.0),
        ("3:00", 180.0),
        ("03:00", 180.0),
        ("0:07", 7.0),
        ("00:03:00", 180.0),
        ("1:02:03", 3723.0),
    ])
    def test_supported_formats(self, value, expected):
        """秒 / 带单位 / 分:秒 / 时:分:秒 都能解析"""
        assert parse_duration(value) == pytest.approx(expected)

    @pytest.mark.parametrize("value,expected", [
        ("00:03:00.250", 180.25),
        ("0:00:03.5", 3.5),
        ("1:02:03.456", 3723.456),
        ("0.001", 0.001),
        ("7.5", 7.5),
    ])
    def test_millisecond_precision(self, value, expected):
        """毫秒精度不丢"""
        assert parse_duration(value) == pytest.approx(expected, abs=1e-9)

    @pytest.mark.parametrize("value", [None, "", "   ", "null", "None", "off", "OFF"])
    def test_unset_returns_none(self, value):
        """未配置时返回 None（表示不限制）；也接受 null/none/off 写法"""
        assert parse_duration(value) is None

    @pytest.mark.parametrize("bad", [
        "abc", "3x", "3:xx", "1:2:3:4", "-5", -1, "3:00:00:00", True, False, "s", "m5", "3m:", ":3",
    ])
    def test_invalid_raises(self, bad):
        """无法解析或为负时抛 ValueError"""
        with pytest.raises(ValueError):
            parse_duration(bad)

    def test_error_message_mentions_value(self):
        """报错信息里带上原值，便于定位"""
        with pytest.raises(ValueError) as exc:
            parse_duration("1:2:3:4")
        assert "1:2:3:4" in str(exc.value)


class TestParseColor:
    """parse_color 函数的测试"""

    def test_hex_rgb_with_alpha_argument(self):
        """#RRGGBB 配合 alpha 参数"""
        assert parse_color("#FFFFFF", 150) == (255, 255, 255, 150)

    def test_hex_rgb_default_alpha(self):
        """不给 alpha 时默认 255"""
        assert parse_color("#000000") == (0, 0, 0, 255)

    def test_hex_rgba(self):
        """#RRGGBBAA 自带透明度"""
        assert parse_color("#11223344") == (17, 34, 51, 68)

    def test_list_rgb(self):
        """[r, g, b] 列表"""
        assert parse_color([10, 20, 30], 0) == (10, 20, 30, 0)

    def test_list_rgba(self):
        """[r, g, b, a] 列表"""
        assert parse_color([10, 20, 30, 40]) == (10, 20, 30, 40)

    def test_none_returns_none(self):
        """None 返回 None"""
        assert parse_color(None) is None

    @pytest.mark.parametrize("bad", ["red", "#FFF", "#GGGGGG", [1, 2], [1, 2, 3, 4, 5], 123])
    def test_invalid_raises(self, bad):
        """无法解析时抛 ValueError"""
        with pytest.raises(ValueError):
            parse_color(bad)


class TestSubtitleOptions:
    """subtitle_options 函数的测试"""

    def test_defaults(self):
        """默认参数（无 config 时全部回落内置默认）"""
        options = subtitle_options(None)
        assert options["font_path"] is None
        assert options["font_size"] is None
        assert options["bottom_ratio"] == pytest.approx(0.08)
        assert options["max_width_ratio"] == pytest.approx(0.9)
        assert options["line_spacing"] == pytest.approx(1.25)
        assert options["stroke_width"] == 3
        assert options["strip_punct"] is False
        assert options["text_color"] == (255, 255, 255, 255)
        assert options["box_color"] == (0, 0, 0, 150)

    def test_reads_full_config(self, tmp_path):
        """从 load_config 的结果中取出字幕参数"""
        path = tmp_path / "config.yaml"
        path.write_text(
            "subtitle:\n"
            "  size: 40\n"
            "  bottom: 0.15\n"
            "  max_width: 0.8\n"
            "  line_spacing: 1.4\n"
            "  stroke_width: 5\n"
            "  strip_punct: true\n"
            "  text_color: '#FFCC00'\n"
            "  box_color: [0, 0, 0]\n"
            "  box_alpha: 0\n",
            encoding="utf-8",
        )
        options = subtitle_options(load_config(str(path)))

        assert options["font_size"] == 40
        assert options["bottom_ratio"] == pytest.approx(0.15)
        assert options["max_width_ratio"] == pytest.approx(0.8)
        assert options["line_spacing"] == pytest.approx(1.4)
        assert options["stroke_width"] == 5
        assert options["strip_punct"] is True
        assert options["text_color"] == (255, 204, 0, 255)
        assert options["box_color"] == (0, 0, 0, 0)

    def test_partial_config_uses_defaults_for_rest(self):
        """只给部分键时其余回落默认"""
        options = subtitle_options({"subtitle": {"size": 32}})
        assert options["font_size"] == 32
        assert options["box_color"] == (0, 0, 0, 150)
        assert options["strip_punct"] is False

    def test_output_is_render_kwargs(self):
        """返回的键名与 render_subtitle_frame 的参数一致"""
        options = subtitle_options(None)
        assert set(options) == {
            "font_path", "font_size", "font_size_landscape",
            "bottom_ratio", "bottom_ratio_landscape",
            "max_width_ratio", "line_spacing", "stroke_width", "strip_punct",
            "text_color", "box_color",
        }
