"""
render 包（编码器 / 进度计时 / ffmpeg 滤镜链后端）的单元测试
"""
import pytest

from genvideo.render import encoder as encoder_mod
from genvideo.render import ffmpeg as ffmpeg_mod
from genvideo.render import progress as progress_mod


# ---------------------------------------------------------------------------
# encoder
# ---------------------------------------------------------------------------

class TestResolveEncoder:
    def test_explicit_encoder_passthrough(self):
        assert encoder_mod.resolve_encoder("libx264") == "libx264"
        assert encoder_mod.resolve_encoder("h264_nvenc") == "h264_nvenc"

    def test_auto_with_hardware(self, monkeypatch):
        monkeypatch.setattr(encoder_mod, "detect_hardware_encoder", lambda: "h264_videotoolbox")
        assert encoder_mod.resolve_encoder("auto") == "h264_videotoolbox"

    def test_auto_fallback_to_libx264(self, monkeypatch):
        monkeypatch.setattr(encoder_mod, "detect_hardware_encoder", lambda: None)
        assert encoder_mod.resolve_encoder("auto") == "libx264"


class TestBuildWriteKwargs:
    def test_software_keeps_preset(self):
        kwargs = encoder_mod.build_write_kwargs(24, "libx264", "veryfast", "5000k")
        assert kwargs["preset"] == "veryfast"
        assert kwargs["codec"] == "libx264"

    def test_hardware_omits_preset(self):
        kwargs = encoder_mod.build_write_kwargs(24, "h264_videotoolbox", "veryfast", "8000k")
        assert "preset" not in kwargs


class TestBuildFfmpegEncodeArgs:
    def test_libx264(self):
        args = encoder_mod.build_ffmpeg_encode_args("libx264", "veryfast", "5000k")
        assert args == ["-c:v", "libx264", "-preset", "veryfast", "-b:v", "5000k"]

    def test_videotoolbox(self):
        args = encoder_mod.build_ffmpeg_encode_args("h264_videotoolbox", None, "12000k")
        assert args[0:2] == ["-c:v", "h264_videotoolbox"]
        assert "-b:v" in args and "12000k" in args
        assert "-allow_sw" in args


# ---------------------------------------------------------------------------
# progress
# ---------------------------------------------------------------------------

class TestFpsMeter:
    def test_elapsed_and_fps(self, monkeypatch):
        times = iter([100.0, 105.0])
        monkeypatch.setattr(progress_mod.time, "time", lambda: next(times))
        meter = progress_mod.FpsMeter()
        meter.start()
        meter.stop(frames=100)
        assert meter.elapsed == pytest.approx(5.0)
        assert meter.fps == pytest.approx(20.0)

    def test_no_frames_fps_none(self):
        meter = progress_mod.FpsMeter()
        meter.start()
        meter.stop()
        assert meter.fps is None


class TestParseFfmpegProgress:
    def test_parse_kv(self):
        state = {}
        progress_mod.parse_ffmpeg_progress("frame=100", state)
        progress_mod.parse_ffmpeg_progress("fps=42.5", state)
        progress_mod.parse_ffmpeg_progress("out_time=00:00:03.50", state)
        assert state["frame"] == "100"
        assert state["fps"] == "42.5"
        assert state["out_time"] == "00:00:03.50"

    def test_ignore_noise(self):
        state = {}
        progress_mod.parse_ffmpeg_progress("", state)
        progress_mod.parse_ffmpeg_progress("garbage", state)
        assert state == {}


# ---------------------------------------------------------------------------
# ffmpeg 滤镜链后端
# ---------------------------------------------------------------------------

class TestSegmentDurations:
    def test_basic(self):
        assert ffmpeg_mod._segment_durations([0.0, 3.0, 5.0, 9.0]) == [3.0, 2.0, 4.0]


class TestClampTransition:
    def test_within_range(self):
        assert ffmpeg_mod._clamp_transition(1.0, [3.0, 5.0, 4.0]) == 1.0

    def test_clamped_to_shortest(self):
        # 最短段 3.0，1.0 过渡 < 3.0，不 clamp
        assert ffmpeg_mod._clamp_transition(2.9, [3.0, 5.0]) == pytest.approx(2.9)
        # 过渡超过最短段，clamp 到最短段 - 0.01
        assert ffmpeg_mod._clamp_transition(5.0, [3.0, 5.0]) == pytest.approx(2.99)

    def test_zero_or_single_segment(self):
        assert ffmpeg_mod._clamp_transition(1.0, [3.0]) == 0.0
        assert ffmpeg_mod._clamp_transition(0.0, [3.0, 5.0]) == 0.0


class TestBuildFilterComplex:
    @staticmethod
    def _fullscreen():
        # 无背景无 mask：图片 cover 铺满
        return dict(img_base=0, mask_idx=None, has_bg=False, has_mask=False, hero_rect=(0, 0, 1920, 1080))

    @staticmethod
    def _hero_fade():
        # 有背景有 mask：图片 cover + alphamerge + overlay
        return dict(img_base=3, mask_idx=6, has_bg=True, has_mask=True, hero_rect=(0, 0, 1152, 1080))

    def test_fullscreen_cover(self):
        fc = ffmpeg_mod._build_filter_complex([3.0], [1920, 1080], 0.0, [], 0, **self._fullscreen())
        assert "scale=1920:1080" in fc
        assert "null[vout]" in fc
        assert "overlay" not in fc and "alphamerge" not in fc

    def test_hero_fade_alphamerge_overlay(self):
        fc = ffmpeg_mod._build_filter_complex([3.0], [1920, 1080], 0.0, [], 0, **self._hero_fade())
        assert "scale=1152:1080" in fc
        assert "alphamerge" in fc
        assert "overlay=0:0" in fc

    def test_hero_no_fade_no_alphamerge(self):
        opts = self._hero_fade()
        opts["has_mask"] = False
        opts["mask_idx"] = None
        fc = ffmpeg_mod._build_filter_complex([3.0], [1920, 1080], 0.0, [], 0, **opts)
        assert "alphamerge" not in fc
        assert "overlay=0:0" in fc

    def test_multi_segment_concat_no_transition(self):
        fc = ffmpeg_mod._build_filter_complex([2.0, 3.0], [1280, 720], 0.0, [], 0, **self._fullscreen())
        assert "concat=n=2:v=1:a=0" in fc
        assert "xfade" not in fc

    def test_multi_segment_xfade(self):
        # durations=[3,5,4], trans=1 -> offsets: xfade1=3, xfade2=8
        fc = ffmpeg_mod._build_filter_complex([3.0, 5.0, 4.0], [1280, 720], 1.0, [], 0, **self._fullscreen())
        assert "xfade=transition=fade:duration=1.0000:offset=3.0000" in fc
        assert "xfade=transition=fade:duration=1.0000:offset=8.0000" in fc

    def test_subtitle_overlay_enable(self):
        # 两条字幕：sub_base=1，通过 overlay + x/y 定位 + enable 时间窗叠加
        subs = [
            {"start": 0.5, "end": 1.5, "x": 100, "y": 200},
            {"start": 2.0, "end": 3.0, "x": 120, "y": 220},
        ]
        fc = ffmpeg_mod._build_filter_complex([3.0], [1280, 720], 0.0, subs, 1, **self._fullscreen())
        assert "overlay=100:200:enable='between(t,0.5000,1.5000)'" in fc
        assert "overlay=120:220:enable='between(t,2.0000,3.0000)'" in fc
        assert "[1:v]overlay" in fc and "[2:v]overlay" in fc
