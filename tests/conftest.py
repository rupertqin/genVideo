"""
Pytest 配置文件
包含测试夹具和通用设置
"""
import pytest
import os
import tempfile
import numpy as np
from PIL import Image
import av
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_audio_file():
    """创建临时音频文件"""
    def _create_temp_audio(duration=5.0, sample_rate=44100):
        """创建临时音频文件"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            # 创建简单的正弦波音频
            frames = int(duration * sample_rate)
            t = np.linspace(0, duration, frames)
            frequency = 440  # A4音符
            audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)

            # 转换为16位整数
            audio_data_int = (audio_data * 32767).astype(np.int16)

            # 使用 PyAV 写入音频文件
            with av.open(tmp_file.name, mode="w") as container:
                stream = container.add_stream("pcm_s16le", rate=sample_rate)
                stream.channels = 1

                # 创建音频帧
                frame = av.AudioFrame(
                    samples=frames,
                    layout="mono",
                    format="s16le",
                    sample_rate=sample_rate
                )
                frame.planes[0].to_ndarray()[:] = audio_data_int

                container.mux(stream, frame)

            return tmp_file.name

    yield _create_temp_audio


@pytest.fixture
def temp_image_file():
    """创建临时图片文件"""
    def _create_temp_image(width=640, height=480, color=(255, 0, 0)):
        """创建临时图片文件"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            # 创建彩色图片
            image = Image.new("RGB", (width, height), color)
            image.save(tmp_file.name, "JPEG")
            return tmp_file.name

    yield _create_temp_image


@pytest.fixture
def sample_image_paths(temp_dir, temp_image_file):
    """创建示例图片路径列表"""
    paths = []
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]

    for i, color in enumerate(colors):
        img_path = os.path.join(temp_dir, f"test_image_{i}.jpg")
        # 创建图片文件
        image = Image.new("RGB", (640, 480), color)
        image.save(img_path, "JPEG")
        paths.append(img_path)

    return paths


@pytest.fixture
def sample_audio_path(temp_dir, temp_audio_file):
    """创建示例音频文件"""
    audio_path = os.path.join(temp_dir, "test_audio.wav")
    temp_audio_file = temp_audio_file()

    # 复制临时文件到目标位置
    import shutil
    shutil.copy2(temp_audio_file, audio_path)
    os.unlink(temp_audio_file)

    return audio_path


@pytest.fixture
def mock_audio_utils(monkeypatch):
    """Mock 音频工具函数"""
    def mock_get_duration(audio_path):
        return 10.0

    def mock_get_pauses(audio_path, min_pause=0.5, noise_threshold=-35):
        return [2.0, 5.0, 8.0]

    monkeypatch.setattr("utils.audio_utils.get_audio_duration_ffmpeg", mock_get_duration)
    monkeypatch.setattr("utils.audio_utils.get_audio_pauses", mock_get_pauses)


@pytest.fixture
def mock_image_utils(monkeypatch):
    """Mock 图片工具函数"""
    def mock_get_image_paths(dir_path):
        return [
            os.path.join(dir_path, "image1.jpg"),
            os.path.join(dir_path, "image2.jpg"),
            os.path.join(dir_path, "image3.jpg")
        ]

    def mock_get_audio_path():
        return "audio.wav"

    monkeypatch.setattr("utils.image_utils.get_image_paths", mock_get_image_paths)
    monkeypatch.setattr("utils.image_utils.get_audio_path", mock_get_audio_path)


# 标记定义
pytestmark = pytest.mark.unit
