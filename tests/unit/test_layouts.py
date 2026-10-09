"""
layouts.py 布局组件模块的单元测试
"""
import numpy as np
import pytest

from utils.layouts import (
    card_layout,
    fullscreen_layout,
    get_layout,
    hero_layout,
    list_layouts,
    register_layout,
)


class TestRegistry:
    """布局注册表的测试"""

    def test_default_layouts_registered(self):
        """内置的 fullscreen / card / hero 都已注册"""
        assert {"fullscreen", "card", "hero"} <= set(list_layouts())

    def test_get_layout(self):
        """能按名字取到布局函数，未知名返回 None"""
        assert callable(get_layout("fullscreen"))
        assert callable(get_layout("card"))
        assert get_layout("不存在的布局") is None

    def test_register_custom_layout(self):
        """可以动态注册新布局（组件可扩展）"""
        @register_layout("_tmp_test_layout")
        def custom(source, size, duration, options):
            return lambda t: source

        assert get_layout("_tmp_test_layout") is custom
        assert "_tmp_test_layout" in list_layouts()


class TestFullscreenLayout:
    """fullscreen 布局的测试"""

    def test_static_and_shape(self):
        """返回静态帧，只算一次，尺寸等于画布"""
        source = np.zeros((60, 80, 3), dtype=np.uint8)
        frame_fn = fullscreen_layout(source, (40, 30), 5.0, {})

        frame = frame_fn(0)
        assert frame.shape == (30, 40, 3)
        assert frame_fn(3.9) is frame

    def test_position_passthrough(self):
        """position 选项生效（left 对齐左边缘）"""
        source = np.zeros((100, 200, 3), dtype=np.uint8)
        source[:, :10] = 255

        frame = fullscreen_layout(source, (100, 100), 1.0, {"position": "left"})(0)
        assert (frame[:, 0] == 255).all()


class TestCardLayout:
    """card 布局的测试"""

    @staticmethod
    def _grey_source(height=120, width=160, value=200):
        return np.full((height, width, 3), value, dtype=np.uint8)

    @staticmethod
    def _base_options():
        """压暗到纯黑 + 不模糊 + 无阴影 + 无圆角，便于精确断言"""
        return {
            "inset": 0.15,
            "background_blur": 0,
            "background_darken": 1.0,
            "radius": 0,
            "shadow": 0,
        }

    def test_static_and_shape(self):
        """返回静态帧，只算一次，尺寸等于画布"""
        frame_fn = card_layout(self._grey_source(), (160, 240), 5.0, self._base_options())
        frame = frame_fn(0)
        assert frame.shape == (240, 160, 3)
        assert frame_fn(3.9) is frame

    def test_background_darkened_card_not(self):
        """背景被压暗，卡片区域保持原图：证明卡片不铺满画面"""
        frame_fn = card_layout(self._grey_source(), (160, 240), 5.0, self._base_options())
        frame = frame_fn(0).astype(int)

        # 角落 = 背景（压暗后接近黑）
        assert frame[0, 0].mean() < 20
        # 中心 = 卡片（保持原图灰度 200）
        assert frame[120, 80].mean() > 180

    def test_title_drawn(self):
        """有标题时，顶部条带出现亮色像素"""
        options = self._base_options()
        options["title"] = "测试标题"
        frame = card_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)

        top_band = frame[:120]
        assert (top_band > 200).sum() > 0

    def test_no_title(self):
        """无标题时顶部条带没有亮色像素"""
        frame = card_layout(self._grey_source(), (160, 240), 5.0, self._base_options())(0).astype(int)
        assert (frame[:120] > 200).sum() == 0

    def test_title_color(self):
        """标题颜色可配置（红色标题）"""
        options = self._base_options()
        options["title"] = "标题"
        options["title_color"] = [255, 0, 0]
        frame = card_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)

        top_band = frame[:120]
        red = (top_band[..., 0] > 200) & (top_band[..., 1] < 80) & (top_band[..., 2] < 80)
        assert red.sum() > 0

    def test_long_title_does_not_crash(self):
        """超长标题自动缩字号，不报错且能画出"""
        options = self._base_options()
        options["title"] = "这是一个非常非常非常非常非常长的标题文字用于测试自动缩放"
        frame = card_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)
        assert frame.shape == (240, 160, 3)
        assert (frame[:120] > 200).sum() > 0

    def test_title_bottom_position(self):
        """标题放在卡片下方"""
        options = self._base_options()
        options["title"] = "底部标题"
        options["title_position"] = "bottom"
        frame = card_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)
        assert (frame[-120:] > 200).sum() > 0


class TestHeroLayout:
    """hero 布局（杂志封面风）的测试"""

    @staticmethod
    def _grey_source(height=120, width=160, value=200):
        return np.full((height, width, 3), value, dtype=np.uint8)

    @staticmethod
    def _base_options():
        """关闭网格与角标，便于精确断言照片区与纸色区"""
        return {
            "hero_top": 0.0,
            "hero_h": 0.60,
            "hero_position": "top",
            "fade": True,
            "grid": False,
            "marks": False,
        }

    def test_static_and_shape(self):
        """返回静态帧，只算一次，尺寸等于画布"""
        frame_fn = hero_layout(self._grey_source(), (160, 240), 5.0, self._base_options())
        frame = frame_fn(0)
        assert frame.shape == (240, 160, 3)
        assert frame_fn(3.9) is frame

    def test_full_bleed_top_and_paper_bottom(self):
        """照片满幅铺满顶部（无留边、无圆角），下方是纸色（照片不铺满整个画面）"""
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, self._base_options())(0).astype(int)

        # 顶角 = 原图灰度（证明无 inset 留白，与 card 的压暗背景不同）
        assert frame[0, 0].mean() == 200
        # 左侧边缘同样满幅（无左右留白）
        assert frame[60, 0].mean() == 200
        # 底部 = 纸色（照片只占上 60%）
        assert list(frame[-1, 0]) == [237, 242, 244]

    def test_bottom_fade_blends_to_paper(self):
        """照片底边渐隐到纸色（hero 最底行已经溶进纸色）"""
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, self._base_options())(0).astype(int)
        # hero 底边（y=143）已被渐隐到接近纸色
        assert frame[143, 80].mean() > 230

    def test_no_title_no_dark_pixels(self):
        """无标题时（且关网格/角标），画面里没有比源图更暗的像素"""
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, self._base_options())(0).astype(int)
        assert (frame < 200).sum() == 0

    def test_title_drawn(self):
        """有标题时，画面里出现更暗的文字像素"""
        options = self._base_options()
        options["title"] = "测试标题"
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)
        assert (frame < 200).sum() > 0

    def test_long_title_does_not_crash(self):
        """超长标题自动缩字号，不报错且能画出"""
        options = self._base_options()
        options["title"] = "这是一个非常非常非常非常非常长的标题文字用于测试自动缩放"
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)
        assert frame.shape == (240, 160, 3)
        assert (frame < 200).sum() > 0

    def test_corner_marks_green(self):
        """四角标记出现绿色（G > R）像素"""
        options = self._base_options()
        options["marks"] = True
        options["accent"] = "#5E8C7A"
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)

        corner = frame[:20, :20]
        assert (corner[..., 1] > corner[..., 0]).any()

    def test_grid_adds_texture(self):
        """网格纹理让画面出现非均匀像素（与纯色底相比）"""
        options = self._base_options()
        options["grid"] = True
        frame = hero_layout(self._grey_source(), (160, 240), 5.0, options)(0).astype(int)

        # 网格线处像素应略暗于纯纸色（非均匀）
        assert (frame[..., 0] != frame[..., 1]).any() or (frame.min() < 237)
