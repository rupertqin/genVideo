# import moviepy
# print(f"Version: {moviepy.__version__}")  # 应 ≥2.0.0
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os
import subprocess


def create_slideshow(image_paths, audio_path, output_path,
                     duration_per_image=5, transition_duration=1,
                     img_size=(1280, 720), fps=30, audio_duration=0):
    """
    创建新版 MoviePy 的渐变轮播视频

    参数说明与旧版一致，但内部实现适配 v2.x API
    """
    if not audio_duration or audio_duration <= 0:
        audio_duration = get_audio_duration_ffmpeg(audio_path)
    print(f"音频时长: {audio_duration} 秒 (使用音频文件: {audio_path})")
    audio = AudioFileClip(audio_path)
    if audio_duration and audio_duration > 0:
        audio = audio.subclipped(0, audio_duration)

    # 计算每张图片显示时长和循环次数，确保视频时长与音频完全一致
    n_images = len(image_paths)
    repeated_images = []
    total_duration = 0.0
    idx = 0
    while total_duration < audio_duration:
        repeated_images.append(image_paths[idx % n_images])
        total_duration += duration_per_image
        idx += 1
    # 最后一张图片的时长用剩余音频时长补齐
    durations = [duration_per_image] * (len(repeated_images) - 1)
    last_img_duration = audio_duration - duration_per_image * (len(repeated_images) - 1)
    overlap_total = transition_duration * (len(repeated_images) - 1)
    last_img_duration += overlap_total
    durations.append(last_img_duration)

    clips = []
    for i, (img_path, img_duration) in enumerate(zip(repeated_images, durations)):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"图片不存在: {img_path}")
        clip = ImageClip(img_path, duration=img_duration)
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
        if i < len(repeated_images) - 1:
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
    final_video = final_video.subclipped(0, audio_duration)

    final_video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4
    )
    print(f"视频生成成功: {output_path}")

def get_audio_duration_ffmpeg(audio_path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", audio_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    # Decode ffprobe output and handle possible errors
    output = result.stdout.decode().strip() if result.stdout else ""
    try:
        return float(output)
    except Exception:
        raise RuntimeError(f"无法获取音频时长（ffprobe 输出）：{output}")

if __name__ == "__main__":
    # 示例配置（需替换实际路径）
    IMAGE_DIR = "images"
    def get_image_paths(dir_path):
        """Return image file paths from `dir_path` in filesystem read order.

        Note: the user indicated images may be unordered; we keep the
        directory reading order (no explicit sorting).
        """
        exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}
        try:
            names = os.listdir(dir_path)
        except FileNotFoundError:
            return []
        paths = [os.path.join(dir_path, name) for name in names
                 if os.path.splitext(name)[1].lower() in exts]
        return paths

    IMAGE_PATHS = get_image_paths(IMAGE_DIR)
    if not IMAGE_PATHS:
        print(f"未在目录 `{IMAGE_DIR}` 中找到图片，请检查路径。")
        raise SystemExit(1)

    def get_audio_path():
        """Return existing audio file path. Prefer WAV over MP3.

        Looks in the current working directory for `audio.wav` then
        `audio.mp3` and returns the first match. Returns `None` if
        neither exists.
        """
        candidates = ["audio.wav", "audio.mp3"]
        for name in candidates:
            if os.path.exists(name):
                return name
        return None

    AUDIO_PATH = get_audio_path()
    if not AUDIO_PATH:
        print("未找到 `audio.wav` 或 `audio.mp3`，请在项目根目录放置音频文件（或修改脚本）。")
        raise SystemExit(1)

    OUTPUT_PATH = "generated.mp4"


    create_slideshow(
        image_paths=IMAGE_PATHS,
        audio_path=AUDIO_PATH,
        output_path=OUTPUT_PATH,
        audio_duration=30,
        duration_per_image=3,
        transition_duration=1,
        img_size=(720, 1280),
        fps=24
    )
