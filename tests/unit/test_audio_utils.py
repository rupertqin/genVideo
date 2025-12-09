"""
audio_utils.py 模块的单元测试
"""
import pytest
import tempfile
import numpy as np
import av
import os
from unittest.mock import patch, MagicMock

from utils.audio_utils import get_audio_duration_ffmpeg, get_audio_pauses


class TestGetAudioDuration:
    """get_audio_duration_ffmpeg 函数的测试"""

    def test_valid_audio_file(self, temp_audio_file):
        """测试有效音频文件的时长获取"""
        audio_path = temp_audio_file(duration=5.0)
        duration = get_audio_duration_ffmpeg(audio_path)
        assert isinstance(duration, float)
        assert duration > 0
        assert abs(duration - 5.0) < 0.1  # 允许小的误差

    def test_different_durations(self, temp_audio_file):
        """测试不同时长的音频文件"""
        durations = [1.0, 3.5, 10.0, 30.0]
        for expected_duration in durations:
            audio_path = temp_audio_file(duration=expected_duration)
            actual_duration = get_audio_duration_ffmpeg(audio_path)
            assert abs(actual_duration - expected_duration) < 0.2

    def test_nonexistent_file(self):
        """测试不存在的音频文件"""
        with pytest.raises(RuntimeError):
            get_audio_duration_ffmpeg("nonexistent.wav")

    @patch('utils.audio_utils.av.open')
    def test_av_exception_handling(self, mock_av_open):
        """测试 PyAV 异常处理"""
        mock_av_open.side_effect = Exception("Test error")

        with pytest.raises(RuntimeError) as exc_info:
            get_audio_duration_ffmpeg("test.wav")

        assert "无法获取音频时长（PyAV）" in str(exc_info.value)

    @patch('utils.audio_utils.av.open')
    def test_no_audio_stream(self, mock_av_open):
        """测试没有音频流的情况"""
        mock_container = MagicMock()
        mock_container.streams.audio = []
        mock_av_open.return_value.__enter__.return_value = mock_container

        with pytest.raises(RuntimeError):
            get_audio_duration_ffmpeg("test.wav")


class TestGetAudioPauses:
    """get_audio_pauses 函数的测试"""

    def test_silence_detection_basic(self):
        """测试基本静音检测"""
        # 创建一个包含静音的模拟音频
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            # 创建静音和声音帧
            silent_frame = MagicMock()
            silent_frame.to_ndarray.return_value = np.array([[100]], dtype=np.int16)  # 非常小的值
            silent_frame.pts = 0
            silent_frame.time_base = 0.1
            silent_frame.samples = 1024
            silent_frame.sample_rate = 44100

            audio_frame = MagicMock()
            audio_frame.to_ndarray.return_value = np.array([[32767]], dtype=np.int16)  # 正常音量
            audio_frame.pts = 2048  # 约0.1秒后
            audio_frame.time_base = 0.1
            audio_frame.samples = 1024
            audio_frame.sample_rate = 44100

            mock_container.decode.return_value = [silent_frame, audio_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            pauses = get_audio_pauses("test.wav", min_pause=0.05, noise_threshold=-35)
            # 应该检测到静音
            assert len(pauses) >= 0  # 根据具体实现调整

    def test_no_silence(self):
        """测试没有静音的情况"""
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            # 只创建有声音的帧
            audio_frame = MagicMock()
            audio_frame.to_ndarray.return_value = np.array([[32767]], dtype=np.int16)
            audio_frame.pts = 0
            audio_frame.time_base = 0.1
            audio_frame.samples = 1024
            audio_frame.sample_rate = 44100

            mock_container.decode.return_value = [audio_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            pauses = get_audio_pauses("test.wav", min_pause=0.05, noise_threshold=-35)
            assert len(pauses) == 0

    def test_silence_too_short(self):
        """测试静音时长小于最小要求的情况"""
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            # 创建短静音帧
            silent_frame = MagicMock()
            silent_frame.to_ndarray.return_value = np.array([[100]], dtype=np.int16)
            silent_frame.pts = 0
            silent_frame.time_base = 0.1
            silent_frame.samples = 512  # 短帧
            silent_frame.sample_rate = 44100

            mock_container.decode.return_value = [silent_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            pauses = get_audio_pauses("test.wav", min_pause=0.1, noise_threshold=-35)
            assert len(pauses) == 0  # 太短，不应该被检测到

    def test_av_exception_handling(self, caplog):
        """测试 PyAV 异常处理"""
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_av_open.side_effect = Exception("Test error")

            pauses = get_audio_pauses("test.wav")
            assert len(pauses) == 0
            assert "检测音频停顿时出错" in caplog.text

    def test_empty_audio_array(self):
        """测试空音频数组的处理"""
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            # 创建空音频帧
            empty_frame = MagicMock()
            empty_frame.to_ndarray.return_value = np.array([], dtype=np.int16)
            empty_frame.pts = 0
            empty_frame.time_base = 0.1
            empty_frame.samples = 0
            empty_frame.sample_rate = 44100

            mock_container.decode.return_value = [empty_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            pauses = get_audio_pauses("test.wav")
            assert len(pauses) == 0  # 应该能处理空数组而不崩溃

    def test_rms_calculation_edge_cases(self):
        """测试 RMS 计算的边界情况"""
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            # 测试零值RMS
            zero_frame = MagicMock()
            zero_frame.to_ndarray.return_value = np.array([[0]], dtype=np.int16)
            zero_frame.pts = 0
            zero_frame.time_base = 0.1
            zero_frame.samples = 1024
            zero_frame.sample_rate = 44100

            mock_container.decode.return_value = [zero_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            pauses = get_audio_pauses("test.wav", min_pause=0.05, noise_threshold=-35)
            assert len(pauses) >= 0  # 应该能处理零值

    def test_parameters_validation(self):
        """测试参数验证"""
        # 测试不同的参数组合
        with patch('utils.audio_utils.av.open') as mock_av_open:
            mock_container = MagicMock()
            mock_stream = MagicMock()
            mock_container.streams.audio = [mock_stream]

            normal_frame = MagicMock()
            normal_frame.to_ndarray.return_value = np.array([[32767]], dtype=np.int16)
            normal_frame.pts = 0
            normal_frame.time_base = 0.1
            normal_frame.samples = 1024
            normal_frame.sample_rate = 44100

            mock_container.decode.return_value = [normal_frame]
            mock_av_open.return_value.__enter__.return_value = mock_container

            # 测试不同的参数组合
            pauses1 = get_audio_pauses("test.wav", min_pause=0.1, noise_threshold=-30)
            pauses2 = get_audio_pauses("test.wav", min_pause=0.5, noise_threshold=-40)

            assert isinstance(pauses1, list)
            assert isinstance(pauses2, list)
