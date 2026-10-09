"""
编码器选择与参数组装。

把硬件编码器探测、``auto`` 解析、MoviePy / ffmpeg 两套编码参数集中在这里，
供 ``frame`` 后端（MoviePy）与 ``ffmpeg`` 后端共用。
"""
from __future__ import annotations

import subprocess
from typing import List, Optional

# 硬件 H.264 编码器候选（按优先级）；仅在显式使用 auto 时才会被采用
HARDWARE_ENCODERS = ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf")

# 软件编码器（preset 参数对其生效）
SOFTWARE_ENCODERS = ("libx264",)


def detect_hardware_encoder() -> Optional[str]:
    """
    探测 ffmpeg 是否带硬件 H.264 编码器（通过 moviepy 自带的 imageio_ffmpeg）。

    返回:
        str or None: 第一个可用的硬件编码器名，没有则 None
    """
    encoders_output = _list_encoders_imageio()
    if not encoders_output:
        return None
    for name in HARDWARE_ENCODERS:
        if name in encoders_output:
            return name
    return None


def _list_encoders_imageio() -> Optional[str]:
    """只通过 imageio_ffmpeg 提供的 ffmpeg 探测；不可用时安全返回 None。"""
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception:
        return None


def _ffmpeg_candidates() -> List[str]:
    """候选 ffmpeg 可执行文件：imageio_ffmpeg 自带 + 系统 PATH。"""
    candidates: List[str] = []
    try:
        import imageio_ffmpeg

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    candidates.append("ffmpeg")
    return candidates


def resolve_encoder(encoder: str) -> str:
    """
    解析最终编码器：``auto`` 时探测硬件编码器，探测不到回退 libx264。

    返回:
        str: 最终编码器名（不会是 "auto"）
    """
    if encoder != "auto":
        return encoder
    detected = detect_hardware_encoder()
    if detected:
        print(f"已自动选择硬件编码器: {detected}")
        return detected
    print("未检测到可用的硬件编码器，回退到 libx264")
    return "libx264"


def is_hardware_encoder(encoder: str) -> bool:
    """是否为硬件编码器（不传 preset 参数）。"""
    return encoder in HARDWARE_ENCODERS


def build_write_kwargs(fps, encoder, preset, bitrate) -> dict:
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


def build_ffmpeg_encode_args(encoder: str, preset: Optional[str], bitrate: str) -> List[str]:
    """
    组装 ffmpeg 命令行里的视频编码参数（供 ffmpeg 滤镜链后端使用）。

    返回:
        list[str]: 形如 ``["-c:v", "h264_videotoolbox", "-b:v", "5000k", ...]``
    """
    args = ["-c:v", encoder]
    if encoder == "libx264" and preset:
        args += ["-preset", preset]
    if bitrate:
        args += ["-b:v", bitrate]
    if encoder == "h264_videotoolbox":
        # VideoToolbox 需要允许软件回退，否则部分分辨率为奇数或非常规时编码失败
        args += ["-allow_sw", "1"]
    return args
