"""
视觉布局组件模块（可插拔的画面层）

每个布局是一个函数：给定源图、画布尺寸、时长、选项，返回一个
``frame(t) -> ndarray`` 的帧函数（通常对静态画面预计算一次，逐帧复用）。

已注册布局：
    fullscreen  — 全屏铺满 + 居中裁剪（默认）
    card        — 背景模糊压暗铺满 + 前景留边卡片（不铺满）+ 标题

新布局用 ``@register_layout("名字")`` 注册即可，随后在 config.yaml 里
``video.layout`` 切换。
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import parse_color
from utils.subtitle_utils import find_default_font
from utils.video_utils import fit_frame

# 布局注册表：名字 -> 布局函数
LAYOUTS: Dict[str, Callable] = {}


def register_layout(name):
    """装饰器：把一个布局函数注册到名字下"""

    def decorator(func):
        LAYOUTS[name] = func
        return func

    return decorator


def get_layout(name):
    """按名字取布局函数，未知名字返回 None"""
    return LAYOUTS.get(name)


def list_layouts():
    """列出所有已注册的布局名"""
    return sorted(LAYOUTS)


def _load_font(size):
    """加载中文字体；找不到时回退到 PIL 默认字体"""
    path = find_default_font()
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit_title_font(text, max_width, base_size):
    """把标题字号缩到单行能放下的程度"""
    size = max(12, int(base_size))
    font = _load_font(size)
    while size > 12 and font.getlength(text) > max_width:
        size -= 2
        font = _load_font(size)
    return font


@register_layout("fullscreen")
def fullscreen_layout(source, video_size, duration, options=None):
    """
    全屏铺满：图片覆盖式缩放 + 居中裁剪（当前默认行为）。

    options:
        position (str): 裁剪位置（center/left/right/top/bottom 等），默认 center
    """
    position = (options or {}).get("position", "center")
    frame = fit_frame(source, video_size, position=position)
    return lambda t: frame


@register_layout("card")
def card_layout(source, video_size, duration, options=None):
    """
    卡片式：背景用模糊 + 压暗的图片铺满，前景放一张留边距、圆角、带阴影的卡片，
    卡片顶部（或底部）显示标题。

    options:
        inset (float): 卡片四周留白，占短边的比例（默认 0.07）
        radius (int): 卡片圆角半径（像素，默认 40）
        shadow (int): 阴影模糊半径（像素，默认 24；0 = 不画阴影）
        background_blur (float): 背景高斯模糊半径（默认 24）
        background_darken (float): 背景压暗强度 0~1（默认 0.35）
        title (str): 标题文字（None 表示不显示）
        title_size (int): 标题字号（默认 60）
        title_color: 标题颜色（"#RRGGBB" / [r,g,b] 等，默认白）
        title_position (str): 标题在卡片的 top / bottom（默认 top）
    """
    options = options or {}
    frame = _render_card_frame(source, video_size, options)
    return lambda t: frame


def _render_card_frame(source, video_size, options) -> np.ndarray:
    """渲染一张静态卡片帧（背景 + 前景卡片 + 标题）"""
    width, height = int(video_size[0]), int(video_size[1])

    inset = float(options.get("inset", 0.07))
    radius = int(options.get("radius", 40))
    shadow = int(options.get("shadow", 24))
    blur = float(options.get("background_blur", 24))
    darken = float(options.get("background_darken", 0.35))

    title = str(options.get("title") or "").strip()
    title_size = int(options.get("title_size", 60))
    title_color = parse_color(options.get("title_color"), 255) or (255, 255, 255, 255)
    title_position = options.get("title_position", "top")

    inset_px = int(round(min(width, height) * inset))

    # 1) 背景：铺满 + 模糊 + 压暗
    background = Image.fromarray(fit_frame(source, (width, height)))
    if blur > 0:
        background = background.filter(ImageFilter.GaussianBlur(blur))
    if darken > 0:
        background = Image.blend(
            background,
            Image.new("RGB", (width, height), (0, 0, 0)),
            min(1.0, max(0.0, darken)),
        )

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(background, (0, 0))

    # 2) 标题占用的纵向条带（放在卡片上方或下方，不压卡片）
    title_band = 0
    if title:
        title_band = int(title_size * 1.6) + inset_px

    # 3) 卡片区域
    card_x0, card_x1 = inset_px, width - inset_px
    if title_position == "bottom":
        card_y0, card_y1 = inset_px, height - inset_px - title_band
    else:
        card_y0, card_y1 = inset_px + title_band, height - inset_px
    card_w = max(1, card_x1 - card_x0)
    card_h = max(1, card_y1 - card_y0)

    # 前景卡片：覆盖式裁剪到卡片区域 + 圆角
    foreground = Image.fromarray(fit_frame(source, (card_w, card_h))).convert("RGBA")
    card_mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle(
        [0, 0, card_w - 1, card_h - 1], radius=radius, fill=255
    )
    foreground.putalpha(card_mask)

    # 阴影：模糊的黑色圆角块，稍向下偏移
    if shadow > 0:
        shadow_layer = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 190))
        shadow_layer.putalpha(card_mask)
        shadow_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        offset = max(1, shadow // 2)
        shadow_canvas.paste(shadow_layer, (card_x0 + offset, card_y0 + offset), shadow_layer)
        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(shadow))
        canvas = Image.alpha_composite(canvas, shadow_canvas)

    canvas.paste(foreground, (card_x0, card_y0), foreground)

    # 4) 标题
    if title:
        draw = ImageDraw.Draw(canvas)
        font = _fit_title_font(title, width - 2 * inset_px, title_size)
        text_w = draw.textlength(title, font=font)
        text_x = (width - text_w) / 2.0
        band_top = 0 if title_position == "top" else (height - title_band)
        text_y = band_top + (title_band - font.size) / 2.0
        draw.text(
            (text_x, text_y),
            title,
            font=font,
            fill=title_color,
            stroke_width=max(2, title_size // 24),
            stroke_fill=(0, 0, 0, 255),
        )

    return np.asarray(canvas.convert("RGB"), dtype=np.uint8)
