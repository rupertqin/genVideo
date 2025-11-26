class SlideshowController:
    """
    控制图片轮播切换，按 change_points 切换图片。
    """
    def __init__(self, image_paths, change_points):
        self.image_paths = image_paths
        self.change_points = change_points
        self.n_images = len(image_paths)
        self.idx = 0
        self.time = 0.0

    def next(self):
        """
        切换到下一个图片，返回图片路径和当前时间区间。
        """
        if self.idx >= len(self.change_points) - 1:
            return None  # 已到结尾
        img_path = self.image_paths[self.idx % self.n_images]
        start = self.change_points[self.idx]
        end = self.change_points[self.idx + 1]
        self.idx += 1
        return img_path, start, end
def get_audio_pauses(audio_path, min_pause=0.5):
    """
    使用 ffmpeg 的 silencedetect 检测音频静音区间，返回停顿时间点集合。
    只有停顿时长 >= min_pause 才计入。
    返回值：停顿结束时间点列表（单位：秒）
    """
    import re
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", f"silencedetect=noise=-36dB:d={min_pause}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode(errors="ignore")
    # 匹配 silence_start/silence_end
    silence_starts = [float(m.group(1)) for m in re.finditer(r"silence_start: ([\d\.]+)", output)]
    silence_durations = [float(m.group(1)) for m in re.finditer(r"silence_duration: ([\d\.]+)", output)]
    # 只保留停顿时长 >= min_pause 的停顿开始点
    pauses = []
    for start, dur in zip(silence_starts, silence_durations):
        if dur >= min_pause:
            pauses.append(start)
    return pauses
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

    # 检测音频停顿点
    pause_points = get_audio_pauses(audio_path, min_pause=0.7)
    print(f"检测到停顿点: {pause_points}")
    # 构造切换时间点序列
    change_points = [0.0] + pause_points + [audio_duration]
    # 可选：演示 next 控制逻辑
    controller = SlideshowController(image_paths, change_points)
    print("轮播切换顺序:")
    while True:
        result = controller.next()
        if result is None:
            break
        img_path, start, end = result
        print(f"图片: {os.path.basename(img_path)} | 时间区间: {start:.2f} - {end:.2f}")
    n_images = len(image_paths)
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
        audio_duration=0,
        duration_per_image=3,
        transition_duration=1,
        img_size=(720, 1280),
        fps=24
    )
