"""
轮播控制器工具模块
提供图片和视频混合轮播切换逻辑控制功能
"""
from dataclasses import dataclass
from typing import Optional, List, Union
from utils.media_utils import MediaItem, MediaType
import random


@dataclass
class MediaSegment:
    """媒体片段数据类"""
    media_item: MediaItem
    start_time: float
    end_time: float
    segment_index: int
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def is_image(self) -> bool:
        return self.media_item.is_image
    
    @property
    def is_video(self) -> bool:
        return self.media_item.is_video


class SlideshowController:
    """
    控制媒体轮播切换的控制器类

    根据预定义的切换时间点（change_points）来控制媒体片段的轮播切换时机。
    每次调用 next() 方法会返回当前应该显示的媒体项目、路径和其对应的播放时间区间。
    支持图片和视频混合轮播。
    当素材数量少于切换点时，循环使用素材且随机选择，避免连续使用同一素材。
    """

    def __init__(self, media_items: List[MediaItem], change_points: List[float], random_loop: bool = True):
        """
        初始化轮播控制器

        参数:
            media_items (list): MediaItem 媒体项目列表
            change_points (list): 切换时间点列表（单位：秒）
            random_loop (bool): 循环时是否随机选择，默认为 True
        """
        self.media_items = media_items
        self.change_points = change_points
        self.n_items = len(media_items)
        self.idx = 0
        self.random_loop = random_loop
        self.last_media_item = None

    def next(self) -> Optional[MediaSegment]:
        """
        切换到下一个媒体，返回媒体项目和当前时间区间

        返回:
            MediaSegment or None:
                - 如果还有未处理的切换点，返回 MediaSegment
                - 如果已处理完所有切换点，返回 None
        """
        if self.idx >= len(self.change_points) - 1:
            return None
        
        if self.idx < self.n_items:
            media_item = self.media_items[self.idx]
        else:
            if self.random_loop and self.n_items > 1:
                available_items = [item for item in self.media_items if item != self.last_media_item]
                if not available_items:
                    available_items = self.media_items
                media_item = random.choice(available_items)
            else:
                media_item = self.media_items[self.idx % self.n_items]
        
        self.last_media_item = media_item
        start = self.change_points[self.idx]
        end = self.change_points[self.idx + 1]
        self.idx += 1
        
        return MediaSegment(
            media_item=media_item,
            start_time=start,
            end_time=end,
            segment_index=self.idx - 1
        )

    def reset(self):
        """
        重置控制器到初始状态
        """
        self.idx = 0
        self.last_media_item = None

    def get_remaining_changes(self) -> int:
        """
        获取剩余的切换次数

        返回:
            int: 剩余的切换次数
        """
        return max(0, len(self.change_points) - 1 - self.idx)

    def get_total_changes(self) -> int:
        """
        获取总的切换次数

        返回:
            int: 总的切换次数
        """
        return len(self.change_points) - 1


class VideoSegmentController:
    """
    视频片段专用控制器
    用于处理视频片段，支持自动循环播放和裁剪
    """

    def __init__(self, video_paths: List[str], audio_duration: float | None = None):
        """
        初始化视频片段控制器

        参数:
            video_paths (list): 视频文件路径列表
            audio_duration (float): 目标音频时长，用于循环视频
        """
        self.video_paths = video_paths
        self.n_videos = len(video_paths)
        self.audio_duration = audio_duration
        self.current_video_idx = 0

    def next_video(self) -> Optional[str]:
        """
        获取下一个视频路径

        返回:
            str or None: 视频路径，如果没有视频则返回 None
        """
        if self.n_videos == 0:
            return None
        
        video_path = self.video_paths[self.current_video_idx % self.n_videos]
        self.current_video_idx += 1
        return video_path

    def reset(self):
        """
        重置控制器到初始状态
        """
        self.current_video_idx = 0

    def has_videos(self) -> bool:
        """
        检查是否有视频文件

        返回:
            bool: 是否有视频文件
        """
        return self.n_videos > 0
