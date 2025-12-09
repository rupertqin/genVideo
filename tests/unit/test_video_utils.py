"""
video_utils.py 模块的单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from utils.video_utils import (
    resize_and_position_image,
    calculate_image_scale,
    create_centered_video_frame
)


class TestCalculateImageScale:
    """calculate_image_scale 函数的测试"""

    def test_scale_calculation_landscape(self):
        """测试横屏图片的缩放计算"""
        img_size = (800, 600)
        video_size = (1280, 720)

        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        # 视频更宽，需要按高度缩放
        expected_scale = 720 / 600  # 1.2
        expected_w = int(800 * expected_scale)  # 960
        expected_h = 720

        assert abs(scale - expected_scale) < 0.01
        assert new_w == expected_w
        assert new_h == expected_h

    def test_scale_calculation_portrait(self):
        """测试竖屏图片的缩放计算"""
        img_size = (600, 800)
        video_size = (1280, 720)

        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        # 视频更宽，需要按高度缩放
        expected_scale = 720 / 800  # 0.9
        expected_w = int(600 * expected_scale)  # 540
        expected_h = 720

        assert abs(scale - expected_scale) < 0.01
        assert new_w == expected_w
        assert new_h == expected_h

    def test_scale_calculation_square(self):
        """测试方形图片的缩放计算"""
        img_size = (500, 500)
        video_size = (1280, 720)

        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        # 按较小的比例缩放（宽度）
        expected_scale = 1280 / 500  # 2.56
        expected_w = 1280
        expected_h = int(500 * expected_scale)  # 1280

        assert abs(scale - expected_scale) < 0.01
        assert new_w == expected_w
        assert new_h == expected_h

    def test_scale_calculation_same_ratio(self):
        """测试相同宽高比的缩放计算"""
        img_size = (800, 450)
        video_size = (1280, 720)

        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        # 宽高比相同，应该按最小比例缩放
        expected_scale = min(1280 / 800, 720 / 450)  # 1.6
        expected_w = 1280
        expected_h = 720

        assert abs(scale - expected_scale) < 0.01
        assert new_w == expected_w
        assert new_h == expected_h

    def test_scale_calculation_edge_cases(self):
        """测试边界情况的缩放计算"""
        # 极小图片
        img_size = (1, 1)
        video_size = (1920, 1080)
        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        assert scale == 1080.0  # 按较大维度
        assert new_w == 1080
        assert new_h == 1080

        # 极大图片
        img_size = (4000, 3000)
        video_size = (640, 480)
        scale, new_w, new_h = calculate_image_scale(img_size, video_size)

        assert abs(scale - (640/4000)) < 0.01  # 按宽度缩放
        assert new_w == 640
        assert new_h == 480


class TestResizeAndPositionImage:
    """resize_and_position_image 函数的测试"""

    def test_resize_and_position_basic(self):
        """测试基本的缩放和位置设置"""
        # 创建模拟的 clip
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)

        # Mock 各种方法
        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized
        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)

        result = resize_and_position_image(mock_clip, video_size)

        # 检查调用
        mock_clip.resized.assert_called_once()
        mock_resized.with_position.assert_called_once_with("center")

    def test_resize_and_position_custom_position(self):
        """测试自定义位置的缩放和位置设置"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)

        mock_resized = MagicMock()
        mock_clip.resized.return_value = mock_resized
        mock_positioned = MagicMock()
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)
        custom_position = ("left", "top")

        result = resize_and_position_image(mock_clip, video_size, position=custom_position)

        mock_resized.with_position.assert_called_once_with(custom_position)

    @patch('utils.video_utils.CompositeVideoClip')
    def test_resize_and_position_composition(self, mock_composite):
        """测试最终的合成步骤"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)

        mock_resized = MagicMock()
        mock_positioned = MagicMock()
        mock_clip.resized.return_value = mock_resized
        mock_resized.with_position.return_value = mock_positioned

        video_size = (1280, 720)

        result = resize_and_position_image(mock_clip, video_size)

        # 检查 CompositeVideoClip 被正确调用
        mock_composite.assert_called_once_with([mock_positioned], size=video_size)


class TestCreateCenteredVideoFrame:
    """create_centered_video_frame 函数的测试"""

    @patch('utils.video_utils.CompositeVideoClip')
    def test_create_centered_frame_basic(self, mock_composite):
        """测试基本的居中视频帧创建"""
        mock_clip = MagicMock()
        video_size = (1280, 720)

        result = create_centered_video_frame(mock_clip, video_size)

        # 检查 CompositeVideoClip 被正确调用
        mock_composite.assert_called_once_with([mock_clip], size=video_size)

    def test_create_centered_frame_different_sizes(self):
        """测试不同尺寸的居中视频帧"""
        mock_clip = MagicMock()

        test_cases = [
            (640, 480),
            (1920, 1080),
            (360, 640),  # 竖屏
            (720, 720),  # 方形
        ]

        for width, height in test_cases:
            with patch('utils.video_utils.CompositeVideoClip') as mock_composite:
                video_size = (width, height)
                create_centered_video_frame(mock_clip, video_size)
                mock_composite.assert_called_once_with([mock_clip], size=video_size)

    def test_integration_scenario(self):
        """测试集成场景的模拟"""
        # 模拟一个完整的视频处理流程
        mock_clip = MagicMock()
        mock_clip.size = (1024, 768)

        # 模拟缩放计算
        with patch('utils.video_utils.calculate_image_scale') as mock_calc:
            mock_calc.return_value = (1.25, 1280, 960)

            mock_resized = MagicMock()
            mock_clip.resized.return_value = mock_resized

            mock_positioned = MagicMock()
            mock_resized.with_position.return_value = mock_positioned

            # 执行处理
            result = resize_and_position_image(mock_clip, (1280, 720))

            # 验证计算被调用
            mock_calc.assert_called_once_with((1024, 768), (1280, 720))

            # 验证缩放被调用
            mock_clip.resized.assert_called_once_with(new_size=(1280, 960))

    def test_error_handling(self):
        """测试错误处理"""
        mock_clip = MagicMock()
        mock_clip.size = (800, 600)

        # 模拟 resize 方法抛出异常
        mock_clip.resized.side_effect = Exception("Resize failed")

        video_size = (1280, 720)

        with pytest.raises(Exception):
            resize_and_position_image(mock_clip, video_size)

    def test_zero_dimension_handling(self):
        """测试零维度的处理"""
        mock_clip = MagicMock()
        mock_clip.size = (0, 600)

        video_size = (1280, 720)

        # 这可能会引发除零错误或产生意外结果
        with pytest.raises((ZeroDivisionError, ValueError)):
            scale, new_w, new_h = calculate_image_scale((0, 600), video_size)
