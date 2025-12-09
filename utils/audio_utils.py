"""
音频处理工具模块
提供音频时长获取和停顿点检测功能
"""
import av
import numpy as np


def get_audio_duration_ffmpeg(audio_path):
    """
    使用 PyAV 获取音频文件的时长

    参数:
        audio_path (str): 音频文件路径

    返回:
        float: 音频时长（秒）

    异常:
        RuntimeError: 无法获取音频时长时抛出
    """
    try:
        with av.open(audio_path) as container:
            audio_stream = container.streams.audio[0]
            # 使用 duration 和 time_base 计算时长
            if audio_stream.duration:
                duration = float(audio_stream.duration * audio_stream.time_base)
            else:
                # 如果流没有 duration，使用容器的 duration
                duration = float(container.duration) / av.time_base
            return duration
    except Exception as e:
        raise RuntimeError(f"无法获取音频时长（PyAV）：{e}")


def get_audio_pauses(audio_path, min_pause=0.5, noise_threshold=-35, min_interval=5.0):
    """
    使用 PyAV 检测音频静音区间，返回停顿时间点集合。
    只有停顿时长 >= min_pause 才计入。
    过滤掉间隔小于 min_interval 的停顿点。

    参数:
        audio_path (str): 音频文件路径
        min_pause (float): 最小停顿时长（秒）
        noise_threshold (float): 噪音阈值（dB），默认 -35dB
        min_interval (float): 停顿点之间的最小间隔（秒），默认 5.0

    返回:
        list: 停顿开始时间点列表（单位：秒），已过滤间隔过小的点
    """
    pauses = []

    try:
        with av.open(audio_path) as container:
            audio_stream = container.streams.audio[0]

            # 重采样到单声道，便于处理
            resampler = av.audio.resampler.AudioResampler(
                format='s16',
                layout='mono',
                rate=audio_stream.rate
            )

            silence_start = None
            current_time = 0.0
            frame_duration = 0.0

            for frame in container.decode(audio=0):
                # 重采样为单声道
                frame = resampler.resample(frame)
                if not frame:
                    continue
                frame = frame[0]

                # 将音频帧转换为 numpy 数组
                audio_array = frame.to_ndarray()

                # 计算当前帧的时间戳
                if frame.pts is not None:
                    current_time = float(frame.pts * frame.time_base)

                # 计算帧时长
                frame_duration = float(frame.samples) / frame.sample_rate

                # 计算帧的 RMS（均方根）振幅，并归一化到 [0, 1]
                if audio_array.size > 0:
                    # 归一化到 [-1, 1] 范围
                    audio_normalized = audio_array.astype(np.float32) / 32768.0

                    # 计算 RMS
                    rms = np.sqrt(np.mean(audio_normalized ** 2))

                    # 转换为 dB
                    if rms > 0:
                        rms_db = 20 * np.log10(rms)
                    else:
                        rms_db = -100  # 极小值

                    # 检测静音
                    is_silent = rms_db < noise_threshold

                    if is_silent:
                        if silence_start is None:
                            silence_start = current_time
                    else:
                        if silence_start is not None:
                            silence_duration = current_time - silence_start
                            if silence_duration >= min_pause:
                                pauses.append(silence_start)
                            silence_start = None

            # 处理结尾的静音
            if silence_start is not None:
                silence_duration = (current_time + frame_duration) - silence_start
                if silence_duration >= min_pause:
                    pauses.append(silence_start)

    except Exception as e:
        print(f"警告：检测音频停顿时出错（PyAV）：{e}")
        import traceback
        traceback.print_exc()
        return []

    # 过滤掉间隔小于 min_interval 的停顿点
    if min_interval > 0 and len(pauses) > 0:
        filtered_pauses = []
        last_point = 0.0
        for point in pauses:
            if point - last_point >= min_interval:
                filtered_pauses.append(point)
                last_point = point
        return filtered_pauses

    return pauses
