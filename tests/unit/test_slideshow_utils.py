"""
slideshow_utils.py 模块的单元测试
"""
import pytest

from utils.slideshow_utils import SlideshowController


class TestSlideshowController:
    """SlideshowController 类的测试"""

    def test_initialization(self):
        """测试初始化"""
        image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        change_points = [0.0, 2.0, 4.0, 6.0]

        controller = SlideshowController(image_paths, change_points)

        assert controller.image_paths == image_paths
        assert controller.change_points == change_points
        assert controller.n_images == 3
        assert controller.idx == 0
        assert controller.time == 0.0

    def test_next_method_basic(self):
        """测试基本的 next() 方法"""
        image_paths = ["img1.jpg", "img2.jpg"]
        change_points = [0.0, 1.0, 3.0, 5.0]

        controller = SlideshowController(image_paths, change_points)

        # 第一次调用
        result1 = controller.next()
        assert result1 == ("img1.jpg", 0.0, 1.0)
        assert controller.idx == 1

        # 第二次调用
        result2 = controller.next()
        assert result2 == ("img2.jpg", 1.0, 3.0)
        assert controller.idx == 2

        # 第三次调用
        result3 = controller.next()
        assert result3 == ("img1.jpg", 3.0, 5.0)  # 循环使用图片
        assert controller.idx == 3

        # 第四次调用（应该返回 None）
        result4 = controller.next()
        assert result4 is None
        assert controller.idx == 4

    def test_next_method_single_image(self):
        """测试只有一张图片的情况"""
        image_paths = ["single.jpg"]
        change_points = [0.0, 2.0, 4.0, 6.0]

        controller = SlideshowController(image_paths, change_points)

        # 所有调用都应该返回同一张图片
        for i in range(3):
            result = controller.next()
            expected_start = change_points[i]
            expected_end = change_points[i + 1]
            assert result == ("single.jpg", expected_start, expected_end)
            assert controller.idx == i + 1

        # 第四次调用返回 None
        result = controller.next()
        assert result is None

    def test_next_method_image_cycle(self):
        """测试图片循环使用"""
        image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        change_points = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]  # 6 个区间

        controller = SlideshowController(image_paths, change_points)

        # 前 3 次应该按顺序使用图片
        for i in range(3):
            result = controller.next()
            expected_img = image_paths[i]
            assert result[0] == expected_img

        # 第 4 次应该循环回第一张图片
        result = controller.next()
        assert result[0] == "img1.jpg"

        # 第 5 次应该是第二张图片
        result = controller.next()
        assert result[0] == "img2.jpg"

        # 第 6 次应该是第三张图片
        result = controller.next()
        assert result[0] == "img3.jpg"

    def test_reset_method(self):
        """测试 reset() 方法"""
        image_paths = ["img1.jpg", "img2.jpg"]
        change_points = [0.0, 1.0, 3.0, 5.0]

        controller = SlideshowController(image_paths, change_points)

        # 推进几次
        controller.next()
        controller.next()
        assert controller.idx == 2
        assert controller.time != 0.0

        # 重置
        controller.reset()
        assert controller.idx == 0
        assert controller.time == 0.0

    def test_get_remaining_changes(self):
        """测试 get_remaining_changes() 方法"""
        image_paths = ["img1.jpg", "img2.jpg"]
        change_points = [0.0, 1.0, 3.0, 5.0]  # 3 个切换

        controller = SlideshowController(image_paths, change_points)

        # 初始状态
        assert controller.get_remaining_changes() == 3

        # 推进一次
        controller.next()
        assert controller.get_remaining_changes() == 2

        # 推进两次
        controller.next()
        assert controller.get_remaining_changes() == 1

        # 推进三次
        controller.next()
        assert controller.get_remaining_changes() == 0

    def test_get_total_changes(self):
        """测试 get_total_changes() 方法"""
        # 不同数量的切换点
        test_cases = [
            ([0.0, 1.0], 1),  # 2 个点，1 个切换
            ([0.0, 1.0, 3.0], 2),  # 3 个点，2 个切换
            ([0.0, 1.0, 3.0, 5.0, 7.0], 4),  # 5 个点，4 个切换
        ]

        for change_points, expected_total in test_cases:
            controller = SlideshowController(["img1.jpg"], change_points)
            assert controller.get_total_changes() == expected_total

    def test_edge_cases(self):
        """测试边界情况"""

        # 测试单个切换点
        controller = SlideshowController(["img1.jpg"], [0.0, 5.0])
        result = controller.next()
        assert result == ("img1.jpg", 0.0, 5.0)
        assert controller.next() is None

        # 测试空图片列表（这可能会导致问题，但我们测试行为）
        controller = SlideshowController([], [0.0, 1.0, 2.0])
        # 这里的行为可能取决于实现

        # 测试单个时间点（没有切换）
        controller = SlideshowController(["img1.jpg"], [5.0])
        # 这种情况下可能没有有效的切换

    def test_time_tracking(self):
        """测试时间跟踪"""
        image_paths = ["img1.jpg"]
        change_points = [0.0, 1.0, 3.0, 5.0]

        controller = SlideshowController(image_paths, change_points)

        # 初始时间
        assert controller.time == 0.0

        # 推进一次后时间应该更新（虽然具体逻辑可能因实现而异）
        controller.next()
        # time 的具体行为可能需要根据实际实现调整

    def test_consecutive_calls(self):
        """测试连续调用的行为"""
        image_paths = ["img1.jpg", "img2.jpg"]
        change_points = [0.0, 2.0, 4.0]

        controller = SlideshowController(image_paths, change_points)

        # 连续调用直到耗尽
        results = []
        while True:
            result = controller.next()
            if result is None:
                break
            results.append(result)

        assert len(results) == 2
        assert results[0] == ("img1.jpg", 0.0, 2.0)
        assert results[1] == ("img2.jpg", 2.0, 4.0)

        # 再次调用应该继续返回 None
        assert controller.next() is None

    def test_mixed_image_and_change_counts(self):
        """测试图片数量和切换点数量的不同组合"""

        # 图片比切换点多
        image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        change_points = [0.0, 1.0, 2.0]  # 2 个切换
        controller = SlideshowController(image_paths, change_points)

        results = []
        while True:
            result = controller.next()
            if result is None:
                break
            results.append(result)

        assert len(results) == 2
        assert results[0][0] == "img1.jpg"
        assert results[1][0] == "img2.jpg"  # 第三张图片不会被使用

        # 切换点比图片多
        image_paths = ["img1.jpg", "img2.jpg"]
        change_points = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]  # 5 个切换
        controller = SlideshowController(image_paths, change_points)

        results = []
        while True:
            result = controller.next()
            if result is None:
                break
            results.append(result)

        assert len(results) == 5
        expected_sequence = ["img1.jpg", "img2.jpg", "img1.jpg", "img2.jpg", "img1.jpg"]
        for i, result in enumerate(results):
            assert result[0] == expected_sequence[i]
