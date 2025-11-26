"""
轮播控制器工具模块
提供图片轮播切换逻辑控制功能
"""


class SlideshowController:
    """
    控制图片轮播切换的控制器类

    根据预定义的切换时间点（change_points）来控制图片的轮播切换时机。
    每次调用 next() 方法会返回当前应该显示的图片路径和其对应的播放时间区间。
    """

    def __init__(self, image_paths, change_points):
        """
        初始化轮播控制器

        参数:
            image_paths (list): 图片文件路径列表
            change_points (list): 切换时间点列表（单位：秒）
        """
        self.image_paths = image_paths
        self.change_points = change_points
        self.n_images = len(image_paths)
        self.idx = 0
        self.time = 0.0

    def next(self):
        """
        切换到下一个图片，返回图片路径和当前时间区间

        返回:
            tuple or None:
                - 如果还有未处理的切换点，返回 (图片路径, 开始时间, 结束时间)
                - 如果已处理完所有切换点，返回 None
        """
        if self.idx >= len(self.change_points) - 1:
            return None  # 已到结尾
        img_path = self.image_paths[self.idx % self.n_images]
        start = self.change_points[self.idx]
        end = self.change_points[self.idx + 1]
        self.idx += 1
        return img_path, start, end

    def reset(self):
        """
        重置控制器到初始状态
        """
        self.idx = 0
        self.time = 0.0

    def get_remaining_changes(self):
        """
        获取剩余的切换次数

        返回:
            int: 剩余的切换次数
        """
        return max(0, len(self.change_points) - 1 - self.idx)

    def get_total_changes(self):
        """
        获取总的切换次数

        返回:
            int: 总的切换次数
        """
        return len(self.change_points) - 1
