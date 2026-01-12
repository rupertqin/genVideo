"""
视频生成主脚本
使用 moviepy 创建图片和视频混合轮播视频，支持音频配合和过渡效果
"""
from moviepy import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os
import argparse
import time

from utils.audio_utils import get_audio_duration_ffmpeg, get_audio_pauses
from utils.media_utils import get_media_paths, get_audio_path, MediaType
from utils.slideshow_utils import SlideshowController
from utils.video_utils import resize_and_position_image, resize_and_position_video
from utils.animation_utils import AnimationConfig, apply_animation, get_random_animation_config
from config import VideoSize, parse_video_size, print_available_sizes


def create_slideshow(media_items, audio_path, output_path,
                     transition_duration=1,
                     stage_size=(1280, 720), fps=30, audio_duration=0,
                     animation_config=None, random_animation=False):
    """
    创建新版 MoviePy 的混合媒体轮播视频

    参数说明:
        media_items (list): MediaItem 媒体项目列表
        audio_path (str): 音频文件路径
        output_path (str): 输出视频文件路径
        transition_duration (int): 过渡效果时长（秒）
        stage_size: 输出视频分辨率，支持以下格式：
            - tuple: (width, height)，如 (1280, 720)
            - str: 预设名称，如 'HD_720P', 'PORTRAIT_1080P'
            - str: 格式 'WIDTHxHEIGHT'，如 '1280x720'
        fps (int): 视频帧率
        audio_duration (float): 目标音频时长，0表示使用原始音频时长
        animation_config (AnimationConfig): 动画配置对象，None 表示无动画
        random_animation (bool): 是否为每张图片随机选择动画效果

    内部实现适配 v2.x API
    """
    stage_size = parse_video_size(stage_size)
    print(f"视频尺寸: {stage_size[0]} x {stage_size[1]}")

    if not audio_duration or audio_duration <= 0:
        audio_duration = get_audio_duration_ffmpeg(audio_path)
    print(f"音频时长: {audio_duration} 秒 (使用音频文件: {audio_path})")
    audio = AudioFileClip(audio_path)
    if audio_duration and audio_duration > 0:
        audio = audio.subclipped(0, audio_duration)

    pause_points = get_audio_pauses(audio_path, min_pause=0.70, noise_threshold=-35, min_interval=5.0)
    print(f"检测到停顿点（间隔 >= 5秒）: {pause_points}")
    print(f"检测到停顿点数量: {len(pause_points)}")
    change_points = [0.0] + pause_points + [audio_duration]

    n_media = len(media_items)
    controller = SlideshowController(media_items, change_points)
    print("轮播切换顺序:")
    for i in range(len(change_points) - 1):
        media_item = media_items[i % n_media]
        start = change_points[i]
        end = change_points[i + 1]
        print(f"媒体: {media_item.name} ({media_item.media_type.value}) | 时间区间: {start:.2f} - {end:.2f}")
    if n_media == 0:
        raise FileNotFoundError("未提供任何媒体文件，无法生成轮播视频。请在 `media` 目录添加图片或视频。")
    if n_media < len(change_points) - 1:
        print(f"媒体数量 ({n_media}) 少于切换点数量 ({len(change_points)-1})，将循环使用媒体以覆盖所有切换点。")

    clips = []
    for i in range(len(change_points) - 1):
        segment = controller.next()
        if segment is None:
            break

        media_item = segment.media_item
        start = change_points[i]
        end = change_points[i + 1]
        duration = end - start

        if i < len(change_points) - 2 and transition_duration > 0:
            duration += transition_duration

        if not os.path.exists(media_item.path):
            raise FileNotFoundError(f"媒体文件不存在: {media_item.path}")

        if media_item.media_type == MediaType.IMAGE:
            clip = ImageClip(media_item.path, duration=duration)
            clip = resize_and_position_image(clip, stage_size, position="center")

        else:
            print(f"  [视频] 直接播放，不应用动画")
            video_duration = VideoFileClip(media_item.path).duration
            
            if video_duration >= duration:
                clip = VideoFileClip(media_item.path).subclipped(0, duration)
            else:
                original_clip = VideoFileClip(media_item.path)
                video_part = original_clip.with_duration(video_duration)
                remaining = duration - video_duration
                
                last_frame = original_clip.get_frame(original_clip.duration - 0.01)
                still_frame = ImageClip(last_frame, duration=remaining)
                
                clip = concatenate_videoclips([video_part, still_frame], method="compose")
            
            clip = resize_and_position_video(clip, stage_size, position="center")

        effects = []
        if i > 0:
            effects.append(FadeIn(duration=transition_duration))
        if i < len(change_points) - 2:
            effects.append(FadeOut(duration=transition_duration))
        if effects:
            clip = clip.with_effects(effects)
        clips.append(clip)

    final_video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-transition_duration
    )
    final_video = final_video.with_audio(audio)
    print(f"最终视频时长: {final_video.duration}, 目标音频时长: {audio_duration}")
    clip_end = min(audio_duration, final_video.duration)
    final_video = final_video.subclipped(0, clip_end)
    final_video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        bitrate="5000k",
        threads=4,
        preset="medium"
    )
    print(f"视频生成成功: {output_path}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='生成图片和视频混合轮播视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认配置
  python generate.py

  # 指定视频尺寸（使用预设）
  python generate.py --size TEST_SMALL
  python generate.py --size PORTRAIT_1080P

  # 指定视频尺寸（自定义）
  python generate.py --size 1280x720

  # 指定输出文件和帧率
  python generate.py --output my_video.mp4 --fps 30

  # 禁用动画
  python generate.py --no-animation

  # 查看所有可用尺寸预设
  python generate.py --list-sizes

支持的媒体格式:
  图片: jpg, jpeg, png, gif, webp, tiff, bmp
  视频: mp4, mov, avi, mkv, webm, m4v, flv
        """
    )

    parser.add_argument('--media', '-m', default='media',
                        help='媒体目录路径，支持图片和视频 (默认: media)')
    parser.add_argument('--images', '-i', default=None,
                        help='图片目录路径（仅图片，用于兼容旧版本）')
    parser.add_argument('--videos', '-v', default=None,
                        help='视频目录路径（仅视频）')
    parser.add_argument('--audio', '-a', default=None,
                        help='音频文件路径 (默认: 自动查找 audio.wav 或 audio.mp3)')
    parser.add_argument('--output', '-o', default='generated.mp4',
                        help='输出视频文件路径 (默认: generated.mp4)')
    parser.add_argument('--size', '-s', default='HD_720P',
                        help='视频尺寸，支持预设名称(如 HD_720P)或格式 WIDTHxHEIGHT (默认: HD_720P)')
    parser.add_argument('--fps', '-f', type=int, default=24,
                        help='视频帧率 (默认: 24)')
    parser.add_argument('--transition', '-t', type=float, default=1.0,
                        help='过渡效果时长（秒） (默认: 1.0)')
    parser.add_argument('--no-animation', action='store_true',
                        help='禁用动画效果')
    parser.add_argument('--list-sizes', action='store_true',
                        help='列出所有可用的视频尺寸预设')

    args = parser.parse_args()

    if args.list_sizes:
        print_available_sizes()
        raise SystemExit(0)

    if args.images and args.videos:
        from utils.media_utils import get_image_paths, get_video_paths, MediaItem

        image_paths = get_image_paths(args.images)
        video_paths = get_video_paths(args.videos)
        media_items = []
        for path in image_paths:
            media_items.append(MediaItem(path=path, media_type=MediaType.IMAGE, name=os.path.basename(path)))
        for path in video_paths:
            media_items.append(MediaItem(path=path, media_type=MediaType.VIDEO, name=os.path.basename(path)))
        media_items.sort(key=lambda x: x.name)
        print(f"从 {args.images} 加载了 {len([m for m in media_items if m.is_image])} 张图片")
        print(f"从 {args.videos} 加载了 {len([m for m in media_items if m.is_video])} 个视频")

    elif args.media:
        media_items = get_media_paths(args.media)
        if not media_items:
            print(f"错误: 未在目录 `{args.media}` 中找到媒体文件，请检查路径。")
            raise SystemExit(1)
        print(f"从 {args.media} 加载了 {len(media_items)} 个媒体文件")

    else:
        media_items = get_media_paths('images')
        if not media_items:
            print(f"错误: 未在目录 `images` 中找到媒体文件，请检查路径。")
            raise SystemExit(1)

    if args.audio:
        AUDIO_PATH = args.audio
        if not os.path.exists(AUDIO_PATH):
            print(f"错误: 音频文件不存在: {AUDIO_PATH}")
            raise SystemExit(1)
    else:
        AUDIO_PATH = get_audio_path()
        if not AUDIO_PATH:
            print("错误: 未找到 `audio.wav` 或 `audio.mp3`，请在项目根目录放置音频文件或使用 --audio 参数指定。")
            raise SystemExit(1)

    try:
        STAGE_SIZE = parse_video_size(args.size)
    except ValueError as e:
        print(f"错误: {e}")
        raise SystemExit(1)

    animation = None
    random_animation = not args.no_animation

    n_images = len([m for m in media_items if m.is_image])
    n_videos = len([m for m in media_items if m.is_video])

    print("=" * 60)
    print("视频生成配置:")
    print(f"  媒体目录: {args.media or 'images'} ({n_images} 张图片, {n_videos} 个视频)")
    print(f"  音频文件: {AUDIO_PATH}")
    print(f"  输出文件: {args.output}")
    print(f"  视频尺寸: {STAGE_SIZE[0]} x {STAGE_SIZE[1]}")
    print(f"  帧率: {args.fps} fps")
    print(f"  过渡时长: {args.transition} 秒")
    print(f"  动画效果: {'启用（随机）' if random_animation else '禁用'}")
    print("=" * 60)

    start_time = time.time()

    create_slideshow(
        media_items=media_items,
        audio_path=AUDIO_PATH,
        output_path=args.output,
        audio_duration=0,
        transition_duration=args.transition,
        stage_size=STAGE_SIZE,
        fps=args.fps,
        animation_config=animation,
        random_animation=random_animation
    )

    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60

    print("=" * 60)
    print(f"✓ 视频生成完成！")
    print(f"  总耗时: {minutes} 分 {seconds:.2f} 秒")
    print(f"  输出文件: {args.output}")
    print("=" * 60)
