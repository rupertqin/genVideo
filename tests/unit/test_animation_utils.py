"""
animation_utils.py 模块的单元测试 - 修复版本
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, Mock

from utils.animation_utils import (
    EasingCurve,
    AnimationConfig,
    apply_animation,
    get_random_animation_config
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
        # 在中点应该有特定的平滑曲线
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
        # 所有缓动函数都应该从0开始，到1结束
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
        # 缓动函数应该是单调递增的
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
            # 测试几个点的单调性
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
        easing_func = config.get_easing_function()

        assert easing_func == EasingCurve.ease_in_quad
        assert callable(easing_func)

    def test_get_easing_function_default(self):
        """测试获取默认缓动函数"""
        config = AnimationConfig()
        easing_func = config.get_easing_function()

        assert easing_func == EasingCurve.ease_in_out_quad

    def test_animation_type_constants(self):
        """测试动画类型常量"""
        assert hasattr(AnimationConfig, 'ZOOM_IN')
        assert hasattr(AnimationConfig, 'ZOOM_OUT')
        assert hasattr(AnimationConfig, 'PAN_LEFT')
        assert hasattr(AnimationConfig, 'PAN_RIGHT')
        assert hasattr(AnimationConfig, 'PAN_UP')
        assert hasattr(AnimationConfig, 'PAN_DOWN')
        assert hasattr(AnimationConfig, 'NONE')

    def test_parameter_validation(self):
        """测试参数验证（基本类型检查）"""
        # 正常参数
        config1 = AnimationConfig(intensity=0.0)
        config2 = AnimationConfig(intensity=1.0)

        assert config1.intensity == 0.0
        assert config2.intensity == 1.0

        # 边界值应该被接受（即使可能不理想）
        config3 = AnimationConfig(intensity=-0.1)
        assert config3.intensity == -0.1

        config4 = AnimationConfig(intensity=1.5)
        assert config4.intensity == 1.5


class TestApplyAnimation:
    """apply_animation 函数的测试"""

    def test_none_animation_type(self):
        """测试无动画类型"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        # 创建mock对象时设置必要的属性
        mock_resized = MagicMock()
        mock_positioned = MagicMock()

        # 设置链式调用
        mock_clip.resized.return_value = mock_resized
        mock_resized.with_position.return_value = mock_positioned

        # Mock CompositeVideoClip避免实际创建
        with patch('utils.animation_utils.CompositeVideoClip') as mock_composite:
            video_size = (1280, 720)
            config = AnimationConfig(animation_type=AnimationConfig.NONE)

            result = apply_animation(mock_clip, config, video_size)

            # 应该调用基本的缩放和居中
            mock_clip.resized.assert_called_once()
            mock_resized.with_position.assert_called_once_with("center")
            # CompositeVideoClip 应该被调用
            mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_zoom_in_animation(self, mock_composite):
        """测试放大动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        # Mock resize 函数
        def mock_resized_func(new_size=None, resize_func=None):
            if resize_func:
                # 模拟调用 resize 函数
                return MagicMock()
            return MagicMock()

        mock_clip.resized.side_effect = mock_resized_func

        mock_positioned = MagicMock()
        mock_clip.resized.return_value.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.ZOOM_IN, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)

        # 应该调用 CompositeVideoClip
        mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_zoom_out_animation(self, mock_composite):
        """测试缩小动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.ZOOM_OUT, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)

        mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_pan_left_animation(self, mock_composite):
        """测试向左平移动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.PAN_LEFT, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)

        # 应该设置动态位置
        mock_resized.with_position.assert_called_once()
        position_func = mock_resized.with_position.call_args[0][0]
        assert callable(position_func)
        mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_pan_right_animation(self, mock_composite):
        """测试向右平移动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.PAN_RIGHT, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)
        mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_pan_up_animation(self, mock_composite):
        """测试向上平移动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.PAN_UP, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)
        mock_composite.assert_called_once()

    @patch('utils.animation_utils.CompositeVideoClip')
    def test_pan_down_animation(self, mock_composite):
        """测试向下平移动画"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        config = AnimationConfig(animation_type=AnimationConfig.PAN_DOWN, intensity=0.1)

        result = apply_animation(mock_clip, config, video_size)
        mock_composite.assert_called_once()

    def test_unknown_animation_type(self):
        """测试未知的动画类型"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        with patch('utils.animation_utils.CompositeVideoClip') as mock_composite:
            video_size = (1280, 720)
            config = AnimationConfig(animation_type="unknown_type")

            result = apply_animation(mock_clip, config, video_size)

            # 应该回退到基本处理
            mock_clip.resized.assert_called_once()
            mock_composite.assert_called_once()

    def test_custom_easing(self):
        """测试自定义缓动函数"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)
        mock_clip.duration = 5.0

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized

        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        with patch('utils.animation_utils.CompositeVideoClip') as mock_composite:
            video_size = (1280, 720)
            config = AnimationConfig(
                animation_type=AnimationConfig.ZOOM_IN,
                easing="ease_in_cubic"
            )

            result = apply_animation(mock_clip, config, video_size)

            # 应该使用自定义缓动函数
            assert config.get_easing_function() == EasingCurve.ease_in_cubic
            mock_composite.assert_called_once()


class TestGetRandomAnimationConfig:
    """get_random_animation_config 函数的测试"""

    @patch('random.choice')
    def test_basic_random_config(self, mock_choice):
        """测试基本的随机配置生成"""
        # Mock random.choice 返回 ZOOM_IN
        mock_choice.return_value = AnimationConfig.ZOOM_IN

        config = get_random_animation_config()

        assert config.animation_type == AnimationConfig.ZOOM_IN
        assert config.intensity == 0.1
        assert config.easing == "ease_in_out_quad"

    def test_custom_intensity(self):
        """测试自定义强度"""
        config = get_random_animation_config(intensity=0.3)

        assert config.intensity == 0.3

    def test_custom_easing(self):
        """测试自定义缓动函数"""
        config = get_random_animation_config(easing="ease_in_quad")

        assert config.easing == "ease_in_quad"

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

        # 测试每种类型都能被选择
        for expected_type in animation_types:
            mock_choice.return_value = expected_type
            config = get_random_animation_config()
            assert config.animation_type == expected_type

    def test_parameter_passing(self):
        """测试参数正确传递"""
        config = get_random_animation_config(
            intensity=0.25,
            easing="ease_out_cubic"
        )

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
