"""Google Cloud Speech-to-Text with Chirp 2 model."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional

try:
    from google.cloud import speech_v2
    from google.protobuf.duration_pb2 import Duration
except ImportError:  # pragma: no cover
    speech_v2 = None  # type: ignore
    Duration = None  # type: ignore


class GoogleSTT:
    """Google Cloud Speech-to-Text with Chirp 2 model."""

    def __init__(
        self,
        language_code: str = "en-US",
        project_id: Optional[str] = None,
        location: str = "global",
    ):
        """Initialize Google Cloud Speech-to-Text client.

        Args:
            language_code: Language code for recognition (e.g., "en-US")
            project_id: Google Cloud project ID (or use GOOGLE_CLOUD_PROJECT env var)
            location: Google Cloud location (default: "global")
        """
        if speech_v2 is None:
            raise RuntimeError(
                "google-cloud-speech package not installed. "
                "Install with: pip install 'maxos[google]'"
            )

        self.language_code = language_code
        self.model = "chirp-2"  # Latest Google STT model
        self.project_id = project_id
        self.location = location

        # Initialize client
        self.client = speech_v2.SpeechAsyncClient()

    async def stream_recognize(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        """Real-time streaming transcription.

        Args:
            audio_stream: Async generator yielding audio bytes

        Yields:
            Transcribed text strings
        """
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=[self.language_code],
            model=self.model,
            features=speech_v2.RecognitionFeatures(
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                enable_spoken_punctuation=True,
                enable_word_confidence=True,
            ),
        )

        streaming_config = speech_v2.StreamingRecognitionConfig(
            config=config,
            streaming_features=speech_v2.StreamingRecognitionFeatures(
                interim_results=True,
                voice_activity_timeout=speech_v2.StreamingRecognitionFeatures.VoiceActivityTimeout(
                    speech_start_timeout=Duration(seconds=5),
                    speech_end_timeout=Duration(seconds=2),
                ),
            ),
        )

        async for response in self.client.streaming_recognize(
            config=streaming_config, audio_stream=audio_stream
        ):
            if response.results:
                result = response.results[0]
                if result.is_final:
                    yield result.alternatives[0].transcript

    async def recognize(self, audio_content: bytes) -> str:
        """Recognize speech from audio bytes.

        Args:
            audio_content: Audio data in bytes

        Returns:
            Transcribed text
        """
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=[self.language_code],
            model=self.model,
            features=speech_v2.RecognitionFeatures(
                enable_automatic_punctuation=True,
            ),
        )

        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{self.location}/recognizers/_",
            config=config,
            content=audio_content,
        )

        response = await self.client.recognize(request=request)

        if response.results:
            return response.results[0].alternatives[0].transcript
        return ""
