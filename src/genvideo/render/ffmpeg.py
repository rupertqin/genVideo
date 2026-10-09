"""
ffmpeg 滤镜链渲染后端。

与 MoviePy 逐帧后端（frame）不同，这里把「缩放、转场、字幕」全部下推到
ffmpeg 的滤镜图（filter_complex），整条管线在 ffmpeg 内部完成，可搭配硬件
编码器，接近剪辑软件的速度。

适用场景：**纯图片轮播**（不支持视频混排与 Ken Burns 动画，遇到会自动回退
或报错）。视频/动画场景仍走 MoviePy 逐帧后端。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Optional, Sequence, Tuple

from genvideo.render.encoder import build_ffmpeg_encode_args, _ffmpeg_candidates
from genvideo.render.progress import default_progress_printer, parse_ffmpeg_progress
from genvideo.utils.layouts import render_layout_static
from genvideo.utils.media_utils import ensure_parent_dir, MediaType


def render_slideshow_ffmpeg(
    media_items: Sequence,
    change_points: Sequence[float],
    audio_path: str,
    output_path: str,
    stage_size: Tuple[int, int],
    fps: int,
    transition_duration: float,
    subtitle_path: Optional[str] = None,
    subtitle_options: Optional[dict] = None,
    encoder: str = "libx264",
    preset: Optional[str] = None,
    bitrate: Optional[str] = None,
    layout_name: str = "fullscreen",
    layout_options: Optional[dict] = None,
) -> None:
    """
    用纯 ffmpeg 滤镜链渲染图片轮播视频。

    参数:
        media_items: MediaItem 列表（只支持图片）
        change_points: 切换时间点（秒），含首尾 [0, ..., total]
        audio_path: 音频文件路径
        output_path: 输出文件路径
        stage_size: (width, height)
        fps: 帧率
        transition_duration: 转场时长（秒）
        subtitle_path: 字幕文件（.srt/.ass），None 表示不叠加
        subtitle_options: 字幕样式（font_size/bottom_ratio/text_color/stroke_width）
        encoder / preset / bitrate: 编码参数
        layout_name: 布局组件名（fullscreen / hero），与 frame 后端共用同一套定义
        layout_options: 布局参数（与 frame 后端一致）

    异常:
        ValueError: media_items 含视频，或 layout 暂不支持 ffmpeg 后端
        RuntimeError: ffmpeg 执行失败
    """
    widths = [int(stage_size[0]), int(stage_size[1])]
    durations = _segment_durations(change_points)

    # 只支持图片：遇到视频让调用方回退到逐帧后端
    for item in media_items:
        if item.media_type != MediaType.IMAGE:
            raise ValueError(
                f"ffmpeg 后端只支持图片轮播，遇到视频: {item.path}。"
                f"请改用逐帧后端（backend=frame）以支持视频/动画。"
            )

    # 渲染布局静态资源（背景图 + 渐隐 mask + 图片区域），复用 frame 后端的视觉定义
    static = render_layout_static(layout_name, stage_size, layout_options or {})
    if static is None:
        raise ValueError(f"ffmpeg 后端暂不支持 layout '{layout_name}'，请改用 backend=frame")

    effective_trans = _clamp_transition(transition_duration, durations)
    bg_path, mask_path, tmpdir = _dump_static(static)
    # 字幕：复用 frame 后端的 PIL 渲染（圆角底色 + 描边逐行），预渲染成透明 PNG，
    # 再由 ffmpeg overlay 叠加——彻底对齐 frame 后端的字幕样式，不用 libass 的直角 box。
    sub_overlays, sub_tmpdir = _prepare_subtitles(
        subtitle_path, stage_size, subtitle_options, sum(durations)
    )
    try:
        command = _build_command(
            media_items=media_items,
            durations=durations,
            audio_path=audio_path,
            output_path=output_path,
            size=widths,
            fps=fps,
            transition=effective_trans,
            sub_overlays=sub_overlays,
            encoder=encoder,
            preset=preset,
            bitrate=bitrate,
            bg_path=bg_path,
            mask_path=mask_path,
            hero_rect=static["hero_rect"],
        )
        ensure_parent_dir(output_path)
        print("ffmpeg 命令:", " ".join(command))
        _run_with_progress(command)
    finally:
        _cleanup(tmpdir)
        _cleanup(sub_tmpdir)


# --------------------------------------------------------------------------
# 内部实现
# --------------------------------------------------------------------------

def _segment_durations(change_points: Sequence[float]) -> List[float]:
    """把切换点转成每段时长列表。"""
    return [change_points[i + 1] - change_points[i] for i in range(len(change_points) - 1)]


def _clamp_transition(transition: float, durations: Sequence[float]) -> float:
    """xfade 的 duration 不能超过相邻段时长，这里做下限保护。"""
    if transition <= 0 or len(durations) < 2:
        return 0.0
    return max(0.0, min(float(transition), min(durations) - 0.01))


def _ffmpeg_exe() -> str:
    """取一个可用的 ffmpeg 可执行文件；都没有则回退字符串 "ffmpeg"（报错时可见）。"""
    for exe in _ffmpeg_candidates():
        return exe
    return "ffmpeg"


def _dump_static(static: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """把布局静态资源（背景图/渐隐 mask）落盘为临时 PNG，返回 (bg_path, mask_path, tmpdir)。"""
    bg = static.get("background")
    mask = static.get("mask")
    if bg is None and mask is None:
        return None, None, None
    tmpdir = tempfile.mkdtemp(prefix="genvideo_layout_")
    bg_path = None
    mask_path = None
    if bg is not None:
        bg_path = os.path.join(tmpdir, "background.png")
        bg.save(bg_path)
    if mask is not None:
        mask_path = os.path.join(tmpdir, "mask.png")
        mask.save(mask_path)
    return bg_path, mask_path, tmpdir


def _cleanup(tmpdir: Optional[str]) -> None:
    """安全删除临时目录（逐文件删除，再删目录；不使用 rm -rf / rmtree）。"""
    if not tmpdir or not os.path.isdir(tmpdir):
        return
    for name in os.listdir(tmpdir):
        try:
            os.remove(os.path.join(tmpdir, name))
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass


def _prepare_subtitles(
    subtitle_path: Optional[str],
    size: Tuple[int, int],
    options: Optional[dict],
    duration: float,
) -> Tuple[List[dict], Optional[str]]:
    """
    解析字幕并把每条字幕用 frame 后端的 PIL 渲染成透明 PNG。

    返回:
        (overlays, tmpdir)
        overlays: [{"path": str, "start": float, "end": float}, ...]
        tmpdir: 存放 PNG 的临时目录（无字幕时为 None）
    """
    if not subtitle_path:
        return [], None
    import numpy as np
    from PIL import Image

    from genvideo.utils.subtitle_utils import filter_cues, load_subtitles, render_subtitle_frame

    cues = filter_cues(load_subtitles(subtitle_path), duration)
    if not cues:
        return [], None

    tmpdir = tempfile.mkdtemp(prefix="genvideo_sub_")
    overlays: List[dict] = []
    for i, cue in enumerate(cues):
        rgba = render_subtitle_frame(cue.text, size, **(options or {}))
        # 裁剪到 alpha 包围盒，避免每条字幕都是全尺寸 PNG（解码开销大）
        ys, xs = np.nonzero(rgba[:, :, 3])
        if ys.size == 0:
            continue
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        path = os.path.join(tmpdir, f"sub_{i:04d}.png")
        Image.fromarray(rgba[y0:y1, x0:x1]).save(path)
        overlays.append({"path": path, "start": cue.start, "end": cue.end, "x": x0, "y": y0})
    return overlays, tmpdir


def _build_command(
    media_items: Sequence,
    durations: List[float],
    audio_path: str,
    output_path: str,
    size: List[int],
    fps: int,
    transition: float,
    sub_overlays: List[dict],
    encoder: str,
    preset: Optional[str],
    bitrate: Optional[str],
    bg_path: Optional[str],
    mask_path: Optional[str],
    hero_rect: Tuple[int, int, int, int],
) -> List[str]:
    """组装完整 ffmpeg 命令（背景/图片输入 + filter_complex + 音频 + 编码）。"""
    n = len(durations)
    command = [_ffmpeg_exe(), "-hide_banner", "-y"]
    has_bg = bg_path is not None
    total = sum(durations)

    # 背景段输入（hero 布局的静态背景，每段一个 loop 供 overlay 用）
    if has_bg:
        for i, dur in enumerate(durations):
            input_dur = dur + (transition if i < n - 1 else 0.0)
            command += ["-loop", "1", "-framerate", str(fps), "-t", f"{input_dur:.4f}", "-i", bg_path]

    # 图片段输入（每段一张，循环使用，多给 transition 时长用于 xfade 重叠）
    for i, dur in enumerate(durations):
        item = media_items[i % len(media_items)]
        input_dur = dur + (transition if i < n - 1 else 0.0)
        command += ["-loop", "1", "-framerate", str(fps), "-t", f"{input_dur:.4f}", "-i", item.path]

    # 渐隐 mask 输入（loop 以对齐各段时长）
    if mask_path:
        command += ["-loop", "1", "-framerate", str(fps), "-i", mask_path]

    # 字幕透明 PNG 输入（每条 loop 整个时长，由 overlay 的 enable 控制显示窗口）
    for ov in sub_overlays:
        command += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.4f}", "-i", ov["path"]]

    # 音频输入
    command += ["-i", audio_path]

    img_base = n if has_bg else 0
    mask_idx = img_base + n if mask_path else None
    sub_base = (mask_idx + 1) if mask_idx is not None else (img_base + n)
    audio_idx = sub_base + len(sub_overlays)

    command += ["-filter_complex", _build_filter_complex(
        durations, size, transition, sub_overlays, sub_base,
        img_base=img_base, mask_idx=mask_idx, has_bg=has_bg,
        has_mask=mask_path is not None, hero_rect=hero_rect,
    )]
    command += ["-map", "[vout]"]
    command += ["-map", f"{audio_idx}:a:0"]

    command += build_ffmpeg_encode_args(encoder, preset, bitrate)
    command += ["-c:a", "aac", "-b:a", "192k", "-r", str(fps)]

    # 精确截断到音频总时长（xfade 的边界误差由这里兜底）
    total = sum(durations)
    command += ["-t", f"{total:.4f}"]

    # 实时进度到 stdout
    command += ["-progress", "pipe:1", "-nostats", "-loglevel", "error"]
    command += [output_path]
    return command


def _build_filter_complex(
    durations: List[float],
    size: List[int],
    transition: float,
    sub_overlays: List[dict],
    sub_base: int,
    img_base: int,
    mask_idx: Optional[int],
    has_bg: bool,
    has_mask: bool,
    hero_rect: Tuple[int, int, int, int],
) -> str:
    """
    生成 filter_complex 字符串。

    结构：图片 cover → (alphamerge 渐隐 mask) → (overlay 静态背景) → 串段(concat/xfade) → 字幕 overlay。
    fullscreen（无背景无 mask）时等价于「图片 cover 铺满」。
    """
    w, h = size
    n = len(durations)
    hx, hy, hw, hh = hero_rect

    parts: List[str] = []
    for i in range(n):
        img_idx = img_base + i
        cover = (
            f"[{img_idx}:v]scale={hw}:{hh}:force_original_aspect_ratio=increase,"
            f"crop={hw}:{hh},setsar=1"
        )
        if has_bg:
            if has_mask:
                parts.append(f"{cover},format=rgba[imgc{i}]")
                parts.append(f"[imgc{i}][{mask_idx}:v]alphamerge[imga{i}]")
                parts.append(f"[{i}:v][imga{i}]overlay={hx}:{hy}[seg{i}]")
            else:
                parts.append(f"{cover}[imgc{i}]")
                parts.append(f"[{i}:v][imgc{i}]overlay={hx}:{hy}[seg{i}]")
        else:
            parts.append(f"{cover},format=yuv420p[seg{i}]")

    # 串段：无转场用 concat；有转场用 xfade 链
    if transition <= 0 or n == 1:
        last_label = "[seg0]"
        if n > 1:
            concat_inputs = "".join(f"[seg{i}]" for i in range(n))
            parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vout0]")
            last_label = "[vout0]"
    else:
        cur = "[seg0]"
        offset = 0.0
        for k in range(1, n):
            offset += durations[k - 1]
            out_label = f"[x{k}]" if k < n - 1 else "[vout0]"
            parts.append(
                f"{cur}[seg{k}]xfade=transition=fade:duration={transition:.4f}:"
                f"offset={offset:.4f}{out_label}"
            )
            cur = out_label
        last_label = "[vout0]"

    # 字幕：用预渲染的透明 PNG overlay（裁剪到文字包围盒，x/y 定位 + enable 时间窗）
    if sub_overlays:
        cur = last_label
        for i, ov in enumerate(sub_overlays):
            out_label = f"[subov{i}]" if i < len(sub_overlays) - 1 else "[vout]"
            parts.append(
                f"{cur}[{sub_base + i}:v]overlay={ov['x']}:{ov['y']}:"
                f"enable='between(t,{ov['start']:.4f},{ov['end']:.4f})'{out_label}"
            )
            cur = out_label
    else:
        parts.append(f"{last_label}null[vout]")

    return ";".join(parts)


def _run_with_progress(command: List[str]) -> None:
    """执行 ffmpeg，逐行解析 -progress 输出并打印实时速度。"""
    printer = default_progress_printer(prefix="渲染")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    state: dict = {}
    assert process.stdout is not None
    for line in process.stdout:
        parse_ffmpeg_progress(line, state)
        # ffmpeg 以 `progress=continue/end` 结束一个进度块，此时 state 才完整
        if state.get("progress"):
            printer(state)

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()
    print()  # 换行，结束 \r 进度行

    if return_code != 0:
        raise RuntimeError(f"ffmpeg 渲染失败（退出码 {return_code}）:\n{stderr}")
