"""
animation_utils.py 模块的单元测试
"""
import numpy as np
import pytest
from unittest.mock import patch
from moviepy import ImageClip, VideoClip

from utils.animation_utils import (
    EasingCurve,
    AnimationConfig,
    apply_animation,
    get_random_animation_config,
)


class TestEasingCurve:
    """EasingCurve 类的测试"""

    def test_linear(self):
        """测试线性缓动"""
        assert EasingCurve.linear(0.0) == 0.0
        assert EasingCurve.linear(0.5) == 0.5
        assert EasingCurve.linear(1.0) == 1.0
        assert EasingCurve.linear(2.0) == 2.0  # 允许超出范围

    def test_ease_in_quad(self):
        """测试二次缓入"""
        assert EasingCurve.ease_in_quad(0.0) == 0.0
        assert abs(EasingCurve.ease_in_quad(0.5) - 0.25) < 0.001
        assert EasingCurve.ease_in_quad(1.0) == 1.0

    def test_ease_out_quad(self):
        """测试二次缓出"""
        assert EasingCurve.ease_out_quad(0.0) == 0.0
        assert abs(EasingCurve.ease_out_quad(0.5) - 0.75) < 0.001
        assert EasingCurve.ease_out_quad(1.0) == 1.0

    def test_ease_in_out_quad(self):
        """测试二次缓入缓出"""
        assert EasingCurve.ease_in_out_quad(0.0) == 0.0
        assert EasingCurve.ease_in_out_quad(1.0) == 1.0
        mid_value = EasingCurve.ease_in_out_quad(0.5)
        assert 0.0 < mid_value < 1.0

    def test_ease_in_cubic(self):
        """测试三次缓入"""
        assert EasingCurve.ease_in_cubic(0.0) == 0.0
        assert abs(EasingCurve.ease_in_cubic(0.5) - 0.125) < 0.001
        assert EasingCurve.ease_in_cubic(1.0) == 1.0

    def test_ease_out_cubic(self):
        """测试三次缓出"""
        assert EasingCurve.ease_out_cubic(0.0) == 0.0
        assert abs(EasingCurve.ease_out_cubic(0.5) - 0.875) < 0.001
        assert EasingCurve.ease_out_cubic(1.0) == 1.0

    def test_ease_in_out_cubic(self):
        """测试三次缓入缓出"""
        assert EasingCurve.ease_in_out_cubic(0.0) == 0.0
        assert EasingCurve.ease_in_out_cubic(1.0) == 1.0
        mid_value = EasingCurve.ease_in_out_cubic(0.5)
        assert 0.0 < mid_value < 1.0

    def test_easing_properties(self):
        """测试缓动函数的基本属性"""
        easing_functions = [
            EasingCurve.linear,
            EasingCurve.ease_in_quad,
            EasingCurve.ease_out_quad,
            EasingCurve.ease_in_out_quad,
            EasingCurve.ease_in_cubic,
            EasingCurve.ease_out_cubic,
            EasingCurve.ease_in_out_cubic
        ]

        for func in easing_functions:
            assert func(0.0) == 0.0
            assert func(1.0) == 1.0

    def test_easing_monotonicity(self):
        """测试缓动函数的单调性"""
        easing_functions = [
            EasingCurve.linear,
            EasingCurve.ease_in_quad,
            EasingCurve.ease_out_quad,
            EasingCurve.ease_in_out_quad,
            EasingCurve.ease_in_cubic,
            EasingCurve.ease_out_cubic,
            EasingCurve.ease_in_out_cubic
        ]

        for func in easing_functions:
            values = [func(i / 10) for i in range(11)]
            for i in range(len(values) - 1):
                assert values[i] <= values[i + 1], f"Function {func.__name__} is not monotonic"


class TestAnimationConfig:
    """AnimationConfig 类的测试"""

    def test_initialization(self):
        """测试初始化"""
        config = AnimationConfig()

        assert config.animation_type == AnimationConfig.ZOOM_IN
        assert config.intensity == 0.1
        assert config.easing == "ease_in_out_quad"
        assert config.duration is None

    def test_initialization_with_parameters(self):
        """测试带参数的初始化"""
        config = AnimationConfig(
            animation_type=AnimationConfig.ZOOM_OUT,
            intensity=0.5,
            easing="ease_in_cubic",
            duration=2.0
        )

        assert config.animation_type == AnimationConfig.ZOOM_OUT
        assert config.intensity == 0.5
        assert config.easing == "ease_in_cubic"
        assert config.duration == 2.0

    def test_get_easing_function(self):
        """测试获取缓动函数"""
        config = AnimationConfig(easing="ease_in_quad")
        assert config.get_easing_function() == EasingCurve.ease_in_quad

    def test_get_easing_function_default(self):
        """测试获取默认缓动函数"""
        assert AnimationConfig().get_easing_function() == EasingCurve.ease_in_out_quad

    def test_unknown_easing_falls_back_to_linear(self):
        """未知缓动名回退到线性"""
        config = AnimationConfig(easing="not_a_curve")
        assert config.get_easing_function() == EasingCurve.linear

    def test_animation_type_constants(self):
        """测试动画类型常量"""
        for name in ('ZOOM_IN', 'ZOOM_OUT', 'PAN_LEFT', 'PAN_RIGHT', 'PAN_UP', 'PAN_DOWN', 'NONE'):
            assert hasattr(AnimationConfig, name)

    def test_parameter_validation(self):
        """测试参数验证（基本类型检查）"""
        assert AnimationConfig(intensity=0.0).intensity == 0.0
        assert AnimationConfig(intensity=1.0).intensity == 1.0
        # 边界值应该被接受（即使可能不理想）
        assert AnimationConfig(intensity=-0.1).intensity == -0.1
        assert AnimationConfig(intensity=1.5).intensity == 1.5


class TestApplyAnimation:
    """apply_animation 函数的测试（用真实帧验证，不再 mock MoviePy 内部）"""

    VIDEO_SIZE = (32, 24)

    def _clip(self, height=60, width=160, duration=4.0):
        """黑底 + 正中一块白色方块，便于观察缩放与位移"""
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[height // 2 - 12:height // 2 + 12, width // 2 - 12:width // 2 + 12] = 255
        return ImageClip(img, duration=duration)

    def _apply(self, animation_type, intensity=1.0, **kwargs):
        config = AnimationConfig(
            animation_type=animation_type, intensity=intensity, **kwargs
        )
        return apply_animation(self._clip(), config, self.VIDEO_SIZE)

    @staticmethod
    def _light_pixels(frame):
        """统计亮像素数量（近似画面内容面积）"""
        return int((frame > 128).all(axis=2).sum())

    def test_returns_video_clip(self):
        """返回带目标尺寸与时长的新片段"""
        result = self._apply(AnimationConfig.ZOOM_IN)
        assert isinstance(result, VideoClip)
        assert result.size == self.VIDEO_SIZE
        assert result.duration == pytest.approx(4.0)

    def test_frame_shape_and_dtype(self):
        """帧尺寸与类型正确"""
        frame = self._apply(AnimationConfig.ZOOM_IN).frame_function(1.0)
        assert frame.shape == (24, 32, 3)
        assert frame.dtype == np.uint8

    def test_none_type_is_static_and_computed_once(self):
        """无动画时等价于静态裁剪，且只算一次"""
        result = self._apply(AnimationConfig.NONE)
        first = result.frame_function(0)
        assert first.shape == (24, 32, 3)
        assert result.frame_function(3.9) is first

    def test_unknown_type_falls_back_to_static(self):
        """未知动画类型回退为静态裁剪"""
        result = self._apply("unknown_type")
        assert result.frame_function(1.0) is result.frame_function(0)

    def test_zoom_in_makes_content_larger(self):
        """放大：结束帧内容面积大于开始帧"""
        result = self._apply(AnimationConfig.ZOOM_IN)
        start = self._light_pixels(result.frame_function(0))
        end = self._light_pixels(result.frame_function(4.0))

        assert start > 0
        assert end > start

    def test_zoom_out_shrinks_content(self):
        """缩小：结束帧内容面积小于开始帧"""
        result = self._apply(AnimationConfig.ZOOM_OUT)
        start = self._light_pixels(result.frame_function(0))
        end = self._light_pixels(result.frame_function(4.0))

        assert start > end

    def test_zoom_changes_over_time(self):
        """缩放过程中画面持续变化"""
        result = self._apply(AnimationConfig.ZOOM_IN)
        assert not np.array_equal(result.frame_function(0), result.frame_function(2.0))

    def test_zoom_zero_intensity_is_stable(self):
        """强度为 0 时画面不变"""
        result = self._apply(AnimationConfig.ZOOM_IN, intensity=0.0)
        assert np.array_equal(result.frame_function(0), result.frame_function(4.0))

    @pytest.mark.parametrize("animation_type", [
        AnimationConfig.PAN_LEFT,
        AnimationConfig.PAN_RIGHT,
        AnimationConfig.PAN_UP,
        AnimationConfig.PAN_DOWN,
    ])
    def test_pan_moves_picture(self, animation_type):
        """平移：形状正确且画面随时间移动"""
        result = self._apply(animation_type)
        first = result.frame_function(0)
        last = result.frame_function(4.0)

        assert first.shape == (24, 32, 3)
        assert not np.array_equal(first, last)

    def test_pan_opposite_directions_differ(self):
        """左右平移到同一时刻的取景不同"""
        left = self._apply(AnimationConfig.PAN_LEFT).frame_function(4.0)
        right = self._apply(AnimationConfig.PAN_RIGHT).frame_function(4.0)
        assert not np.array_equal(left, right)

    def test_pan_is_pure_numpy_slice(self):
        """平移窗口恒等于输出尺寸：各帧是同一张底图的切片（共享内存，不经过 PIL）"""
        result = self._apply(AnimationConfig.PAN_LEFT)
        first = result.frame_function(1.0)
        later = result.frame_function(3.0)
        assert np.shares_memory(first, later)

    def test_zoom_frames_are_independent(self):
        """缩放需要逐帧重采样：各帧是彼此独立的新数组"""
        result = self._apply(AnimationConfig.ZOOM_IN)
        first = result.frame_function(1.0)
        later = result.frame_function(3.0)
        assert not np.shares_memory(first, later)

    def test_custom_easing_accepted(self):
        """自定义缓动函数可用"""
        result = self._apply(AnimationConfig.ZOOM_IN, easing="ease_in_cubic")
        assert result.frame_function(0).shape == (24, 32, 3)


class TestGetRandomAnimationConfig:
    """get_random_animation_config 函数的测试"""

    @patch('random.choice')
    def test_basic_random_config(self, mock_choice):
        """测试基本的随机配置生成"""
        mock_choice.return_value = AnimationConfig.ZOOM_IN

        config = get_random_animation_config()

        assert config.animation_type == AnimationConfig.ZOOM_IN
        assert config.intensity == 0.1
        assert config.easing == "ease_in_out_quad"

    def test_custom_intensity(self):
        """测试自定义强度"""
        assert get_random_animation_config(intensity=0.3).intensity == 0.3

    def test_custom_easing(self):
        """测试自定义缓动函数"""
        assert get_random_animation_config(easing="ease_in_quad").easing == "ease_in_quad"

    @patch('random.choice')
    def test_different_animation_types(self, mock_choice):
        """测试不同的动画类型"""
        animation_types = [
            AnimationConfig.ZOOM_IN,
            AnimationConfig.ZOOM_OUT,
            AnimationConfig.PAN_LEFT,
            AnimationConfig.PAN_RIGHT,
            AnimationConfig.PAN_UP,
            AnimationConfig.PAN_DOWN,
        ]

        for expected_type in animation_types:
            mock_choice.return_value = expected_type
            config = get_random_animation_config()
            assert config.animation_type == expected_type

    def test_parameter_passing(self):
        """测试参数正确传递"""
        config = get_random_animation_config(intensity=0.25, easing="ease_out_cubic")
        assert config.intensity == 0.25
        assert config.easing == "ease_out_cubic"

    @patch('random.choice')
    def test_function_existence(self, mock_choice):
        """测试函数存在且可调用"""
        mock_choice.return_value = AnimationConfig.ZOOM_IN

        config = get_random_animation_config()

        assert isinstance(config, AnimationConfig)
        assert hasattr(config, 'animation_type')
        assert hasattr(config, 'intensity')
        assert hasattr(config, 'easing')
