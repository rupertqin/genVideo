"""
subtitle_utils.py 模块的单元测试

覆盖：
- PyAV 字幕解析（load_subtitles）
- 时间戳格式化与 SRT 序列化
- 同名字幕查找与字体查找
- 字幕图渲染（PIL）
- 字幕叠加（moviepy，使用假模块注入避免依赖）
"""
import os
import sys
import types

import numpy as np
import pytest

from genvideo.utils.subtitle_utils import (
    SubtitleCue,
    _ass_tail,
    _rect_to_text,
    _SubtitleOverlay,
    burn_subtitles,
    cues_to_srt,
    filter_cues,
    find_default_font,
    find_subtitle_path,
    format_timestamp,
    load_subtitles,
    normalize_punctuation,
    render_subtitle_frame,
)

SAMPLE_SRT = """1
00:00:00,500 --> 00:00:02,000
第一条字幕

2
00:00:02,000 --> 00:00:03,500
第二条字幕
"""


def _write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestLoadSubtitles:
    """load_subtitles 函数的测试"""

    def test_reads_timing_and_text(self, temp_dir):
        """正确解析起止时间与文本"""
        path = _write(os.path.join(temp_dir, "a.srt"), SAMPLE_SRT)
        cues = load_subtitles(path)

        assert len(cues) == 2
        assert cues[0].text == "第一条字幕"
        assert cues[0].start == pytest.approx(0.5, abs=1e-3)
        assert cues[0].end == pytest.approx(2.0, abs=1e-3)
        assert cues[1].text == "第二条字幕"
        assert cues[1].start == pytest.approx(2.0, abs=1e-3)
        assert cues[1].end == pytest.approx(3.5, abs=1e-3)

    def test_cue_duration(self, temp_dir):
        """duration 属性等于 end - start"""
        path = _write(os.path.join(temp_dir, "a.srt"), SAMPLE_SRT)
        cues = load_subtitles(path)
        assert cues[0].duration == pytest.approx(1.5, abs=1e-3)

    def test_multiline_text_joined(self, temp_dir):
        """多行字幕合并为单行（便于后续折行渲染）"""
        content = "1\n00:00:00,000 --> 00:00:01,000\n第一行\n第二行\n"
        path = _write(os.path.join(temp_dir, "m.srt"), content)
        cues = load_subtitles(path)
        assert len(cues) == 1
        assert cues[0].text == "第一行 第二行"

    def test_sorted_by_start(self, temp_dir):
        """结果按开始时间升序"""
        path = _write(os.path.join(temp_dir, "a.srt"), SAMPLE_SRT)
        cues = load_subtitles(path)
        starts = [cue.start for cue in cues]
        assert starts == sorted(starts)

    def test_missing_file_raises(self):
        """文件不存在时抛 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_subtitles(os.path.join("not", "exist.srt"))

    def test_empty_file_returns_empty(self, temp_dir):
        """空字幕文件返回空列表而不报错"""
        path = os.path.join(temp_dir, "empty.srt")
        open(path, "w").close()
        assert load_subtitles(path) == []


class _StubRect:
    """模拟 PyAV 的 Subtitle rect（只关心取文本的逻辑）"""

    def __init__(self, dialogue=None, ass=None, text=None, dialogue_raises=False):
        self._dialogue = dialogue
        self._ass = ass
        self._text = text
        self._dialogue_raises = dialogue_raises

    @property
    def dialogue(self):
        if self._dialogue_raises:
            # 复现 PyAV 16.x 对非 ASCII 文本的报错
            raise ValueError("byte must be in range(0, 256)")
        return self._dialogue

    @property
    def ass(self):
        return self._ass

    @property
    def text(self):
        return self._text


class TestAssTail:
    """_ass_tail 函数的测试"""

    def test_srt_style_line(self):
        """简洁形态 0,0,Default,,0,0,0,,文本"""
        assert _ass_tail(b"0,0,Default,,0,0,0,,\xe4\xbd\xa0\xe5\xa5\xbd") == "你好".encode()

    def test_full_ass_line(self):
        """完整 ASS 形态（含时间字段）"""
        line = b"0,0:00:00.00,0:00:02.00,Default,,0,0,0,,\xe4\xbd\xa0\xe5\xa5\xbd"
        assert _ass_tail(line) == "你好".encode()

    def test_preserves_commas_in_text(self):
        """正文里的逗号不会被截断"""
        line = "0,0,Default,,0,0,0,,你好，世界，再见".encode()
        assert _ass_tail(line) == "你好，世界，再见".encode()

    def test_empty_returns_none(self):
        """空值返回 None"""
        assert _ass_tail(None) is None
        assert _ass_tail(b"") is None


class TestRectToText:
    """_rect_to_text 函数的测试"""

    def test_prefers_dialogue(self):
        """优先使用 dialogue"""
        rect = _StubRect(dialogue="第一句".encode(), ass="0,0,Default,,0,0,0,,第二句".encode())
        assert _rect_to_text(rect) == "第一句"

    def test_falls_back_to_ass_when_dialogue_raises(self):
        """dialogue 抛错时回退到 ass（PyAV 16.x 兼容）"""
        rect = _StubRect(
            dialogue_raises=True,
            ass=b"0,0,Default,,0,0,0,,\xe7\xac\xac\xe4\xba\x8c\xe5\x8f\xa5",
        )
        assert _rect_to_text(rect) == "第二句"

    def test_falls_back_to_text(self):
        """没有 dialogue/ass 时用 text"""
        assert _rect_to_text(_StubRect(text="第三句".encode())) == "第三句"

    def test_no_content_returns_empty(self):
        """全部为空时返回空字符串"""
        assert _rect_to_text(_StubRect()) == ""

    def test_normalizes_whitespace_and_ass_break(self):
        """ASS 换行符与空白被归一为单个空格"""
        rect = _StubRect(dialogue=b"a\\Nb \xc2\xa0c")
        assert _rect_to_text(rect) == "a b c"


class TestFormatTimestamp:
    """format_timestamp 函数的测试"""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "00:00:00,000"),
            (1.5, "00:00:01,500"),
            (61.25, "00:01:01,250"),
            (3661.234, "01:01:01,234"),
            (-3, "00:00:00,000"),
        ],
    )
    def test_format(self, seconds, expected):
        """按 HH:MM:SS,mmm 格式化，负数归零"""
        assert format_timestamp(seconds) == expected

    def test_custom_separator(self):
        """支持 WebVTT 风格的 '.' 分隔符"""
        assert format_timestamp(1.5, sep=".") == "00:00:01.500"


class TestCuesToSrt:
    """cues_to_srt 函数的测试"""

    def test_round_trip(self, temp_dir):
        """序列化后再解析，内容与时间保持一致"""
        path = _write(os.path.join(temp_dir, "a.srt"), SAMPLE_SRT)
        cues = load_subtitles(path)

        srt_text = cues_to_srt(cues)
        assert srt_text.startswith("1\n00:00:00,500 --> 00:00:02,000\n第一条字幕")

        round_trip = _write(os.path.join(temp_dir, "b.srt"), srt_text)
        reparsed = load_subtitles(round_trip)
        assert [c.text for c in reparsed] == [c.text for c in cues]
        for original, again in zip(cues, reparsed):
            assert again.start == pytest.approx(original.start, abs=1e-3)
            assert again.end == pytest.approx(original.end, abs=1e-3)

    def test_empty_list(self):
        """空列表序列化为空字符串"""
        assert cues_to_srt([]) == ""


class TestFindSubtitlePath:
    """find_subtitle_path 函数的测试"""

    def test_finds_same_name_srt(self, temp_dir):
        """audio.wav -> audio.srt"""
        _write(os.path.join(temp_dir, "audio.srt"), SAMPLE_SRT)
        assert find_subtitle_path(os.path.join(temp_dir, "audio.wav")) == os.path.join(
            temp_dir, "audio.srt"
        )

    def test_returns_none_when_absent(self, temp_dir):
        """无同名字幕时返回 None"""
        assert find_subtitle_path(os.path.join(temp_dir, "audio.wav")) is None

    def test_empty_input(self):
        """空路径返回 None"""
        assert find_subtitle_path("") is None

    def test_prefers_srt(self, temp_dir):
        """同时存在多种格式时优先 srt"""
        _write(os.path.join(temp_dir, "audio.srt"), SAMPLE_SRT)
        _write(os.path.join(temp_dir, "audio.ass"), "[Script Info]")
        assert find_subtitle_path(os.path.join(temp_dir, "audio.wav")).endswith(".srt")


class TestFindDefaultFont:
    """find_default_font 函数的测试"""

    def test_returns_existing_path_or_none(self):
        """返回 None 或一个真实存在的字体文件"""
        font = find_default_font()
        if font is not None:
            assert os.path.exists(font)


class TestRenderSubtitleFrame:
    """render_subtitle_frame 函数的测试"""

    def test_shape_and_dtype(self):
        """输出为 (H, W, 4) 的 uint8 RGBA 数组"""
        frame = render_subtitle_frame("你好世界", (720, 1280))
        assert frame.shape == (1280, 720, 4)
        assert frame.dtype == np.uint8

    def test_text_is_drawn(self):
        """有文本时存在不透明像素"""
        frame = render_subtitle_frame("这是一条字幕", (640, 360))
        assert (frame[..., 3] > 0).sum() > 0

    def test_empty_text_is_transparent(self):
        """空文本返回全透明图"""
        frame = render_subtitle_frame("   ", (320, 240))
        assert (frame[..., 3] > 0).sum() == 0

    def test_long_text_wraps_without_error(self):
        """超长文本自动折行且能画出内容"""
        text = "理解别人的欲望和防御，处理复杂的人际关系，同时保留自己的内部距离" * 2
        frame = render_subtitle_frame(text, (720, 1280))
        assert frame.shape == (1280, 720, 4)
        assert (frame[..., 3] > 0).sum() > 0

    def test_font_size_affects_coverage(self):
        """字号越大，绘制像素越多"""
        text = "字幕大小测试"
        small = render_subtitle_frame(text, (640, 360), font_size=20)
        large = render_subtitle_frame(text, (640, 360), font_size=40)
        assert (large[..., 3] > 0).sum() > (small[..., 3] > 0).sum()

    def test_no_box_color(self):
        """底色 alpha 为 0 时不画底色"""
        frame = render_subtitle_frame("字幕", (640, 360), box_color=(0, 0, 0, 0))
        assert (frame[..., 3] > 0).sum() > 0

    def test_strip_punct_still_renders(self):
        """strip_punct=True 时正常渲染且有内容"""
        frame = render_subtitle_frame("你好，世界。", (640, 360), strip_punct=True)
        assert frame.shape == (360, 640, 4)
        assert (frame[..., 3] > 0).sum() > 0


class TestNormalizePunctuation:
    """normalize_punctuation 函数的测试"""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("你好。", "你好"),                      # 句尾句号删除
            ("你好，", "你好"),                      # 句尾逗号删除
            ("你好，世界", "你好 世界"),             # 句中逗号 -> 空格
            ("你好，世界。", "你好 世界"),           # 句中逗号 + 句尾句号
            ("大家好，我们现在开始。", "大家好 我们现在开始"),
            ("这个公式是什么呢？60比40", "这个公式是什么呢？60比40"),  # 问号保留
            ("你好！", "你好！"),                    # 感叹号保留
            ("a,b.c", "a b c"),                     # 英文逗号句号
            ("好.吧", "好 吧"),
            ("  你好， 世界。 ", "你好 世界"),       # 空白一并归一
            ("", ""),
            ("就到这里", "就到这里"),
        ],
    )
    def test_normalize(self, text, expected):
        """逗号/句号：句尾删除、句中替换为空格；其余标点保留"""
        assert normalize_punctuation(text) == expected

    def test_only_comma_and_period_affected(self):
        """分号/冒号/问号/感叹号一律不动"""
        text = "你好；这个：怎么样？！"
        assert normalize_punctuation(text) == text


class _FakeVideoClip:
    """模拟 moviepy.VideoClip"""

    def __init__(self, frame_function=None, is_mask=False, duration=None, **kwargs):
        self.frame_function = frame_function
        self.is_mask = is_mask
        self.duration = duration
        self.audio = None
        self.size = None

    def with_audio(self, audio):
        self.audio = audio
        return self


class _FakeBaseClip:
    """模拟待叠加字幕的 MoviePy 片段（get_frame 返回同一块缓存，便于验证不被就地改写）"""

    def __init__(self, width=200, height=120, duration=10.0, audio=None):
        self.w = width
        self.h = height
        self.duration = duration
        self.audio = audio
        self.image = np.zeros((height, width, 3), dtype=np.uint8)

    def get_frame(self, t):
        return self.image


@pytest.fixture
def fake_moviepy(monkeypatch):
    """注入假的 moviepy 模块，避免测试依赖真实 MoviePy"""
    module = types.ModuleType("moviepy")
    module.VideoClip = _FakeVideoClip
    monkeypatch.setitem(sys.modules, "moviepy", module)
    return module


class TestFilterCues:
    """filter_cues 函数的测试"""

    def _cues(self):
        return [
            SubtitleCue(0.0, 2.0, "第一句"),
            SubtitleCue(2.0, 4.0, "第二句"),
            SubtitleCue(4.0, 99.0, "跨到片尾"),
            SubtitleCue(100.0, 105.0, "超出时长"),
            SubtitleCue(7.0, 7.0, "零时长"),
        ]

    def test_no_duration_only_drops_zero_length(self):
        """不限制时长时只丢弃零时长字幕"""
        result = filter_cues(self._cues())
        assert [c.text for c in result] == ["第一句", "第二句", "跨到片尾", "超出时长"]

    def test_duration_drops_cues_after_end(self):
        """起点在片尾之后的字幕被丢弃"""
        result = filter_cues(self._cues(), duration=50.0)
        assert [c.text for c in result] == ["第一句", "第二句", "跨到片尾"]

    def test_cue_straddling_end_is_kept(self):
        """起点在片内、结尾超出时长的字幕保留（渲染时会裁剪）"""
        result = filter_cues([SubtitleCue(45.0, 60.0, "跨片尾")], duration=50.0)
        assert len(result) == 1

    def test_cue_at_start_is_kept_even_if_end_exceeds(self):
        """起点在片内就保留（结束时间超出片尾由渲染层裁剪）"""
        assert len(filter_cues([SubtitleCue(0.0, 2.0, "开头")], duration=0.5)) == 1

    def test_all_filtered_out(self):
        """全部超出时长时返回空列表"""
        cues = [SubtitleCue(100.0, 105.0, "晚"), SubtitleCue(200.0, 201.0, "更晚")]
        assert filter_cues(cues, duration=50.0) == []

    def test_empty_input(self):
        """空输入返回空列表"""
        assert filter_cues([]) == []


class TestSubtitleOverlay:
    """_SubtitleOverlay 的按时间定位与缓存"""

    def _overlay(self):
        cues = [SubtitleCue(0.5, 2.0, "第一句"), SubtitleCue(3.0, 5.0, "第二句")]
        return _SubtitleOverlay(cues, (64, 48), {})

    @pytest.mark.parametrize(
        "t,expected",
        [(0.0, None), (0.4, None), (0.5, 0), (1.9, 0), (2.0, None), (3.5, 1), (5.0, None)],
    )
    def test_locate(self, t, expected):
        """按时间正确定位当前字幕（左闭右开）"""
        assert self._overlay().locate(t) == expected

    def test_blank_outside_cues(self):
        """无字幕时返回全透明图层"""
        overlay = self._overlay()
        assert overlay.rgba(0.0).shape == (48, 64, 4)
        assert overlay.rgba(0.0)[..., 3].sum() == 0
        assert overlay.rgba(2.5)[..., 3].sum() == 0

    def test_renders_active_cue(self):
        """命中字幕时图层有不透明像素"""
        overlay = self._overlay()
        assert overlay.rgba(1.0)[..., 3].sum() > 0

    def test_caches_same_cue(self):
        """同一字幕内复用同一张图，跨条后重新渲染"""
        overlay = self._overlay()
        first = overlay.rgba(1.0)
        assert overlay.rgba(1.2) is first
        assert overlay.rgba(3.5) is not first

    def test_frame_at_returns_index(self):
        """frame_at 同时给出当前字幕下标（供包围盒缓存使用）"""
        overlay = self._overlay()
        assert overlay.frame_at(1.0)[1] == 0
        assert overlay.frame_at(3.5)[1] == 1
        assert overlay.frame_at(0.0)[1] is None


class TestBurnSubtitles:
    """burn_subtitles 函数的测试"""

    def test_no_cues_returns_original(self, fake_moviepy):
        """无字幕时原样返回"""
        clip = _FakeBaseClip()
        assert burn_subtitles(clip, []) is clip

    def test_cues_outside_duration_skipped(self, fake_moviepy):
        """完全落在片尾之后的字幕被丢弃"""
        clip = _FakeBaseClip()
        assert burn_subtitles(clip, [SubtitleCue(20.0, 25.0, "太靠后")]) is clip

    def test_zero_length_cue_skipped(self, fake_moviepy):
        """零时长字幕被忽略"""
        clip = _FakeBaseClip()
        assert burn_subtitles(clip, [SubtitleCue(1.0, 1.0, "空")]) is clip

    def test_returns_video_clip_with_duration(self, fake_moviepy):
        """返回带 frame_function 与时长的新片段"""
        result = burn_subtitles(_FakeBaseClip(), [SubtitleCue(0.0, 2.0, "第一句")])
        assert isinstance(result, _FakeVideoClip)
        assert result.duration == pytest.approx(10.0)
        assert callable(result.frame_function)

    def test_audio_preserved(self, fake_moviepy):
        """原片段音频被保留（否则成片会静音）"""
        audio = object()
        clip = _FakeBaseClip(audio=audio)
        assert burn_subtitles(clip, [SubtitleCue(0.0, 2.0, "字幕")]).audio is audio

    def test_no_audio_when_source_has_none(self, fake_moviepy):
        """原片段无音频时不额外添加"""
        assert burn_subtitles(_FakeBaseClip(), [SubtitleCue(0.0, 2.0, "字幕")]).audio is None

    def test_frame_untouched_outside_cues(self, fake_moviepy):
        """无字幕时刻返回原始帧（内容与形状都不变）"""
        clip = _FakeBaseClip()
        result = burn_subtitles(clip, [SubtitleCue(1.0, 2.0, "字幕")])
        frame = result.frame_function(0.0)
        assert frame.shape == (120, 200, 3)
        assert frame.sum() == 0
        assert frame is clip.image  # 零开销路径：直接复用原帧

    def test_frame_blended_inside_cue(self, fake_moviepy):
        """字幕时间内把白字混入帧"""
        clip = _FakeBaseClip()
        result = burn_subtitles(clip, [SubtitleCue(1.0, 2.0, "字幕")])
        frame = result.frame_function(1.5)
        assert frame.shape == (120, 200, 3)
        assert frame.dtype == np.uint8
        assert frame.sum() > 0

    def test_source_frame_not_mutated(self, fake_moviepy):
        """混合时不就地改写源帧（ImageClip 会复用同一块内存）"""
        clip = _FakeBaseClip()
        result = burn_subtitles(clip, [SubtitleCue(1.0, 2.0, "字幕")])
        blended = result.frame_function(1.5)
        assert blended is not clip.image
        assert clip.image.sum() == 0

    def test_render_kwargs_passthrough(self, fake_moviepy):
        """渲染参数透传到渲染函数（字号影响绘制结果）"""
        cues = [SubtitleCue(1.0, 2.0, "字幕")]
        small = burn_subtitles(_FakeBaseClip(width=320, height=240), cues, font_size=10)
        large = burn_subtitles(_FakeBaseClip(width=320, height=240), cues, font_size=30)
        assert (
            large.frame_function(1.5).sum() > small.frame_function(1.5).sum()
        )
