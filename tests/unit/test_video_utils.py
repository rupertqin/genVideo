"""
video_utils.py 模块的单元测试
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from moviepy import ImageClip

from genvideo.utils.video_utils import (
    cover_geometry,
    resize_and_position_image,
    calculate_image_scale,
    create_centered_video_frame,
    fit_frame,
)


class TestCoverGeometry:
    """cover_geometry / calculate_image_scale 的测试（覆盖式缩放）"""

    def test_landscape_source(self):
        """横图：按宽度方向放大（取较大比例，保证铺满）"""
        scale, new_w, new_h = cover_geometry((800, 600), (1280, 720))
        assert scale == pytest.approx(1.6)
        assert (new_w, new_h) == (1280, 960)

    def test_portrait_source(self):
        """竖图：按宽度方向放大"""
        scale, new_w, new_h = cover_geometry((600, 800), (1280, 720))
        assert scale == pytest.approx(1280 / 600)
        assert new_w == 1280
        assert new_h >= 720

    def test_square_source(self):
        """方图：按宽度方向放大"""
        scale, new_w, new_h = cover_geometry((500, 500), (1280, 720))
        assert scale == pytest.approx(2.56)
        assert (new_w, new_h) == (1280, 1280)

    def test_same_ratio(self):
        """宽高比一致时两个方向刚好铺满"""
        scale, new_w, new_h = cover_geometry((800, 450), (1280, 720))
        assert scale == pytest.approx(1.6)
        assert (new_w, new_h) == (1280, 720)

    def test_tiny_source(self):
        """极小图：放大到铺满"""
        scale, new_w, new_h = cover_geometry((1, 1), (1920, 1080))
        assert scale == pytest.approx(1920.0)
        assert (new_w, new_h) == (1920, 1920)

    def test_huge_source(self):
        """超大图：缩小到铺满"""
        scale, new_w, new_h = cover_geometry((4000, 3000), (640, 480))
        assert scale == pytest.approx(0.16)
        assert (new_w, new_h) == (640, 480)

    def test_result_covers_target(self):
        """结果尺寸两个方向都不小于目标（不会出现黑边）"""
        for img_size in [(800, 600), (600, 800), (500, 500), (1, 1), (4000, 3000)]:
            video_size = (1280, 720)
            _, new_w, new_h = cover_geometry(img_size, video_size)
            assert new_w >= video_size[0]
            assert new_h >= video_size[1]

    def test_zero_dimension_handling(self):
        """零尺寸会抛除零错误"""
        with pytest.raises(ZeroDivisionError):
            calculate_image_scale((0, 600), (1280, 720))

    def test_calculate_image_scale_matches_cover_geometry(self):
        """calculate_image_scale 与 cover_geometry 行为一致（兼容旧接口）"""
        assert calculate_image_scale((800, 600), (1280, 720)) == cover_geometry(
            (800, 600), (1280, 720)
        )


class TestFitFrame:
    """fit_frame 函数的测试"""

    def _marked_source(self, height=100, width=200):
        """构造一张只有正中有一块白色标记的图"""
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[height // 2 - 5:height // 2 + 5, width // 2 - 5:width // 2 + 5] = 255
        return img

    def test_output_shape_and_dtype(self):
        """输出尺寸等于目标尺寸，类型为 uint8"""
        frame = fit_frame(self._marked_source(), (100, 100))
        assert frame.shape == (100, 100, 3)
        assert frame.dtype == np.uint8

    def test_center_keeps_middle_marker(self):
        """居中裁剪保留画面中央的内容"""
        frame = fit_frame(self._marked_source(), (100, 100), position="center")
        assert (frame == 255).all(axis=2).sum() > 0

    def test_left_position_keeps_left_edge(self):
        """position=left 时输出左边缘来自源图最左侧"""
        source = np.zeros((100, 200, 3), dtype=np.uint8)
        source[:, 0:10] = 255  # 最左 10 像素为白
        source[:, 190:] = 128  # 最右 10 像素为灰

        frame = fit_frame(source, (100, 100), position="left")
        assert (frame[:, 0] == 255).all()

        frame_right = fit_frame(source, (100, 100), position="right")
        assert (frame_right[:, -1] == 128).all()

    def test_tuple_position(self):
        """支持 ("left", "top") 形式的二元组位置"""
        source = np.zeros((100, 200, 3), dtype=np.uint8)
        source[:, 0:10] = 255
        frame = fit_frame(source, (100, 100), position=("left", "top"))
        assert (frame[:, 0] == 255).all()

    def test_rgba_source_is_converted(self):
        """RGBA 源图被转成 RGB"""
        source = np.zeros((100, 100, 4), dtype=np.uint8)
        source[..., 3] = 255
        frame = fit_frame(source, (50, 50))
        assert frame.shape == (50, 50, 3)

    def test_no_upscale_when_already_matching(self):
        """源图与目标完全一致时不缩放"""
        source = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = fit_frame(source, (100, 100))
        assert frame.shape == (100, 100, 3)


class TestResizeAndPositionImage:
    """resize_and_position_image 函数的测试"""

    def _clip(self, height=60, width=80, duration=2.0):
        source = np.random.default_rng(0).integers(
            0, 255, (height, width, 3), dtype=np.uint8
        )
        return ImageClip(source, duration=duration)

    def test_output_size(self):
        """返回片段的尺寸为目标尺寸"""
        result = resize_and_position_image(self._clip(), (40, 30))
        assert result.size == (40, 30)

    def test_duration_preserved(self):
        """时长与原片段一致"""
        result = resize_and_position_image(self._clip(duration=3.5), (40, 30))
        assert result.duration == pytest.approx(3.5)

    def test_frame_shape(self):
        """帧尺寸与目标一致"""
        result = resize_and_position_image(self._clip(), (40, 30))
        assert result.frame_function(0).shape == (30, 40, 3)

    def test_frame_computed_once(self):
        """同一帧被复用（静态图片不做逐帧重算）"""
        result = resize_and_position_image(self._clip(), (40, 30))
        first = result.frame_function(0)
        assert result.frame_function(0) is first
        assert result.frame_function(1.9) is first

    def test_covers_without_letterbox(self):
        """源图比目标更宽时，输出被铺满而不是留黑边"""
        source = np.full((20, 200, 3), 200, dtype=np.uint8)
        result = resize_and_position_image(ImageClip(source, duration=1.0), (40, 30))
        frame = result.frame_function(0)
        assert frame.shape == (30, 40, 3)
        assert (frame > 150).all()  # 全部是源图内容，没有黑边


class TestCreateCenteredVideoFrame:
    """create_centered_video_frame 函数的测试"""

    @patch('genvideo.utils.video_utils.CompositeVideoClip')
    def test_create_centered_frame_basic(self, mock_composite):
        """测试基本的居中视频帧创建"""
        mock_clip = MagicMock()
        video_size = (1280, 720)

        create_centered_video_frame(mock_clip, video_size)

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
            with patch('genvideo.utils.video_utils.CompositeVideoClip') as mock_composite:
                video_size = (width, height)
                create_centered_video_frame(mock_clip, video_size)
                mock_composite.assert_called_once_with([mock_clip], size=video_size)
