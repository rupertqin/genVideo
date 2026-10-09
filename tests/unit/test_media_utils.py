"""
media_utils.py 模块的单元测试（媒体/音频路径解析）
"""
import os

import pytest

from genvideo.utils.media_utils import (
    AUDIO_FILENAMES,
    ensure_parent_dir,
    find_audio_in,
    get_media_paths,
    resolve_dir,
    MediaType,
)


class TestResolveDir:
    """resolve_dir 函数的测试"""

    def test_configured_exists(self, tmp_path):
        """首选目录存在时直接返回"""
        target = tmp_path / "assets" / "images"
        target.mkdir(parents=True)
        assert resolve_dir(str(target), ("whatever",)) == str(target)

    def test_falls_back_to_first_existing(self, tmp_path):
        """首选不存在时按顺序回退到第一个存在的备用目录"""
        fallback = tmp_path / "media"
        fallback.mkdir()
        other = tmp_path / "images"
        other.mkdir()

        assert resolve_dir(str(tmp_path / "assets"), (str(fallback), str(other))) == str(fallback)

    def test_returns_none_when_nothing_exists(self, tmp_path):
        """都不存在时返回 None"""
        assert resolve_dir(str(tmp_path / "nope"), (str(tmp_path / "also_nope"),)) is None

    def test_ignores_empty_entries(self, tmp_path):
        """忽略 None / 空字符串条目"""
        fallback = tmp_path / "media"
        fallback.mkdir()

        assert resolve_dir(None, ("", str(fallback))) == str(fallback)
        assert resolve_dir("", (None,)) is None

    def test_file_is_not_a_dir(self, tmp_path):
        """文件不算目录"""
        file_path = tmp_path / "audio.wav"
        file_path.write_bytes(b"")
        assert resolve_dir(str(file_path)) is None


class TestFindAudioIn:
    """find_audio_in 函数的测试"""

    def test_direct_file(self, tmp_path):
        """直接给音频文件完整路径时返回自身"""
        audio = tmp_path / "voice.wav"
        audio.write_bytes(b"")
        assert find_audio_in(str(audio)) == str(audio)

    def test_arbitrary_filename_in_dir(self, tmp_path):
        """完整路径里的文件名任意（如 第14集.wav）"""
        audio = tmp_path / "第14集.wav"
        audio.write_bytes(b"")
        assert find_audio_in(str(audio)) == str(audio)

    def test_full_path_not_inside_dir(self, tmp_path):
        """音频不在配置的目录里时返回 None（只认给定路径/目录内的约定文件名）"""
        (tmp_path / "other.wav").write_bytes(b"")
        assert find_audio_in(str(tmp_path)) is None

    def test_directory_with_wav(self, tmp_path):
        """目录里找 audio.wav"""
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"")
        assert find_audio_in(str(tmp_path)) == str(audio)

    def test_directory_with_mp3(self, tmp_path):
        """只有 mp3 时也能找到"""
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"")
        assert find_audio_in(str(tmp_path)) == str(audio)

    def test_wav_preferred_over_mp3(self, tmp_path):
        """wav 优先于 mp3"""
        (tmp_path / "audio.wav").write_bytes(b"")
        (tmp_path / "audio.mp3").write_bytes(b"")
        assert find_audio_in(str(tmp_path)).endswith("audio.wav")

    def test_directory_without_audio(self, tmp_path):
        """目录里没有音频文件时返回 None"""
        (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
        assert find_audio_in(str(tmp_path)) is None

    @pytest.mark.parametrize("value", [None, "", "  "])
    def test_empty_input(self, value):
        """空值返回 None"""
        assert find_audio_in(value) is None

    def test_missing_path(self, tmp_path):
        """路径不存在时返回 None"""
        assert find_audio_in(str(tmp_path / "nope")) is None

    def test_audio_filenames_constant(self):
        """默认查找的音频文件名"""
        assert AUDIO_FILENAMES == ("audio.wav", "audio.mp3")


class TestEnsureParentDir:
    """ensure_parent_dir 函数的测试"""

    def test_creates_missing_dir(self, tmp_path):
        """父目录不存在时自动创建"""
        target = tmp_path / "output" / "video.mp4"
        assert ensure_parent_dir(str(target)) == str(target.parent)
        assert target.parent.is_dir()

    def test_creates_nested_dirs(self, tmp_path):
        """多级目录一并创建"""
        target = tmp_path / "a" / "b" / "c" / "video.mp4"
        ensure_parent_dir(str(target))
        assert target.parent.is_dir()

    def test_existing_dir_is_kept(self, tmp_path):
        """父目录已存在时不报错"""
        target = tmp_path / "video.mp4"
        ensure_parent_dir(str(target))
        assert tmp_path.is_dir()

    def test_no_dir_part(self):
        """纯文件名没有父目录，返回空字符串"""
        assert ensure_parent_dir("video.mp4") == ""

    def test_empty_path(self):
        """空路径返回空字符串"""
        assert ensure_parent_dir("") == ""


class TestGetMediaPaths:
    """get_media_paths 的补充测试（图片/视频混合与排序）"""

    def test_missing_dir_returns_empty(self, tmp_path):
        """目录不存在时返回空列表"""
        assert get_media_paths(str(tmp_path / "nope")) == []

    def test_sorted_by_name_and_typed(self, tmp_path):
        """按文件名排序，并正确区分图片与视频"""
        (tmp_path / "b.jpg").write_bytes(b"")
        (tmp_path / "a.mp4").write_bytes(b"")
        (tmp_path / "c.png").write_bytes(b"")

        items = get_media_paths(str(tmp_path))
        assert [item.name for item in items] == ["a.mp4", "b.jpg", "c.png"]
        assert items[0].media_type == MediaType.VIDEO
        assert items[1].media_type == MediaType.IMAGE
