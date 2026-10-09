"""
字幕处理工具模块

字幕解析基于 PyAV 的 Subtitle API（av.subtitles）：
    - 将 SRT/ASS 等字幕文件解复用为 SubtitleSet，再读取每个 rect 的
      AssSubtitle.dialogue 得到文本，配合 SubtitleSet.pts /
      start_display_time / end_display_time 得到时间轴。
渲染部分使用 Pillow 把每条字幕画成带描边与半透明底色的 RGBA 图，
再由 MoviePy 叠加到成片上去（硬字幕 / 烧录字幕）。
"""
from __future__ import annotations

import bisect
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import av
import numpy as np

# 支持的字幕文件后缀（按优先级）
SUBTITLE_EXTS = (".srt", ".ass", ".ssa", ".vtt")

# 常见中文字体候选（按平台顺序查找，取第一个存在的）
FONT_CANDIDATES = (
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    # Linux
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # Windows
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


@dataclass
class SubtitleCue:
    """单条字幕：起止时间（秒）与文本"""

    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        """字幕显示时长（秒），不会为负"""
        return max(0.0, self.end - self.start)


def _ass_tail(ass) -> Optional[bytes]:
    """
    从 ASS dialogue 行中取出正文部分。

    形如 ``0,0,Default,,0,0,0,,文本`` 或
    ``0,0:00:00.00,0:00:02.00,Default,,0,0,0,,文本``，
    正文是最后一个字段（最多切 10 段，正文内的逗号会被保留）。
    """
    if not ass:
        return None
    if isinstance(ass, (bytes, bytearray)):
        return bytes(ass).split(b",", 9)[-1]
    return str(ass).split(",", 9)[-1].encode("utf-8")


def _rect_to_text(rect) -> str:
    """
    从 PyAV 的 Subtitle rect 中取出可读文本。

    优先用 ``AssSubtitle.dialogue``；部分 PyAV 版本（如 16.x）该属性对
    非 ASCII 文本会抛 ``ValueError``，因此再回退到 ``ass`` 行解析、
    最后才用 ``text``。文本中的 ASS ``\\N`` 换行符会被归一为空格。
    """
    raw = None
    try:
        raw = getattr(rect, "dialogue", None)
    except Exception:
        raw = None

    if not raw:
        try:
            ass = getattr(rect, "ass", None)
        except Exception:
            ass = None
        raw = _ass_tail(ass)

    if not raw:
        try:
            raw = getattr(rect, "text", None)
        except Exception:
            raw = None

    if not raw:
        return ""
    if isinstance(raw, (bytes, bytearray)):
        text = bytes(raw).decode("utf-8", "replace")
    else:
        text = str(raw)
    text = text.replace("\\N", " ").replace("\\n", " ")
    text = text.replace("\r", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def load_subtitles(path: str) -> List[SubtitleCue]:
    """
    使用 PyAV 解析字幕文件，返回按开始时间排序的字幕列表。

    参数:
        path (str): 字幕文件路径（通常为 .srt）

    返回:
        list[SubtitleCue]: 字幕条目；文件为空或无有效字幕时返回空列表

    异常:
        FileNotFoundError: 字幕文件不存在时抛出
    """
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"字幕文件不存在: {path}")

    cues: List[SubtitleCue] = []
    try:
        container = av.open(path)
    except av.FFmpegError:
        # 空文件 / 无有效字幕流时 PyAV 会抛错，视为「无字幕」
        return cues

    with container:
        streams = list(container.streams.subtitles)
        if not streams:
            return cues

        stream = streams[0]
        for packet in container.demux(stream):
            # 结尾的 flush 包没有时间戳，跳过
            if packet.dts is None:
                continue
            subtitle_set = stream.decode2(packet)
            if subtitle_set is None:
                continue

            # pts 以 av.time_base 为单位；display_time 以毫秒为单位
            base = (subtitle_set.pts or 0) / av.time_base
            start = base + (subtitle_set.start_display_time or 0) / 1000.0
            end = base + (subtitle_set.end_display_time or 0) / 1000.0

            for rect in subtitle_set.rects:
                text = _rect_to_text(rect)
                if text:
                    cues.append(SubtitleCue(max(0.0, start), max(start, end), text))

    cues.sort(key=lambda cue: cue.start)
    return cues


def format_timestamp(seconds: float, sep: str = ",") -> str:
    """
    将秒数格式化为 SRT 时间戳 ``HH:MM:SS,mmm``。

    参数:
        seconds (float): 秒数（负值按 0 处理）
        sep (str): 秒与毫秒的分隔符（SRT 为 ``,``，VTT 为 ``.``）

    返回:
        str: 时间戳字符串
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def cues_to_srt(cues: Sequence[SubtitleCue]) -> str:
    """
    将字幕列表序列化为 SRT 文本（便于回写与校验）。
    """
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(blocks)


def filter_cues(
    cues: Sequence[SubtitleCue],
    duration: Optional[float] = None,
) -> List[SubtitleCue]:
    """
    过滤出真正会显示的字幕：丢弃零时长、以及起点已在片尾之后的条目。

    参数:
        cues (Sequence[SubtitleCue]): 全部字幕
        duration (float): 成片时长（秒）；None 表示不限制

    返回:
        list[SubtitleCue]: 可用字幕
    """
    return [
        cue
        for cue in cues
        if cue.end > cue.start and not (duration and cue.start >= duration)
    ]


def find_subtitle_path(media_path: str) -> Optional[str]:
    """
    查找与给定媒体文件同名的字幕文件（audio.wav -> audio.srt）。

    参数:
        media_path (str): 音频/视频文件路径

    返回:
        str or None: 找到的字幕文件路径，否则 None
    """
    if not media_path:
        return None
    base, _ = os.path.splitext(media_path)
    for ext in SUBTITLE_EXTS:
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
    return None


def find_default_font() -> Optional[str]:
    """
    返回系统上第一个可用的中文字体路径，找不到时返回 None。
    """
    for font_path in FONT_CANDIDATES:
        if os.path.exists(font_path):
            return font_path
    return None


# 需要处理的标点：逗号和句号（含中英文），其余（？ ！ 等）保留
PUNCT_COMMA_PERIOD = "，,。."


def normalize_punctuation(text: str) -> str:
    """
    把逗号/句号替换为空格：句尾的因此被删掉，句中的变成空格。

    只处理 ``，`` ``。`` ``,`` ``.`` 四个字符，问号/感叹号等保留。
    """
    for char in PUNCT_COMMA_PERIOD:
        text = text.replace(char, " ")
    return " ".join(text.split()).strip()


def _wrap_text(text: str, font, max_width: float) -> List[str]:
    """
    按像素宽度把文本折行（中文按字符折，英文按整词尽力折）。
    """
    lines: List[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        current = ""
        for char in paragraph:
            if not current or font.getlength(current + char) <= max_width:
                current += char
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def render_subtitle_frame(
    text: str,
    size: Tuple[int, int],
    font_path: Optional[str] = None,
    font_size: Optional[int] = None,
    bottom_ratio: float = 0.08,
    max_width_ratio: float = 0.9,
    line_spacing: float = 1.25,
    stroke_width: int = 3,
    strip_punct: bool = False,
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    box_color: Tuple[int, int, int, int] = (0, 0, 0, 150),
) -> np.ndarray:
    """
    把一条字幕渲染成全屏 RGBA 图（背景透明），供叠加到视频帧。

    参数:
        text (str): 字幕文本
        size (tuple): 视频尺寸 (width, height)
        font_path (str): 字体文件路径，None 时自动查找
        font_size (int): 字号（像素），None 时按视频高度自适应
        bottom_ratio (float): 字幕底部留白占视频高度的比例
        max_width_ratio (float): 单行最大宽度占视频宽度的比例
        line_spacing (float): 行距倍数
        stroke_width (int): 文字描边宽度
        strip_punct (bool): 去掉逗号/句号（句尾删除、句中替换为空格）
        text_color (tuple): 文字颜色 RGBA
        box_color (tuple): 文字底色 RGBA（alpha 为 0 时不画底色）

    返回:
        numpy.ndarray: 形状 (height, width, 4) 的 uint8 RGBA 数组
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = int(size[0]), int(size[1])
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    text = (text or "").strip()
    if strip_punct:
        text = normalize_punctuation(text)
    if not text:
        return np.asarray(frame, dtype=np.uint8)

    if font_size is None:
        font_size = max(16, int(round(height * 0.05)))
    font_size = int(font_size)

    resolved_font = font_path or find_default_font()
    if resolved_font:
        font = ImageFont.truetype(resolved_font, font_size)
    else:
        font = ImageFont.load_default()

    max_width = width * max_width_ratio
    lines = _wrap_text(text, font, max_width)
    if not lines:
        return np.asarray(frame, dtype=np.uint8)

    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    line_gap = int(round(line_height * (line_spacing - 1.0)))
    total_height = line_height * len(lines) + line_gap * (len(lines) - 1)

    bottom_margin = height * bottom_ratio
    top = height - bottom_margin - total_height
    if top < 0:
        top = 0.0

    draw = ImageDraw.Draw(frame)
    pad_x, pad_y = int(font_size * 0.35), int(font_size * 0.18)
    y = top
    for line in lines:
        line_width = font.getlength(line)
        x = (width - line_width) / 2.0
        if box_color[3] > 0:
            draw.rounded_rectangle(
                [
                    x - pad_x,
                    y - pad_y,
                    x + line_width + pad_x,
                    y + line_height + pad_y,
                ],
                radius=int(font_size * 0.25),
                fill=box_color,
            )
        draw.text(
            (x, y),
            line,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 255),
        )
        y += line_height + line_gap

    return np.asarray(frame, dtype=np.uint8)


class _SubtitleOverlay:
    """
    按时间定位当前字幕，并按需渲染成 RGBA 图层。

    只缓存当前这一条字幕的图，因此数百条字幕也只占一张图的内存，
    避免为每条字幕预先生成全尺寸图层导致内存暴涨。
    """

    def __init__(self, cues: Sequence[SubtitleCue], size: Tuple[int, int], render_kwargs):
        self.cues = sorted(cues, key=lambda cue: cue.start)
        self.starts = [cue.start for cue in self.cues]
        self.size = (int(size[0]), int(size[1]))
        self.render_kwargs = render_kwargs
        self._current_index: Optional[int] = None
        self._frame = self._blank()

    def _blank(self) -> np.ndarray:
        return np.zeros((self.size[1], self.size[0], 4), dtype=np.uint8)

    def locate(self, t: float) -> Optional[int]:
        """返回 t 时刻命中字幕的下标，无字幕时返回 None"""
        index = bisect.bisect_right(self.starts, t) - 1
        if index >= 0 and t < self.cues[index].end:
            return index
        return None

    def frame_at(self, t: float):
        """返回 ``(RGBA 图层, 当前字幕下标)``，命中同一条时复用缓存"""
        index = self.locate(t)
        if index != self._current_index:
            self._current_index = index
            if index is None:
                self._frame = self._blank()
            else:
                self._frame = render_subtitle_frame(
                    self.cues[index].text, self.size, **self.render_kwargs
                )
        return self._frame, index

    def rgba(self, t: float) -> np.ndarray:
        """返回 t 时刻的字幕 RGBA 图层（命中同一条时复用缓存）"""
        return self.frame_at(t)[0]


def burn_subtitles(
    clip,
    cues: Sequence[SubtitleCue],
    video_size: Optional[Tuple[int, int]] = None,
    **render_kwargs,
):
    """
    把字幕烧录（硬字幕）到 MoviePy 视频片段上。

    直接用 numpy 把字幕图层混合到帧上，并且：
      - 每帧只渲染/缓存当前这一条字幕（成本与字幕条数无关）；
      - 无字幕的帧原样返回，零额外开销；
      - 有字幕的帧只在文字包围盒内做混合（避免整帧运算）。

    不用 ``CompositeVideoClip``：它每帧都要经 PIL 转换与粘贴，
    1080p 下会把编码吞吐拉低数倍（实测 35 fps -> 5.8 fps）。

    参数:
        clip: MoviePy 视频片段
        cues (list[SubtitleCue]): 字幕列表
        video_size (tuple): 视频尺寸，None 时取片段自身的 (w, h)
        **render_kwargs: 透传给 render_subtitle_frame 的参数

    返回:
        叠加字幕后新的 MoviePy 片段（无有效字幕时返回原片段）
    """
    from moviepy import VideoClip

    duration = getattr(clip, "duration", None)
    valid = filter_cues(cues, duration)
    if not valid:
        return clip

    width, height = video_size or (clip.w, clip.h)
    overlay = _SubtitleOverlay(valid, (width, height), render_kwargs)
    boxes: dict = {}  # 字幕下标 -> 文字包围盒 (y0, y1, x0, x1)，每条只算一次

    def frame_function(t):
        base = clip.get_frame(t)
        rgba, index = overlay.frame_at(t)
        if index is None:
            return base  # 无字幕帧：不做任何额外计算

        alpha = rgba[:, :, 3]
        box = boxes.get(index)
        if box is None:
            rows = np.flatnonzero(alpha.any(axis=1))
            cols = np.flatnonzero(alpha.any(axis=0))
            if not rows.size or not cols.size:
                boxes[index] = box = (0, 0, 0, 0)
            else:
                box = boxes[index] = (
                    int(rows[0]),
                    min(int(rows[-1]) + 1, base.shape[0]),
                    int(cols[0]),
                    min(int(cols[-1]) + 1, base.shape[1]),
                )
        y0, y1, x0, x1 = box
        if y1 <= y0 or x1 <= x0:
            return base

        out = base.copy()
        sub_alpha = rgba[y0:y1, x0:x1, 3:4].astype(np.float32) / 255.0
        out[y0:y1, x0:x1] = (
            base[y0:y1, x0:x1] * (1.0 - sub_alpha)
            + rgba[y0:y1, x0:x1, :3] * sub_alpha
        ).astype(out.dtype)
        return out

    result = VideoClip(frame_function, duration=duration)
    audio = getattr(clip, "audio", None)
    if audio is not None:
        result = result.with_audio(audio)
    return result
