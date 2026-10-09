"""
视觉布局组件模块（可插拔的画面层）

每个布局是一个函数：给定源图、画布尺寸、时长、选项，返回一个
``frame(t) -> ndarray`` 的帧函数（通常对静态画面预计算一次，逐帧复用）。

已注册布局：
    fullscreen  — 全屏铺满 + 居中裁剪（默认）
    card        — 背景模糊压暗铺满 + 前景留边卡片（不铺满）+ 标题
    hero        — 顶部全幅主视觉照片 + 下沿渐隐到纸色 + 网格纹理 +
                  超大背景标题 + 四角标记（杂志封面风，非卡片）

新布局用 ``@register_layout("名字")`` 注册即可，随后在 config.yaml 里
``video.layout`` 切换。
"""
from __future__ import annotations

import os
from typing import Callable, Dict, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from genvideo.config import parse_color
from genvideo.utils.subtitle_utils import find_default_font
from genvideo.utils.video_utils import fit_frame

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


# 衬线（宋体）字体候选：hero 布局的大背景标题需要宋体字感，先于默认黑体查找
_SERIF_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttf",
    "/System/Library/Fonts/STSong.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simsun.ttf",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
)


def _load_truetype(path, size):
    """按路径加载字体，失败回退 PIL 默认字体"""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _find_serif_font():
    """找一个可用的衬线（宋体）中文字体；找不到退回默认黑体"""
    for path in _SERIF_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return find_default_font()


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


# ==============================================================
# hero 布局：杂志封面风（对齐参考页面 index.html 的视觉结构）
# ==============================================================

# 照片下沿渐隐的落点（与 .bg-hero::after 的渐变停靠点一致）：
# 顶部到 46% 完全透明，64% 处 0.40，82% 处 0.84，底部完全纸色
_HERO_FADE_STOPS = ((0.0, 0.0), (0.46, 0.0), (0.64, 0.40), (0.82, 0.84), (1.0, 1.0))


def _fade_alpha_at(t):
    """按参考渐隐曲线取某个纵向位置 (0~1) 的纸色混合系数"""
    stops = _HERO_FADE_STOPS
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for (t0, a0), (t1, a1) in zip(stops, stops[1:]):
        if t0 <= t <= t1:
            return a0 + (a1 - a0) * (t - t0) / (t1 - t0)
    return 1.0


def _apply_fade(hero, bg_rgb, axis="vertical"):
    """
    给 hero 照片（RGB PIL 图）沿一条边加渐隐，溶进纸色背景。

    axis:
        "vertical"   — 从顶部（透明）到底部（纸色）纵向渐隐（竖屏照片带）
        "horizontal" — 从左（透明）到右（纸色）横向渐隐（横屏照片带）
    """
    arr = np.asarray(hero, dtype=np.uint8).astype(np.float32)
    n = arr.shape[0] if axis == "vertical" else arr.shape[1]
    if n <= 1:
        return hero
    ts = np.linspace(0.0, 1.0, n)
    alphas = np.array([_fade_alpha_at(t) for t in ts], dtype=np.float32)
    bg = np.asarray(bg_rgb, dtype=np.float32)
    if axis == "vertical":
        arr = arr * (1.0 - alphas[:, None, None]) + bg[None, None, :] * alphas[:, None, None]
    else:
        arr = arr * (1.0 - alphas[None, :, None]) + bg[None, None, :] * alphas[None, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _draw_grid(odraw, width, height, options):
    """在透明图层上画 1px 网格纹理"""
    grid_size = options.get("grid_size")
    if not grid_size:
        grid_size = max(16, int(round(width / 13.5)))
    grid_size = int(grid_size)
    grid_rgb = parse_color(options.get("grid_color", "#1E2528"), 255) or (30, 37, 40, 255)
    alpha = int(round(255 * float(options.get("grid_alpha", 0.05))))
    color = tuple(grid_rgb[:3]) + (max(0, min(255, alpha)),)
    for x in range(0, width, grid_size):
        odraw.line([(x, 0), (x, height)], fill=color, width=1)
    for y in range(0, height, grid_size):
        odraw.line([(0, y), (width, y)], fill=color, width=1)


def _draw_bg_title(odraw, width, height, title, options, landscape, photo_edge):
    """
    画超大背景标题，超宽自动缩字号。

    竖屏：水平居中于全画幅、贴着照片区底边（photo_edge 为照片区底边 y）。
    横屏：垂直居中、水平居中于照片区右侧的纸色区（photo_edge 为照片区右边界 x）。
    """
    title_color = parse_color(options.get("title_color", "#1E252861"), 255) or (30, 37, 40, 97)

    base = options.get("title_size")
    if not base:
        base = max(16, int(round(height * (340 / 1920))))
    base = int(base)

    font_path = options.get("title_font") or _find_serif_font()
    font = _load_truetype(font_path, base)
    title_max_width = float(options.get("title_max_width", 0.8))

    if landscape:
        # 右侧纸色区：宽 = 画布宽 - 照片区右边界
        content_w = max(1, width - int(photo_edge))
        max_w = content_w * title_max_width
        size = base
        while size > 12 and font.getlength(title) > max_w:
            size -= 2
            font = _load_truetype(font_path, size)
        text_w = font.getlength(title)
        x = photo_edge + (content_w - text_w) / 2.0
        y = (height - font.size) / 2.0
    else:
        max_w = width * title_max_width
        size = base
        while size > 12 and font.getlength(title) > max_w:
            size -= 2
            font = _load_truetype(font_path, size)
        offset = int(round(height * (122 / 1920)))
        top = int(photo_edge) - offset
        text_w = font.getlength(title)
        x = (width - text_w) / 2.0
        y = top

    odraw.text((x, y), title, font=font, fill=title_color)


def _draw_corner_marks(odraw, width, height, options):
    """画四角绿色标记（左上 + 右下两个 L 形角标）"""
    accent = parse_color(options.get("accent", "#5E8C7A"), 255) or (94, 140, 122, 255)
    alpha = int(round(255 * 0.45))
    color = tuple(accent[:3]) + (alpha,)
    inset = int(round(width * (40 / 1080)))
    length = int(round(width * (24 / 1080)))
    lw = max(2, int(round(width * (2 / 1080))))

    # 左上角
    odraw.line([(inset, inset), (inset + length, inset)], fill=color, width=lw)
    odraw.line([(inset, inset), (inset, inset + length)], fill=color, width=lw)
    # 右下角
    odraw.line(
        [(width - inset - length, height - inset), (width - inset, height - inset)],
        fill=color, width=lw,
    )
    odraw.line(
        [(width - inset, height - inset - length), (width - inset, height - inset)],
        fill=color, width=lw,
    )


@register_layout("hero")
def hero_layout(source, video_size, duration, options=None):
    """
    杂志封面风：满幅主视觉照片 + 渐隐到纸色 + 网格纹理 + 超大背景标题 + 四角标记。

    与 ``card`` 的关键区别：照片不放进圆角卡片（无留边、无圆角、无阴影），
    而是满幅通栏铺开，沿一条边渐隐溶进纸色背景。

    自动适配横竖屏：
        竖屏（height >= width）：顶部通栏照片带，下沿渐隐，标题贴照片底边；
        横屏（width > height）：左侧通栏照片带，右沿渐隐，标题在右侧纸色区。

    options:
        bg_color (str): 纸色背景（默认 "#EDF2F4"）
        hero_top (float): 竖屏照片区顶边，占画布高度比例（默认 0.0）
        hero_h (float): 竖屏照片区高度，占画布高度比例（默认 0.60）
        hero_w (float): 横屏照片区宽度，占画布宽度比例（默认 0.60）
        hero_position (str): 照片裁剪位置（竖屏默认 "top"，横屏默认 "left"）
        fade (bool): 是否给照片下沿/右沿加渐隐（默认 True）
        grid (bool): 是否叠加网格纹理（默认 True）
        grid_size (int): 网格单元格边长（像素，None 时按宽度自适应）
        grid_color / grid_alpha: 网格线颜色与透明度
        marks (bool): 是否画四角标记（默认 True）
        accent (str): 角标颜色（默认 "#5E8C7A"）
        title (str): 大背景标题（None 表示不显示）
        title_size (int): 基准字号（None 时按高度自适应，1080x1920 下 ≈340）
        title_color (str): 标题颜色（默认半透明冷墨 "#1E252861"）
        title_font (str): 标题字体路径（None 时自动找宋体）
        title_max_width (float): 标题最大宽度占（照片区外的）纸色区比例，超出自动缩字号
    """
    options = options or {}
    frame = _render_hero_frame(source, video_size, options)
    return lambda t: frame


def _render_hero_frame(source, video_size, options) -> np.ndarray:
    """渲染一张静态 hero 帧（纸底 + 满幅照片 + 渐隐 + 网格 + 标题 + 角标）"""
    width, height = int(video_size[0]), int(video_size[1])

    bg = parse_color(options.get("bg_color", "#EDF2F4"), 255) or (237, 242, 244, 255)
    bg_rgb = bg[:3]

    # 1) 纸色画布
    canvas = Image.new("RGB", (width, height), bg_rgb)

    # 2) 满幅照片（hero）：按横竖屏选择照片带方向
    landscape = width > height
    if landscape:
        # 横屏：左侧垂直通栏，右沿渐隐
        hero_w = float(options.get("hero_w", 0.60))
        hero_left_px = 0
        hero_w_px = max(1, int(round(width * hero_w)))
        hero_w_px = min(hero_w_px, width)
        hero_position = options.get("hero_position") or "left"
        hero = Image.fromarray(fit_frame(source, (hero_w_px, height), position=hero_position))
        if options.get("fade", True):
            hero = _apply_fade(hero, bg_rgb, axis="horizontal")
        canvas.paste(hero, (hero_left_px, 0))
        photo_edge = hero_left_px + hero_w_px  # 照片区右边界
    else:
        # 竖屏：顶部水平通栏，下沿渐隐
        hero_top = float(options.get("hero_top", 0.0))
        hero_h = float(options.get("hero_h", 0.60))
        hero_top_px = int(round(height * hero_top))
        hero_h_px = max(1, int(round(height * hero_h)))
        hero_h_px = min(hero_h_px, height - hero_top_px)
        hero_position = options.get("hero_position") or "top"
        if hero_h_px > 0:
            hero = Image.fromarray(fit_frame(source, (width, hero_h_px), position=hero_position))
            if options.get("fade", True):
                hero = _apply_fade(hero, bg_rgb, axis="vertical")
            canvas.paste(hero, (0, hero_top_px))
        photo_edge = hero_top_px + hero_h_px  # 照片区底边

    # 3) 半透明覆盖层：网格 + 大标题 + 四角标记（都压在照片与纸色之上）
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    if options.get("grid", True):
        _draw_grid(odraw, width, height, options)
    title = str(options.get("title") or "").strip()
    if title:
        _draw_bg_title(odraw, width, height, title, options, landscape, photo_edge)
    if options.get("marks", True):
        _draw_corner_marks(odraw, width, height, options)

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    return np.asarray(canvas, dtype=np.uint8)


def _fade_mask(w, h, axis="vertical"):
    """
    生成渐隐 alpha mask（L 灰度图），给 ffmpeg 后端的图片加透明度。

    灰度值 = 图片保留度 = 1 - 纸色混合系数。竖屏顶部 255（不透明）到底部 0（透明）；
    横屏从左 255 到右 0。
    """
    n = h if axis == "vertical" else w
    ts = np.linspace(0.0, 1.0, n)
    alphas = np.array([1.0 - _fade_alpha_at(t) for t in ts], dtype=np.float32)
    arr = np.round(np.clip(alphas, 0, 1) * 255).astype(np.uint8)
    if axis == "vertical":
        arr = np.tile(arr[:, None], (1, w))
    else:
        arr = np.tile(arr[None, :], (h, 1))
    return Image.fromarray(arr, mode="L")


def _hero_static_assets(video_size, options):
    """
    渲染 hero 布局的静态资源，供 ffmpeg 后端合成用（与 frame 后端画面一致）。

    返回:
        dict:
            background (PIL.Image): 纸色背景 + 网格 + 大标题 + 四角标记（不含图片）
            mask (PIL.Image or None): 渐隐 alpha mask（fade=False 时为 None）
            hero_rect (tuple): 图片应 overlay 到的区域 (x, y, w, h)
            landscape (bool): 是否横屏
    """
    width, height = int(video_size[0]), int(video_size[1])
    bg = parse_color(options.get("bg_color", "#EDF2F4"), 255) or (237, 242, 244, 255)
    bg_rgb = bg[:3]
    landscape = width > height

    if landscape:
        hero_w = float(options.get("hero_w", 0.60))
        hero_w_px = max(1, int(round(width * hero_w)))
        hero_w_px = min(hero_w_px, width)
        hero_rect = (0, 0, hero_w_px, height)
        photo_edge = hero_w_px
        mask = _fade_mask(hero_w_px, height, axis="horizontal") if options.get("fade", True) else None
    else:
        hero_top = float(options.get("hero_top", 0.0))
        hero_h = float(options.get("hero_h", 0.60))
        hero_top_px = int(round(height * hero_top))
        hero_h_px = max(1, int(round(height * hero_h)))
        hero_h_px = min(hero_h_px, height - hero_top_px)
        hero_rect = (0, hero_top_px, width, hero_h_px)
        photo_edge = hero_top_px + hero_h_px
        mask = _fade_mask(width, hero_h_px, axis="vertical") if hero_h_px > 0 and options.get("fade", True) else None

    # 静态背景：纸色 + 网格 + 大标题 + 四角标记（都压在图片之上的元素）
    background = Image.new("RGB", (width, height), bg_rgb)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    if options.get("grid", True):
        _draw_grid(odraw, width, height, options)
    title = str(options.get("title") or "").strip()
    if title:
        _draw_bg_title(odraw, width, height, title, options, landscape, photo_edge)
    if options.get("marks", True):
        _draw_corner_marks(odraw, width, height, options)
    background = Image.alpha_composite(background.convert("RGBA"), overlay).convert("RGB")

    return {"background": background, "mask": mask, "hero_rect": hero_rect, "landscape": landscape}


def render_layout_static(layout_name, video_size, options):
    """
    渲染指定布局的静态资源（背景图 + 渐隐 mask + 图片区域），供 ffmpeg 后端合成。

    这是「布局 UI 组件」与「渲染后端」解耦的接口：ffmpeg 后端复用这里产出的
    静态元素，保证与 frame 后端画面一致。

    返回:
        dict or None:
            hero/fullscreen 返回静态资源 dict；card 暂不支持 ffmpeg 后端，返回 None。
    """
    options = options or {}
    if layout_name == "hero":
        return _hero_static_assets(video_size, options)
    if layout_name == "fullscreen":
        # 图片 cover 铺满全屏，无背景无 mask
        return {
            "background": None,
            "mask": None,
            "hero_rect": (0, 0, int(video_size[0]), int(video_size[1])),
            "landscape": int(video_size[0]) > int(video_size[1]),
        }
    return None
