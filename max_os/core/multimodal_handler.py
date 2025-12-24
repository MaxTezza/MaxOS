"""Multimodal input handler for detecting and processing different input types."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore


class MultimodalHandler:
    """Handles detection and processing of multimodal inputs."""

    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB

    # Supported formats
    SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

    @staticmethod
    def detect_input_type(input_data: str | bytes | Path | Any) -> str:
        """Detect the type of input data.

        Args:
            input_data: Input data to analyze

        Returns:
            Input type: "text", "image", "audio", "video", or "unknown"
        """
        # Bytes data - check first bytes for magic numbers
        if isinstance(input_data, bytes):
            return MultimodalHandler._detect_bytes_type(input_data)

        # String or Path - check if it's a file path
        if isinstance(input_data, (str, Path)):
            path = Path(input_data)
            if path.exists() and path.is_file():
                return MultimodalHandler._detect_file_type(path)
            # Otherwise treat as text
            return "text"

        # PIL Image
        if Image and isinstance(input_data, Image.Image):
            return "image"

        return "unknown"

    @staticmethod
    def _detect_bytes_type(data: bytes) -> str:
        """Detect type from byte data using magic numbers.

        Args:
            data: Byte data

        Returns:
            Detected type: "image", "audio", "video", or "unknown"
        """
        # Check magic numbers
        if data.startswith(b"\xff\xd8\xff"):  # JPEG
            return "image"
        if data.startswith(b"\x89PNG"):  # PNG
            return "image"
        if data.startswith(b"GIF8"):  # GIF
            return "image"
        if data.startswith(b"RIFF") and b"WAVE" in data[:20]:  # WAV
            return "audio"
        if data.startswith(b"ID3") or data.startswith(b"\xff\xfb"):  # MP3
            return "audio"
        if data.startswith(b"\x00\x00\x00") and b"ftyp" in data[:20]:  # MP4/MOV
            # Could be video or audio
            return "video"

        return "unknown"

    @staticmethod
    def _detect_file_type(path: Path) -> str:
        """Detect file type from extension and MIME type.

        Args:
            path: File path

        Returns:
            Detected type: "image", "audio", "video", or "text"
        """
        suffix = path.suffix.lower()

        if suffix in MultimodalHandler.SUPPORTED_IMAGE_FORMATS:
            return "image"
        if suffix in MultimodalHandler.SUPPORTED_AUDIO_FORMATS:
            return "audio"
        if suffix in MultimodalHandler.SUPPORTED_VIDEO_FORMATS:
            return "video"

        # Try MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            if mime_type.startswith("image/"):
                return "image"
            if mime_type.startswith("audio/"):
                return "audio"
            if mime_type.startswith("video/"):
                return "video"

        return "text"

    @staticmethod
    def validate_file(path: str | Path, input_type: str) -> bool:
        """Validate file format and size.

        Args:
            path: File path
            input_type: Expected input type

        Returns:
            True if valid, False otherwise
        """
        path = Path(path)

        if not path.exists():
            return False

        # Check file size
        size = path.stat().st_size

        if input_type == "image" and size > MultimodalHandler.MAX_IMAGE_SIZE:
            return False
        if input_type == "audio" and size > MultimodalHandler.MAX_AUDIO_SIZE:
            return False
        if input_type == "video" and size > MultimodalHandler.MAX_VIDEO_SIZE:
            return False

        # Check format
        suffix = path.suffix.lower()
        if input_type == "image" and suffix not in MultimodalHandler.SUPPORTED_IMAGE_FORMATS:
            return False
        if input_type == "audio" and suffix not in MultimodalHandler.SUPPORTED_AUDIO_FORMATS:
            return False
        if input_type == "video" and suffix not in MultimodalHandler.SUPPORTED_VIDEO_FORMATS:
            return False

        return True

    @staticmethod
    def load_image(path: str | Path) -> Image.Image:
        """Load image from path.

        Args:
            path: Image file path

        Returns:
            PIL Image object

        Raises:
            RuntimeError: If PIL not installed
            ValueError: If file invalid
        """
        if Image is None:
            raise RuntimeError("PIL/Pillow package not installed")

        path = Path(path)
        if not MultimodalHandler.validate_file(path, "image"):
            raise ValueError(f"Invalid image file: {path}")

        return Image.open(path)

    @staticmethod
    def load_audio(path: str | Path) -> bytes:
        """Load audio file as bytes.

        Args:
            path: Audio file path

        Returns:
            Audio bytes

        Raises:
            ValueError: If file invalid
        """
        path = Path(path)
        if not MultimodalHandler.validate_file(path, "audio"):
            raise ValueError(f"Invalid audio file: {path}")

        return path.read_bytes()

    @staticmethod
    def load_video(path: str | Path) -> bytes:
        """Load video file as bytes.

        Args:
            path: Video file path

        Returns:
            Video bytes

        Raises:
            ValueError: If file invalid
        """
        path = Path(path)
        if not MultimodalHandler.validate_file(path, "video"):
            raise ValueError(f"Invalid video file: {path}")

        return path.read_bytes()
