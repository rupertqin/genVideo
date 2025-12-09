"""
视频生成主脚本
使用 moviepy 创建图片轮播视频，支持音频配合和过渡效果
"""
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os
import argparse
import time

# 导入工具模块
from utils.audio_utils import get_audio_duration_ffmpeg, get_audio_pauses
from utils.image_utils import get_image_paths, get_audio_path
from utils.slideshow_utils import SlideshowController
from utils.video_utils import resize_and_position_image
from utils.animation_utils import AnimationConfig, apply_animation, get_random_animation_config
from config import VideoSize, parse_video_size, print_available_sizes


def create_slideshow(image_paths, audio_path, output_path,
                     duration_per_image=5, transition_duration=1,
                     stage_size=(1280, 720), fps=30, audio_duration=0,
                     animation_config=None, random_animation=False):
    """
    创建新版 MoviePy 的渐变轮播视频

    参数说明:
        image_paths (list): 图片文件路径列表
        audio_path (str): 音频文件路径
        output_path (str): 输出视频文件路径
        duration_per_image (int): 每张图片的显示时长（秒）
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
    # 解析视频尺寸
    stage_size = parse_video_size(stage_size)
    print(f"视频尺寸: {stage_size[0]} x {stage_size[1]}")

    if not audio_duration or audio_duration <= 0:
        audio_duration = get_audio_duration_ffmpeg(audio_path)
    print(f"音频时长: {audio_duration} 秒 (使用音频文件: {audio_path})")
    audio = AudioFileClip(audio_path)
    if audio_duration and audio_duration > 0:
        audio = audio.subclipped(0, audio_duration)

    # 检测音频停顿点
    pause_points = get_audio_pauses(audio_path, min_pause=0.7, noise_threshold=-35)
    print(f"检测到停顿点: {pause_points}")
    # 构造切换时间点序列
    change_points = [0.0] + pause_points + [audio_duration]

    # 使用轮播控制器
    controller = SlideshowController(image_paths, change_points)
    print("轮播切换顺序:")
    while True:
        result = controller.next()
        if result is None:
            break
        img_path, start, end = result
        print(f"图片: {os.path.basename(img_path)} | 时间区间: {start:.2f} - {end:.2f}")

    n_images = len(image_paths)
    if n_images == 0:
        raise FileNotFoundError("未提供任何图片，无法生成轮播视频。请在 `images` 目录添加图片。")
    if n_images < len(change_points) - 1:
        print(f"图片数量 ({n_images}) 少于切换点数量 ({len(change_points)-1})，将循环使用图片以覆盖所有切换点。")

    clips = []
    for i in range(len(change_points)-1):
        img_path = image_paths[i % n_images]
        start = change_points[i]
        end = change_points[i+1]
        # 基本时长为相邻 change_points 之间的间隔
        duration = end - start
        # 由于使用了 padding=-transition_duration（让片段重叠做过渡），
        # 如果不补偿，后续片段会提前 start transition_duration * 累计 次数。
        # 为了让视觉切换严格在 change_points 上发生，需要对除最后一段外的片段
        # 将时长增加 transition_duration，这样在拼接时被 padding 抵消。
        if i < len(change_points) - 2 and transition_duration > 0:
            duration += transition_duration
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"图片不存在: {img_path}")

        # 创建图片片段
        clip = ImageClip(img_path, duration=duration)

        # 应用动画效果（动画函数内部会处理缩放和位置）
        if random_animation:
            current_animation = get_random_animation_config(intensity=0.15, easing="ease_in_out_quad")
            clip = apply_animation(clip, current_animation, stage_size)
            print(f"  动画: {current_animation.animation_type}")
        elif animation_config:
            clip = apply_animation(clip, animation_config, stage_size)
        else:
            # 无动画时使用标准的缩放和位置处理
            clip = resize_and_position_image(clip, stage_size, position="center")

        # 添加过渡效果
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
        threads=4
    )
    print(f"视频生成成功: {output_path}")


if __name__ == "__main__":

    # 命令行参数解析
    parser = argparse.ArgumentParser(
        description='生成图片轮播视频',
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
        """
    )

    parser.add_argument('--images', '-i', default='images',
                        help='图片目录路径 (默认: images)')
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

    # 如果请求列出尺寸预设
    if args.list_sizes:
        print_available_sizes()
        raise SystemExit(0)

    # 获取图片路径
    IMAGE_PATHS = get_image_paths(args.images)
    if not IMAGE_PATHS:
        print(f"错误: 未在目录 `{args.images}` 中找到图片，请检查路径。")
        raise SystemExit(1)

    # 获取音频路径
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

    # 解析视频尺寸
    try:
        STAGE_SIZE = parse_video_size(args.size)
    except ValueError as e:
        print(f"错误: {e}")
        raise SystemExit(1)

    # 动画配置
    animation = None
    random_animation = not args.no_animation

    print("=" * 60)
    print("视频生成配置:")
    print(f"  图片目录: {args.images} ({len(IMAGE_PATHS)} 张图片)")
    print(f"  音频文件: {AUDIO_PATH}")
    print(f"  输出文件: {args.output}")
    print(f"  视频尺寸: {STAGE_SIZE[0]} x {STAGE_SIZE[1]}")
    print(f"  帧率: {args.fps} fps")
    print(f"  过渡时长: {args.transition} 秒")
    print(f"  动画效果: {'启用（随机）' if random_animation else '禁用'}")
    print("=" * 60)

    # 记录开始时间
    start_time = time.time()

    create_slideshow(
        image_paths=IMAGE_PATHS,
        audio_path=AUDIO_PATH,
        output_path=args.output,
        audio_duration=0,
        duration_per_image=3,
        transition_duration=args.transition,
        stage_size=STAGE_SIZE,
        fps=args.fps,
        animation_config=animation,
        random_animation=random_animation
    )

    # 计算总耗时
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60

    print("=" * 60)
    print(f"✓ 视频生成完成！")
    print(f"  总耗时: {minutes} 分 {seconds:.2f} 秒")
    print(f"  输出文件: {args.output}")
    print("=" * 60)
