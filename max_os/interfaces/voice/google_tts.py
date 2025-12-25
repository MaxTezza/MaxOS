"""Google Cloud Text-to-Speech with ultra-realistic Studio voices."""

from __future__ import annotations

try:
    from google.cloud import texttospeech_v1
except ImportError:  # pragma: no cover
    texttospeech_v1 = None  # type: ignore


class GoogleTTS:
    """Google Cloud TTS with ultra-realistic Studio voices."""

    def __init__(
        self,
        voice_name: str = "en-US-Studio-O",
        language_code: str = "en-US",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ):
        """Initialize Google Cloud Text-to-Speech client.

        Args:
            voice_name: Voice name (e.g., "en-US-Studio-O" for Studio voices)
            language_code: Language code (e.g., "en-US")
            speaking_rate: Speaking rate multiplier (0.25 to 4.0)
            pitch: Voice pitch adjustment in semitones (-20.0 to 20.0)
        """
        if texttospeech_v1 is None:
            raise RuntimeError(
                "google-cloud-texttospeech package not installed. "
                "Install with: pip install 'maxos[google]'"
            )

        self.client = texttospeech_v1.TextToSpeechAsyncClient()
        self.voice = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,  # Studio voices = most realistic
        )
        self.audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16,
            speaking_rate=speaking_rate,
            pitch=pitch,
            effects_profile_id=["headphone-class-device"],
        )

    async def synthesize(self, text: str, use_ssml: bool = False) -> bytes:
        """Convert text to speech audio.

        Args:
            text: Text to convert to speech
            use_ssml: Whether the text is in SSML format

        Returns:
            Audio content in bytes (LINEAR16 format)
        """
        synthesis_input = texttospeech_v1.SynthesisInput()
        if use_ssml:
            synthesis_input.ssml = text
        else:
            synthesis_input.text = text

        response = await self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config,
        )

        return response.audio_content

    async def synthesize_with_emotion(
        self, text: str, emotion: str = "neutral", emphasis_level: str = "moderate"
    ) -> bytes:
        """Add emotion using SSML.

        Args:
            text: Text to convert to speech
            emotion: Emotion to apply (currently uses prosody adjustments)
            emphasis_level: Level of emphasis ("strong", "moderate", "reduced", "none")

        Returns:
            Audio content in bytes
        """
        # Map emotions to prosody settings
        emotion_map = {
            "excited": {"rate": "fast", "pitch": "+2st"},
            "calm": {"rate": "slow", "pitch": "-1st"},
            "neutral": {"rate": "medium", "pitch": "0st"},
            "emphatic": {"rate": "medium", "pitch": "+1st"},
        }

        prosody = emotion_map.get(emotion, emotion_map["neutral"])

        ssml = f"""
        <speak>
            <prosody rate="{prosody['rate']}" pitch="{prosody['pitch']}">
                <emphasis level="{emphasis_level}">{text}</emphasis>
            </prosody>
        </speak>
        """

        return await self.synthesize(ssml, use_ssml=True)

    def synthesize_sync(self, text: str, use_ssml: bool = False) -> bytes:
        """Synchronous version of synthesize.

        Args:
            text: Text to convert to speech
            use_ssml: Whether the text is in SSML format

        Returns:
            Audio content in bytes
        """
        synthesis_input = texttospeech_v1.SynthesisInput()
        if use_ssml:
            synthesis_input.ssml = text
        else:
            synthesis_input.text = text

        # Use sync client for synchronous call
        sync_client = texttospeech_v1.TextToSpeechClient()
        response = sync_client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config,
        )

        return response.audio_content
