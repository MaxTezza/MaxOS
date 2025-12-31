"""
The Voice of MaxOS.
Wraps Google Cloud Text-to-Speech API.
"""

import os
import structlog
from google.cloud import texttospeech
import subprocess
import tempfile

from max_os.utils.config import load_settings

logger = structlog.get_logger("max_os.core.voice")


class VoiceEngine:
    def __init__(self):
        self.settings = load_settings()
        self.enabled = False
        
        api_key = self.settings.llm.get("google_api_key") or os.environ.get("GOOGLE_API_KEY")
        
        try:
            if api_key:
                # Use API Key for TTS if provided
                from google.api_core import client_options
                options = client_options.ClientOptions(api_key=api_key)
                self.client = texttospeech.TextToSpeechClient(client_options=options)
                logger.info("Voice Engine Online (Using API Key)")
            else:
                # Fallback to ADC
                self.client = texttospeech.TextToSpeechClient()
                logger.info("Voice Engine Online (Using ADC)")

            self.voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Journey-F" # Neural Voice
            )
            # Load initial settings
            self._update_config()
            self.enabled = True
        except Exception as e:
            logger.error("Voice Engine Failed to Init. Audio output will be disabled.", error=str(e))
            self.enabled = False

    def _update_config(self):
        """Reloads audio config from settings."""
        speed = self.settings.accessibility.get("voice_speed", 1.0)
        # TTS API mapping: 0.25 to 4.0
        
        volume = self.settings.accessibility.get("voice_volume", 1.0)
        # TTS API volume_gain_db: -96.0 to 16.0. 
        # Simple mapping: 1.0 = 0db. 0.5 = -6db. 
        # Let's just use 0db for now or implement logic later if requested.
        
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speed
        )

    def speak(self, text: str):
        if not self.enabled:
            logger.warning("Voice disabled, cannot speak:", text=text)
            return

        # Refresh config in case it changed
        self._update_config()

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice, audio_config=self.audio_config
            )

            # Write to temp file and play
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(response.audio_content)
                temp_path = f.name
            
            # Play using aplay (WAV)
            subprocess.run(["aplay", "-q", temp_path], check=False)
            
            # Cleanup
            os.remove(temp_path)
            
        except Exception as e:
            logger.error("TTS Error", error=str(e))
