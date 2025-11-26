"""
视频生成主脚本
使用 moviepy 创建图片轮播视频，支持音频配合和过渡效果
"""
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os

# 导入工具模块
from utils.audio_utils import get_audio_duration_ffmpeg, get_audio_pauses
from utils.image_utils import get_image_paths, get_audio_path
from utils.slideshow_utils import SlideshowController


def create_slideshow(image_paths, audio_path, output_path,
                     duration_per_image=5, transition_duration=1,
                     img_size=(1280, 720), fps=30, audio_duration=0):
    """
    创建新版 MoviePy 的渐变轮播视频

    参数说明:
        image_paths (list): 图片文件路径列表
        audio_path (str): 音频文件路径
        output_path (str): 输出视频文件路径
        duration_per_image (int): 每张图片的显示时长（秒）
        transition_duration (int): 过渡效果时长（秒）
        img_size (tuple): 输出视频分辨率 (width, height)
        fps (int): 视频帧率
        audio_duration (float): 目标音频时长，0表示使用原始音频时长

    内部实现适配 v2.x API
    """
    if not audio_duration or audio_duration <= 0:
        audio_duration = get_audio_duration_ffmpeg(audio_path)
    print(f"音频时长: {audio_duration} 秒 (使用音频文件: {audio_path})")
    audio = AudioFileClip(audio_path)
    if audio_duration and audio_duration > 0:
        audio = audio.subclipped(0, audio_duration)

    # 检测音频停顿点
    pause_points = get_audio_pauses(audio_path, min_pause=0.7)
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
        clip = ImageClip(img_path, duration=duration)
        video_w, video_h = img_size
        img_w, img_h = clip.size
        scale = max(video_w / img_w, video_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        clip = clip.resized(new_size=(new_w, new_h))
        clip = clip.with_position(("center", "center"))
        clip = CompositeVideoClip([clip], size=img_size)
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
    # 示例配置（需替换实际路径）
    IMAGE_DIR = "images"
    OUTPUT_PATH = "generated.mp4"

    # 使用工具函数获取资源路径
    IMAGE_PATHS = get_image_paths(IMAGE_DIR)
    if not IMAGE_PATHS:
        print(f"未在目录 `{IMAGE_DIR}` 中找到图片，请检查路径。")
        raise SystemExit(1)

    AUDIO_PATH = get_audio_path()
    if not AUDIO_PATH:
        print("未找到 `audio.wav` 或 `audio.mp3`，请在项目根目录放置音频文件（或修改脚本）。")
        raise SystemExit(1)

    create_slideshow(
        image_paths=IMAGE_PATHS,
        audio_path=AUDIO_PATH,
        output_path=OUTPUT_PATH,
        audio_duration=0,
        duration_per_image=3,
        transition_duration=1,
        img_size=(720, 1280),
        fps=24
    )
