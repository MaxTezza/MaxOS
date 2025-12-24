"""Tests for multimodal handler."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from max_os.core.multimodal_handler import MultimodalHandler


def test_detect_text_input():
    """Test text input detection."""
    handler = MultimodalHandler()

    assert handler.detect_input_type("Hello world") == "text"
    assert handler.detect_input_type("Some random text") == "text"


def test_detect_image_bytes():
    """Test image detection from bytes."""
    handler = MultimodalHandler()

    # JPEG magic bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0"
    assert handler.detect_input_type(jpeg_bytes) == "image"

    # PNG magic bytes
    png_bytes = b"\x89PNG\r\n\x1a\n"
    assert handler.detect_input_type(png_bytes) == "image"

    # GIF magic bytes
    gif_bytes = b"GIF89a"
    assert handler.detect_input_type(gif_bytes) == "image"


def test_detect_audio_bytes():
    """Test audio detection from bytes."""
    handler = MultimodalHandler()

    # WAV magic bytes
    wav_bytes = b"RIFF....WAVE"
    assert handler.detect_input_type(wav_bytes) == "audio"

    # MP3 magic bytes
    mp3_bytes = b"ID3\x03\x00"
    assert handler.detect_input_type(mp3_bytes) == "audio"


def test_detect_video_bytes():
    """Test video detection from bytes."""
    handler = MultimodalHandler()

    # MP4 magic bytes
    mp4_bytes = b"\x00\x00\x00\x18ftypmp42"
    assert handler.detect_input_type(mp4_bytes) == "video"


def test_detect_file_by_extension():
    """Test file type detection by extension."""
    handler = MultimodalHandler()

    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "is_file", return_value=True):
            assert handler.detect_input_type("image.jpg") == "image"
            assert handler.detect_input_type("photo.png") == "image"
            assert handler.detect_input_type("audio.wav") == "audio"
            assert handler.detect_input_type("song.mp3") == "audio"
            assert handler.detect_input_type("video.mp4") == "video"
            assert handler.detect_input_type("movie.avi") == "video"
            assert handler.detect_input_type("document.txt") == "text"


def test_detect_pil_image():
    """Test PIL Image detection."""
    with patch("max_os.core.multimodal_handler.Image") as mock_image:
        mock_img = MagicMock()
        mock_image.Image = type(mock_img)

        handler = MultimodalHandler()
        result = handler.detect_input_type(mock_img)

        assert result == "image"


def test_validate_image_file():
    """Test image file validation."""
    handler = MultimodalHandler()

    # Valid image
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB
            assert handler.validate_file("image.jpg", "image") is True

    # Too large
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB
            assert handler.validate_file("image.jpg", "image") is False

    # Wrong format
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1024
            assert handler.validate_file("image.bmp", "video") is False

    # Doesn't exist
    with patch.object(Path, "exists", return_value=False):
        assert handler.validate_file("nonexistent.jpg", "image") is False


def test_validate_audio_file():
    """Test audio file validation."""
    handler = MultimodalHandler()

    # Valid audio
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 10 * 1024 * 1024  # 10MB
            assert handler.validate_file("audio.wav", "audio") is True

    # Too large
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 200 * 1024 * 1024  # 200MB
            assert handler.validate_file("audio.wav", "audio") is False


def test_validate_video_file():
    """Test video file validation."""
    handler = MultimodalHandler()

    # Valid video
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB
            assert handler.validate_file("video.mp4", "video") is True

    # Too large
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 600 * 1024 * 1024  # 600MB
            assert handler.validate_file("video.mp4", "video") is False


def test_load_image():
    """Test image loading."""
    with patch("max_os.core.multimodal_handler.Image") as mock_image:
        mock_img = MagicMock()
        mock_image.open.return_value = mock_img

        handler = MultimodalHandler()

        with patch.object(MultimodalHandler, "validate_file", return_value=True):
            result = handler.load_image("test.jpg")
            assert result == mock_img
            mock_image.open.assert_called_once_with(Path("test.jpg"))


def test_load_image_invalid():
    """Test loading invalid image."""
    with patch("max_os.core.multimodal_handler.Image"):
        handler = MultimodalHandler()

        with patch.object(MultimodalHandler, "validate_file", return_value=False):
            with pytest.raises(ValueError, match="Invalid image file"):
                handler.load_image("invalid.jpg")


def test_load_audio():
    """Test audio loading."""
    handler = MultimodalHandler()
    audio_data = b"fake audio data"

    with patch.object(MultimodalHandler, "validate_file", return_value=True):
        with patch.object(Path, "read_bytes", return_value=audio_data):
            result = handler.load_audio("test.wav")
            assert result == audio_data


def test_load_audio_invalid():
    """Test loading invalid audio."""
    handler = MultimodalHandler()

    with patch.object(handler, "validate_file", return_value=False):
        with pytest.raises(ValueError, match="Invalid audio file"):
            handler.load_audio("invalid.wav")


def test_load_video():
    """Test video loading."""
    handler = MultimodalHandler()
    video_data = b"fake video data"

    with patch.object(MultimodalHandler, "validate_file", return_value=True):
        with patch.object(Path, "read_bytes", return_value=video_data):
            result = handler.load_video("test.mp4")
            assert result == video_data


def test_load_video_invalid():
    """Test loading invalid video."""
    handler = MultimodalHandler()

    with patch.object(handler, "validate_file", return_value=False):
        with pytest.raises(ValueError, match="Invalid video file"):
            handler.load_video("invalid.mp4")


def test_supported_formats():
    """Test supported format constants."""
    assert ".jpg" in MultimodalHandler.SUPPORTED_IMAGE_FORMATS
    assert ".png" in MultimodalHandler.SUPPORTED_IMAGE_FORMATS
    assert ".wav" in MultimodalHandler.SUPPORTED_AUDIO_FORMATS
    assert ".mp3" in MultimodalHandler.SUPPORTED_AUDIO_FORMATS
    assert ".mp4" in MultimodalHandler.SUPPORTED_VIDEO_FORMATS
    assert ".avi" in MultimodalHandler.SUPPORTED_VIDEO_FORMATS


def test_size_limits():
    """Test size limit constants."""
    assert MultimodalHandler.MAX_IMAGE_SIZE == 20 * 1024 * 1024
    assert MultimodalHandler.MAX_AUDIO_SIZE == 100 * 1024 * 1024
    assert MultimodalHandler.MAX_VIDEO_SIZE == 500 * 1024 * 1024
