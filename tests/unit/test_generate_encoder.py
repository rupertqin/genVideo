"""
generate.py 编码器选择相关逻辑的单元测试

覆盖：
- detect_hardware_encoder：探测 ffmpeg 是否带硬件 H.264 编码器
- _build_write_kwargs：write_videofile 参数组装（preset 只给软件 x264）
"""
import subprocess
import sys
import types

import pytest

import imageio_ffmpeg

from generate import (
    DEFAULT_PRESET,
    HARDWARE_ENCODERS,
    _build_write_kwargs,
    detect_hardware_encoder,
)


def _fake_run(stdout):
    """构造一个假的 subprocess.run，只关心 stdout"""
    def run(*args, **kwargs):
        return types.SimpleNamespace(stdout=stdout, returncode=0)
    return run


@pytest.fixture
def fake_ffmpeg(monkeypatch):
    """指向一个假 ffmpeg 可执行文件，避免真的启动子进程"""
    monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe", lambda: "/fake/ffmpeg")


class TestDetectHardwareEncoder:
    """detect_hardware_encoder 函数的测试"""

    def test_detects_available_hardware(self, fake_ffmpeg, monkeypatch):
        """识别出可用的硬件编码器"""
        monkeypatch.setattr(
            subprocess, "run", _fake_run(" V..... h264_videotoolbox  H.264 (VideoToolbox)")
        )
        assert detect_hardware_encoder() == "h264_videotoolbox"

    def test_returns_none_when_only_software(self, fake_ffmpeg, monkeypatch):
        """只有软件编码器时返回 None"""
        monkeypatch.setattr(subprocess, "run", _fake_run(" V....D libx264  H.264 / AVC"))
        assert detect_hardware_encoder() is None

    def test_priority_order(self, fake_ffmpeg, monkeypatch):
        """多个硬件编码器时按候选顺序取第一个"""
        monkeypatch.setattr(
            subprocess, "run", _fake_run(" h264_amf  h264_nvenc  h264_videotoolbox ")
        )
        assert detect_hardware_encoder() == HARDWARE_ENCODERS[0]

    def test_returns_none_when_ffmpeg_missing(self, monkeypatch):
        """取不到 ffmpeg 可执行文件时安全返回 None"""
        def boom():
            raise RuntimeError("ffmpeg not found")

        monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe", boom)
        assert detect_hardware_encoder() is None

    def test_returns_none_when_imageio_ffmpeg_unavailable(self, monkeypatch):
        """imageio_ffmpeg 不可导入时安全返回 None"""
        monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
        assert detect_hardware_encoder() is None

    def test_returns_none_when_ffmpeg_fails(self, fake_ffmpeg, monkeypatch):
        """ffmpeg 执行失败时安全返回 None"""
        def boom(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "ffmpeg")

        monkeypatch.setattr(subprocess, "run", boom)
        assert detect_hardware_encoder() is None


class TestBuildWriteKwargs:
    """_build_write_kwargs 函数的测试"""

    def test_software_encoder_keeps_preset(self):
        """libx264 带上 preset"""
        kwargs = _build_write_kwargs(24, "libx264", "veryfast", "5000k")
        assert kwargs["preset"] == "veryfast"
        assert kwargs["codec"] == "libx264"
        assert kwargs["fps"] == 24
        assert kwargs["bitrate"] == "5000k"
        assert kwargs["audio_codec"] == "aac"

    def test_hardware_encoder_omits_preset(self):
        """硬件编码器不传 preset（传 None 会触发 MoviePy 的 TypeError）"""
        kwargs = _build_write_kwargs(24, "h264_videotoolbox", "veryfast", "8000k")
        assert "preset" not in kwargs
        assert kwargs["codec"] == "h264_videotoolbox"
        assert kwargs["bitrate"] == "8000k"

    def test_none_preset_omitted(self):
        """preset 为 None 时不写入该键"""
        assert "preset" not in _build_write_kwargs(24, "libx264", None, "5000k")

    def test_default_preset_value(self):
        """默认 preset 为 veryfast"""
        assert DEFAULT_PRESET == "veryfast"
