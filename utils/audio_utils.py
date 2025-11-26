"""
音频处理工具模块
提供音频时长获取和停顿点检测功能
"""
import re
import subprocess


def get_audio_duration_ffmpeg(audio_path):
    """
    使用 ffprobe 获取音频文件的时长

    参数:
        audio_path (str): 音频文件路径

    返回:
        float: 音频时长（秒）

    异常:
        RuntimeError: 无法获取音频时长时抛出
    """
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


def get_audio_pauses(audio_path, min_pause=0.5):
    """
    使用 ffmpeg 的 silencedetect 检测音频静音区间，返回停顿时间点集合。
    只有停顿时长 >= min_pause 才计入。

    参数:
        audio_path (str): 音频文件路径
        min_pause (float): 最小停顿时长（秒）

    返回:
        list: 停顿结束时间点列表（单位：秒）
    """
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
