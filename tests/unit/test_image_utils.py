"""
image_utils.py 模块的单元测试
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from utils.image_utils import get_image_paths, get_audio_path


class TestGetImagePaths:
    """get_image_paths 函数的测试"""

    def test_existing_directory_with_images(self, temp_dir):
        """测试包含图片的目录"""
        # 创建测试图片文件
        image_files = ["test1.jpg", "test2.png", "test3.gif", "test4.webp", "test5.tiff", "test6.bmp"]
        non_image_files = ["test.txt", "readme.md", "config.json"]

        for filename in image_files + non_image_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)

        # 检查返回的图片路径
        assert len(paths) == len(image_files)
        for img_file in image_files:
            expected_path = os.path.join(temp_dir, img_file)
            assert expected_path in paths

    def test_empty_directory(self, temp_dir):
        """测试空目录"""
        paths = get_image_paths(temp_dir)
        assert paths == []

    def test_nonexistent_directory(self):
        """测试不存在的目录"""
        paths = get_image_paths("nonexistent_directory")
        assert paths == []

    def test_directory_with_no_images(self, temp_dir):
        """测试没有图片文件的目录"""
        # 创建非图片文件
        non_image_files = ["test.txt", "readme.md", "config.json", "data.csv"]

        for filename in non_image_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        assert paths == []

    def test_case_insensitive_extensions(self, temp_dir):
        """测试扩展名大小写不敏感"""
        image_files = ["test1.JPG", "test2.JPEG", "test3.PnG", "test4.GIF", "test5.WEBP"]

        for filename in image_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        assert len(paths) == len(image_files)

    def test_supported_extensions(self, temp_dir):
        """测试所有支持的扩展名"""
        supported_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}

        for ext in supported_extensions:
            filename = f"test{ext}"
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        assert len(paths) == len(supported_extensions)

    def test_unsupported_extensions(self, temp_dir):
        """测试不支持的扩展名"""
        unsupported_files = ["test.pdf", "test.docx", "test.xls", "test.zip", "test.exe"]

        for filename in unsupported_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        assert len(paths) == 0

    def test_mixed_files(self, temp_dir):
        """测试混合文件类型"""
        all_files = [
            "image1.jpg", "image2.png", "text1.txt", "config.json",
            "image3.gif", "readme.md", "data.csv", "image4.webp"
        ]

        for filename in all_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        expected_image_count = 4  # image1.jpg, image2.png, image3.gif, image4.webp
        assert len(paths) == expected_image_count

    def test_directory_with_subdirectories(self, temp_dir):
        """测试包含子目录的情况（只处理当前目录）"""
        # 创建主目录文件
        main_file = os.path.join(temp_dir, "main.jpg")
        with open(main_file, 'w') as f:
            f.write("test content")

        # 创建子目录
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        sub_file = os.path.join(subdir, "sub.jpg")
        with open(sub_file, 'w') as f:
            f.write("test content")

        paths = get_image_paths(temp_dir)
        # 应该只包含主目录的文件
        assert len(paths) == 1
        assert main_file in paths
        assert sub_file not in paths

    def test_ordering(self, temp_dir):
        """测试文件排序（按文件系统读取顺序）"""
        image_files = ["zebra.jpg", "apple.jpg", "banana.jpg"]

        for filename in image_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        paths = get_image_paths(temp_dir)
        # 检查返回的顺序与os.listdir一致
        expected_order = [os.path.join(temp_dir, f) for f in sorted(image_files)]
        assert paths == expected_order


class TestGetAudioPath:
    """get_audio_path 函数的测试"""

    @patch('os.path.exists')
    def test_wav_file_exists(self, mock_exists, temp_dir):
        """测试 WAV 文件存在的情况"""
        # 在当前工作目录创建 WAV 文件
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            mock_exists.side_effect = lambda path: path in ["audio.wav", "audio.mp3"]

            # 创建 WAV 文件
            with open("audio.wav", 'w') as f:
                f.write("test audio")

            result = get_audio_path()
            assert result == "audio.wav"
        finally:
            os.chdir(original_cwd)

    @patch('os.path.exists')
    def test_mp3_file_exists(self, mock_exists, temp_dir):
        """测试只有 MP3 文件存在的情况"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            mock_exists.side_effect = lambda path: path in ["audio.mp3"]

            # 创建 MP3 文件
            with open("audio.mp3", 'w') as f:
                f.write("test audio")

            result = get_audio_path()
            assert result == "audio.mp3"
        finally:
            os.chdir(original_cwd)

    @patch('os.path.exists')
    def test_both_files_exist(self, mock_exists, temp_dir):
        """测试 WAV 和 MP3 都存在的情况（应该优先 WAV）"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            mock_exists.return_value = True

            # 创建两个文件
            with open("audio.wav", 'w') as f:
                f.write("test audio")
            with open("audio.mp3", 'w') as f:
                f.write("test audio")

            result = get_audio_path()
            assert result == "audio.wav"  # 优先返回 WAV
        finally:
            os.chdir(original_cwd)

    @patch('os.path.exists')
    def test_no_audio_files(self, mock_exists):
        """测试没有音频文件的情况"""
        mock_exists.return_value = False

        result = get_audio_path()
        assert result is None

    @patch('os.path.exists')
    def test_file_exists_false_cases(self, mock_exists):
        """测试文件不存在的各种情况"""
        test_cases = [
            [],  # 空列表
            ["audio.wav"],  # 只有 WAV
            ["audio.mp3"],  # 只有 MP3
            ["other.mp3", "music.wav"],  # 错误名称
        ]

        for case in test_cases:
            mock_exists.side_effect = lambda path: path in case
            result = get_audio_path()
            assert result is None

    def test_actual_file_operations(self, temp_dir):
        """测试实际文件操作"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # 测试没有文件
            result = get_audio_path()
            assert result is None

            # 创建 MP3 文件
            with open("audio.mp3", 'w') as f:
                f.write("test audio")

            result = get_audio_path()
            assert result == "audio.mp3"

            # 创建 WAV 文件（应该优先）
            with open("audio.wav", 'w') as f:
                f.write("test audio")

            result = get_audio_path()
            assert result == "audio.wav"

        finally:
            os.chdir(original_cwd)
