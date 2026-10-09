"""
视频生成主脚本
使用 moviepy 创建图片和视频混合轮播视频，支持音频配合和过渡效果
"""
from moviepy import ImageClip, VideoFileClip, AudioFileClip, VideoClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os
import argparse
import time

from utils.audio_utils import get_audio_duration_ffmpeg, get_audio_pauses
from utils.media_utils import (
    get_media_paths,
    find_audio_in,
    ensure_parent_dir,
    MediaType,
)
from utils.slideshow_utils import SlideshowController
from utils.video_utils import resize_and_position_video
from utils.animation_utils import AnimationConfig, apply_animation, get_random_animation_config
from utils.subtitle_utils import (
    load_subtitles,
    burn_subtitles,
    filter_cues,
    find_subtitle_path,
    format_timestamp,
)
from utils.layouts import get_layout, list_layouts
from config import (
    VideoSize,
    parse_video_size,
    print_available_sizes,
    load_config,
    parse_duration,
    subtitle_options,
    DEFAULT_CONFIG,
)

# 硬件 H.264 编码器候选（按优先级）；仅在显式使用 --encoder auto 时才会被采用
HARDWARE_ENCODERS = ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf")

# create_slideshow 的程序化默认值（与 config.yaml 的内置默认同源）
DEFAULT_VIDEO = DEFAULT_CONFIG["video"]
DEFAULT_PRESET = DEFAULT_VIDEO["preset"]

# 默认图片/音频目录不存在时，按顺序回退的旧目录（兼容既有项目结构）
LEGACY_MEDIA_DIRS = ("media", "images")
LEGACY_AUDIO_DIRS = (".", "media")


def detect_hardware_encoder():
    """
    探测 moviepy 实际调用的 ffmpeg 是否带硬件 H.264 编码器。

    返回:
        str or None: 第一个可用的硬件编码器名，没有则 None
    """
    try:
        import subprocess

        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None

    for name in HARDWARE_ENCODERS:
        if name in result.stdout:
            return name
    return None


def _build_write_kwargs(fps, encoder, preset, bitrate):
    """
    组装 MoviePy ``write_videofile`` 的参数。

    ``preset`` 只对软件 x264 有意义；硬件编码器不能传 ``None``
    （MoviePy 会当成路径处理而报 TypeError），所以直接不传。
    """
    kwargs = dict(
        fps=fps,
        codec=encoder,
        audio_codec="aac",
        audio_bitrate="192k",
        bitrate=bitrate,
        threads=4,
    )
    if encoder == "libx264" and preset:
        kwargs["preset"] = preset
    return kwargs


def create_slideshow(media_items, audio_path, output_path,
                     transition_duration=1,
                     stage_size=(1280, 720), fps=30, audio_duration=0,
                     animation_config=None, random_animation=False,
                     subtitle_path=None, subtitle_options=None,
                     encoder=DEFAULT_VIDEO["encoder"], preset=DEFAULT_PRESET,
                     bitrate=DEFAULT_VIDEO["bitrate"],
                     layout_name="fullscreen", layout_options=None):
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

    # audio_duration > 0 表示调用方明确要求了时长上限；否则用完整音频
    duration_limit = float(audio_duration) if audio_duration and audio_duration > 0 else None
    if duration_limit is None:
        audio_duration = get_audio_duration_ffmpeg(audio_path)
    else:
        audio_duration = duration_limit

    print(f"音频时长: {audio_duration} 秒 (使用音频文件: {audio_path})")
    audio = AudioFileClip(audio_path)
    actual_duration = audio.duration
    if duration_limit is not None:
        audio_duration = min(duration_limit, actual_duration)
        audio = audio.subclipped(0, audio_duration)
    print(f"成片时长: {audio_duration} 秒"
          + ("（已按时长配置截断）" if duration_limit is not None else "（完整音频）"))

    pause_points = get_audio_pauses(audio_path, min_pause=0.70, noise_threshold=-35, min_interval=5.0)
    # 截断时长时，只保留时长范围内的停顿点，否则会出现超出片尾的分段
    pause_points = [point for point in pause_points if 0 < point < audio_duration]
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
            image_clip = ImageClip(media_item.path, duration=duration)
            anim_config = get_random_animation_config() if random_animation else animation_config
            if (layout_name == "fullscreen"
                    and anim_config is not None
                    and anim_config.animation_type != AnimationConfig.NONE):
                clip = apply_animation(image_clip, anim_config, stage_size)
            else:
                layout_fn = get_layout(layout_name)
                frame_func = layout_fn(image_clip.get_frame(0), stage_size, duration, layout_options)
                clip = VideoClip(frame_func, duration=duration)
                clip.size = stage_size

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

    if subtitle_path:
        cues = load_subtitles(subtitle_path)
        shown = filter_cues(cues, getattr(final_video, "duration", None))
        if shown:
            final_video = burn_subtitles(final_video, shown, **(subtitle_options or {}))
            print(f"已叠加字幕 {len(shown)} 条（来源: {subtitle_path}，文件共 {len(cues)} 条）")
        else:
            print(f"警告: 字幕文件未解析出内容，已跳过: {subtitle_path}")

    ensure_parent_dir(output_path)
    final_video.write_videofile(
        output_path, **_build_write_kwargs(fps, encoder, preset, bitrate)
    )
    print(f"视频生成成功: {output_path}")


if __name__ == "__main__":

    # config.yaml 提供默认值；命令行参数可覆盖（优先级：命令行 > config.yaml > 内置默认）
    try:
        CFG = load_config()
    except RuntimeError as exc:
        print(f"错误: {exc}")
        raise SystemExit(1)
    video_cfg, media_cfg, sub_cfg = CFG["video"], CFG["media"], CFG["subtitle"]

    parser = argparse.ArgumentParser(
        description='生成图片和视频混合轮播视频（默认值来自 config.yaml）',
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

    parser.add_argument('--media', '-m', default=None,
                        help='混合媒体目录（图片+视频放一起）；设置后忽略 --images/--videos'
                             f' (config.yaml: media.dir = {media_cfg["dir"]})')
    parser.add_argument('--images', '-i', default=None,
                        help=f'图片目录 (config.yaml: media.images = {media_cfg["images"]})')
    parser.add_argument('--videos', '-v', default=None,
                        help=f'视频目录 (config.yaml: media.videos = {media_cfg["videos"]})')
    parser.add_argument('--audio', '-a', default=None,
                        help='音频文件，或存放音频的目录 (config.yaml: '
                             f'media.audio = {media_cfg["audio"]})')
    parser.add_argument('--output', '-o', default=media_cfg["output"],
                        help=f'输出视频文件路径 (config.yaml: {media_cfg["output"]})')
    parser.add_argument('--size', '-s', default=video_cfg["size"],
                        help='视频尺寸，支持预设名称(如 HD_720P)或格式 WIDTHxHEIGHT'
                             f' (config.yaml: {video_cfg["size"]})')
    parser.add_argument('--fps', '-f', type=int, default=int(video_cfg["fps"]),
                        help=f'视频帧率 (config.yaml: {video_cfg["fps"]})')
    parser.add_argument('--duration', default=video_cfg["duration"],
                        help='输出时长，可精确到毫秒：180 | 180.5 | 180s | 3m | 3:00 | 00:03:00.250'
                             f' (config.yaml: video.duration = {video_cfg["duration"]})')
    parser.add_argument('--transition', '-t', type=float, default=float(video_cfg["transition"]),
                        help=f'过渡效果时长（秒） (config.yaml: {video_cfg["transition"]})')
    parser.add_argument('--animation', dest='animation', action='store_true',
                        default=bool(video_cfg["animation"]),
                        help='为图片启用随机缩放/平移动画（会降低编码速度）')
    parser.add_argument('--no-animation', dest='animation', action='store_false',
                        help='不启用动画效果')
    parser.add_argument('--layout', default=video_cfg["layout"],
                        help='画面布局组件：fullscreen | card'
                             f' (config.yaml: video.layout = {video_cfg["layout"]})')
    parser.add_argument('--encoder', default=video_cfg["encoder"],
                        help='视频编码器: libx264 | h264_videotoolbox | h264_nvenc | ... | auto'
                             f' (config.yaml: {video_cfg["encoder"]})')
    parser.add_argument('--preset', default=video_cfg["preset"],
                        help='libx264 编码预设，越快画质略降'
                             f' (config.yaml: {video_cfg["preset"]})')
    parser.add_argument('--bitrate', default=video_cfg["bitrate"],
                        help=f'视频码率 (config.yaml: {video_cfg["bitrate"]}；硬件编码器建议适当调高)')
    parser.add_argument('--subtitles', dest='subtitles', default=sub_cfg["path"],
                        help='字幕文件路径 (默认: 自动查找与音频同名的 .srt)')
    parser.add_argument('--no-subtitles', dest='subtitles_enabled', action='store_false',
                        default=bool(sub_cfg["enabled"]),
                        help='不叠加字幕（覆盖 config.yaml 的 subtitle.enabled）')
    parser.add_argument('--subtitle-font', default=sub_cfg["font"],
                        help='字幕字体文件路径 (默认: 自动选择系统中文字体)')
    parser.add_argument('--subtitle-size', type=float, default=sub_cfg["size"],
                        help='字幕字号（像素） (默认: 按视频高度自适应)')
    parser.add_argument('--subtitle-bottom', type=float, default=float(sub_cfg["bottom"]),
                        help=f'字幕距底部的高度比例 (config.yaml: {sub_cfg["bottom"]})')
    parser.add_argument('--list-sizes', action='store_true',
                        help='列出所有可用的视频尺寸预设')

    args = parser.parse_args()

    if args.list_sizes:
        print_available_sizes()
        raise SystemExit(0)

    # ---- 媒体目录：--media（混合目录）优先，其次 --images/--videos，最后 config.yaml ----
    MEDIA_DIR = args.media or media_cfg["dir"]
    if MEDIA_DIR:
        if not os.path.isdir(MEDIA_DIR):
            print(f"错误: 媒体目录不存在: {MEDIA_DIR}")
            raise SystemExit(1)
        media_items = get_media_paths(MEDIA_DIR)
        if not media_items:
            print(f"错误: 未在目录 `{MEDIA_DIR}` 中找到媒体文件，请检查路径。")
            raise SystemExit(1)
        IMAGE_DIR = MEDIA_DIR
        print(f"从 {MEDIA_DIR} 加载了 {len(media_items)} 个媒体文件")

    else:
        IMAGE_DIR = args.images or media_cfg["images"]
        if args.images and not os.path.isdir(IMAGE_DIR):
            print(f"错误: 图片目录不存在: {IMAGE_DIR}")
            raise SystemExit(1)

        media_items = get_media_paths(IMAGE_DIR)

        # 默认目录不存在或还是空的时，回退到旧目录（避免刚建的空 assets/images 把流程挡死）
        if not media_items and not args.images:
            for legacy_dir in LEGACY_MEDIA_DIRS:
                if os.path.abspath(legacy_dir) == os.path.abspath(IMAGE_DIR):
                    continue
                legacy_items = get_media_paths(legacy_dir)
                if legacy_items:
                    print(f"提示: `{IMAGE_DIR}` 中没有媒体文件，改用旧目录 `{legacy_dir}/`"
                          f"（建议迁移，或在 config.yaml 设置 media.images: {legacy_dir}）")
                    IMAGE_DIR, media_items = legacy_dir, legacy_items
                    break

        if not media_items:
            print(f"错误: 目录 `{IMAGE_DIR}` 中没有可用的媒体文件。")
            print("      请把图片放入该目录，或在 config.yaml 中设置 media.images。")
            raise SystemExit(1)

        print(f"从 {IMAGE_DIR} 加载了 {len([m for m in media_items if m.is_image])} 张图片")

        VIDEO_DIR = args.videos or media_cfg["videos"]
        if VIDEO_DIR:
            if not os.path.isdir(VIDEO_DIR):
                print(f"错误: 视频目录不存在: {VIDEO_DIR}")
                raise SystemExit(1)
            videos = get_media_paths(VIDEO_DIR)
            media_items = sorted(media_items + videos, key=lambda item: item.name)
            print(f"从 {VIDEO_DIR} 加载了 {len([m for m in videos if m.is_video])} 个视频")

    # ---- 音频：可以是文件，也可以是存放音频的目录；未显式指定时按 config.yaml 查找 ----
    AUDIO_SETTING = args.audio or media_cfg["audio"]
    AUDIO_PATH = find_audio_in(AUDIO_SETTING)
    if not AUDIO_PATH and not args.audio:
        for legacy_dir in LEGACY_AUDIO_DIRS:
            legacy_audio = find_audio_in(legacy_dir)
            if legacy_audio:
                print(f"提示: 在 `{AUDIO_SETTING}` 中未找到音频，改用 `{legacy_audio}`"
                      f"（建议迁移，或在 config.yaml 设置 media.audio: {legacy_dir}）")
                AUDIO_PATH = legacy_audio
                break
    if not AUDIO_PATH:
        print(f"错误: 未找到音频文件（查找位置: `{AUDIO_SETTING}`）。")
        print(f"      请把 audio.wav / audio.mp3 放入该目录，或用 --audio 指定。")
        raise SystemExit(1)

    SUBTITLE_PATH = None
    if args.subtitles_enabled:
        SUBTITLE_PATH = args.subtitles or find_subtitle_path(AUDIO_PATH)
        if SUBTITLE_PATH and not os.path.exists(SUBTITLE_PATH):
            print(f"错误: 字幕文件不存在: {SUBTITLE_PATH}")
            raise SystemExit(1)

    # 字幕样式：config.yaml 提供全部参数，命令行可覆盖其中三项
    SUBTITLE_OPTIONS = subtitle_options(CFG)
    SUBTITLE_OPTIONS.update(
        font_path=args.subtitle_font,
        font_size=int(args.subtitle_size) if args.subtitle_size else None,
        bottom_ratio=args.subtitle_bottom,
    )

    # 画面布局组件：config.yaml 的 video.layout 选择，命令行可覆盖
    LAYOUT_NAME = args.layout or video_cfg.get("layout", "fullscreen")
    if get_layout(LAYOUT_NAME) is None:
        print(f"错误: 未知布局 `{LAYOUT_NAME}`（可用: {', '.join(list_layouts())}）")
        raise SystemExit(1)
    LAYOUT_OPTIONS = dict(CFG.get("layout", {}).get(LAYOUT_NAME, {}) or {})
    # card 布局的标题：未显式配置时，自动用音频文件名（去扩展名）
    if LAYOUT_NAME == "card" and not LAYOUT_OPTIONS.get("title"):
        LAYOUT_OPTIONS["title"] = os.path.splitext(os.path.basename(AUDIO_PATH))[0]

    ENCODER = args.encoder
    if ENCODER == 'auto':
        detected = detect_hardware_encoder()
        if detected:
            ENCODER = detected
            print(f"已自动选择硬件编码器: {detected}")
        else:
            ENCODER = 'libx264'
            print("未检测到可用的硬件编码器，回退到 libx264")

    try:
        STAGE_SIZE = parse_video_size(args.size)
    except ValueError as e:
        print(f"错误: {e}")
        raise SystemExit(1)

    try:
        DURATION = parse_duration(args.duration)
    except ValueError as e:
        print(f"错误: {e}")
        raise SystemExit(1)

    animation = None
    random_animation = bool(args.animation)

    n_images = len([m for m in media_items if m.is_image])
    n_videos = len([m for m in media_items if m.is_video])

    print("=" * 60)
    print("视频生成配置:")
    print(f"  媒体目录: {IMAGE_DIR} ({n_images} 张图片, {n_videos} 个视频)")
    print(f"  音频文件: {AUDIO_PATH}")
    print(f"  输出文件: {args.output}")
    print(f"  视频尺寸: {STAGE_SIZE[0]} x {STAGE_SIZE[1]}")
    print(f"  帧率: {args.fps} fps")
    print("  输出时长: " + (
        f"{format_timestamp(DURATION, sep='.')}  ({DURATION:g} 秒)" if DURATION else "完整音频"))
    print(f"  过渡时长: {args.transition} 秒")
    print(f"  动画效果: {'启用（随机）' if random_animation else '禁用'}")
    print(f"  画面布局: {LAYOUT_NAME}")
    if SUBTITLE_PATH:
        print(f"  字幕文件: {SUBTITLE_PATH}")
    elif args.subtitles_enabled:
        print(f"  字幕文件: （未找到与音频同名的 {os.path.splitext(AUDIO_PATH)[0]}.srt，不叠加）")
    else:
        print("  字幕文件: （已关闭）")
    if SUBTITLE_PATH:
        font_name = SUBTITLE_OPTIONS["font_path"]
        print(
            "  字幕样式: "
            f"字号={SUBTITLE_OPTIONS['font_size'] or '自适应'} "
            f"字体={'自动' if not font_name else os.path.basename(font_name)} "
            f"底部={SUBTITLE_OPTIONS['bottom_ratio']:.0%} "
            f"行距={SUBTITLE_OPTIONS['line_spacing']} "
            f"文字=rgba{SUBTITLE_OPTIONS['text_color']} "
            f"底色=rgba{SUBTITLE_OPTIONS['box_color']}"
        )
    print(f"  编码器: {ENCODER}" + (f" (preset={args.preset})" if ENCODER == 'libx264' else ''))
    print(f"  码率: {args.bitrate}")
    print("=" * 60)

    start_time = time.time()

    create_slideshow(
        media_items=media_items,
        audio_path=AUDIO_PATH,
        output_path=args.output,
        audio_duration=DURATION or 0,
        transition_duration=args.transition,
        stage_size=STAGE_SIZE,
        fps=args.fps,
        animation_config=animation,
        random_animation=random_animation,
        subtitle_path=SUBTITLE_PATH,
        subtitle_options=SUBTITLE_OPTIONS,
        layout_name=LAYOUT_NAME,
        layout_options=LAYOUT_OPTIONS,
        encoder=ENCODER,
        preset=args.preset,
        bitrate=args.bitrate,
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
