# import moviepy
# print(f"Version: {moviepy.__version__}")  # 应 ≥2.0.0
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
import os
import subprocess


def create_slideshow(image_paths, audio_path, output_path,
                     duration_per_image=5, transition_duration=1,
                     img_size=(1280, 720), fps=24):
    """
    创建新版 MoviePy 的渐变轮播视频

    参数说明与旧版一致，但内部实现适配 v2.x API
    """
    # 用 ffmpeg 获取音频时长（更准确）
    audio_duration = get_audio_duration_ffmpeg(audio_path)
    audio = AudioFileClip(audio_path)

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
    durations.append(last_img_duration)

    clips = []
    for i, (img_path, img_duration) in enumerate(zip(repeated_images, durations)):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"图片不存在: {img_path}")
        clip = ImageClip(img_path, duration=img_duration)
        clip = clip.resized(new_size=img_size)
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
    return float(result.stdout)

if __name__ == "__main__":
    # 示例配置（需替换实际路径）
    IMAGE_PATHS = [f"images/image_{i}.jpg" for i in range(1, 11)]
    AUDIO_PATH = "audio.mp3"
    OUTPUT_PATH = "generated.mp4"

    audio_duration = get_audio_duration_ffmpeg(AUDIO_PATH)
    print(f"音频时长: {audio_duration} 秒")

    create_slideshow(
        image_paths=IMAGE_PATHS,
        audio_path=AUDIO_PATH,
        output_path=OUTPUT_PATH,
        duration_per_image=5,
        transition_duration=1,
        img_size=(1920, 1080),
        fps=30
    )
