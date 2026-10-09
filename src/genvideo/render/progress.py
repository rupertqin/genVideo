"""
渲染进度与速度计时。

两个用途：
1. ``FpsMeter`` — 计时 + 平均 fps / 实时 fps，供 MoviePy 逐帧后端总结用。
2. ``parse_ffmpeg_progress`` — 解析 ffmpeg ``-progress`` 输出里的进度字段
   （frame / fps / speed / out_time），供 ffmpeg 滤镜链后端实时打印。
"""
from __future__ import annotations

import sys
import time
from typing import Callable, Dict, Optional


class FpsMeter:
    """累计计时器：记录起止时间、总帧数，算平均 fps。"""

    def __init__(self):
        self._start: Optional[float] = None
        self._end: Optional[float] = None
        self._frames = 0

    def start(self) -> None:
        self._start = time.time()

    def stop(self, frames: int = 0) -> None:
        self._end = time.time()
        self._frames = frames

    @property
    def elapsed(self) -> float:
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.time()
        return end - self._start

    @property
    def fps(self) -> Optional[float]:
        """平均帧率；未记录帧数时返回 None。"""
        if self._frames <= 0 or self.elapsed <= 0:
            return None
        return self._frames / self.elapsed

    def summary(self, label: str = "渲染") -> str:
        """格式化耗时与平均速度。"""
        if self.fps is None:
            return f"{label}: 耗时 {self.elapsed:.2f} 秒"
        return f"{label}: 耗时 {self.elapsed:.2f} 秒，平均 {self.fps:.1f} fps"


def parse_ffmpeg_progress(line: str, state: Dict) -> None:
    """
    解析 ffmpeg ``-progress pipe:1`` 输出的一行，更新 state 字典。

    ffmpeg 以 ``key=value`` 逐行输出，每个进度块以 ``progress=...`` 结尾。
    这里只关心 ``frame`` / ``fps`` / ``speed`` / ``out_time`` / ``progress``。
    """
    line = line.strip()
    if not line or "=" not in line:
        return
    key, _, value = line.partition("=")
    if key in ("frame", "fps", "speed", "out_time", "out_time_ms", "progress", "bitrate"):
        state[key] = value


def default_progress_printer(prefix: str = "渲染进度") -> Callable[[Dict], None]:
    """
    返回一个按「每秒最多打印一次」节流的进度打印回调。

    回调入参是 ``parse_ffmpeg_progress`` 累积出的 state 字典，打印当前
    帧/时间与实时 fps/speed。
    """
    last = {"t": 0.0}

    def printer(state: Dict) -> None:
        now = time.time()
        if now - last["t"] < 1.0:
            return
        last["t"] = now
        out_time = state.get("out_time") or state.get("out_time_ms")
        fps = state.get("fps") or "-"
        speed = state.get("speed") or "-"
        bits = [f"t={out_time}", f"fps={fps}", f"speed={speed}x"]
        msg = f"\r{prefix}: " + "  ".join(bits)
        sys.stdout.write(msg)
        sys.stdout.flush()

    return printer
