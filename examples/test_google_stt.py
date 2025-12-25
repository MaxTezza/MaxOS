"""Test Google Cloud Speech-to-Text (Chirp 2 model)."""

import asyncio
import os

from max_os.interfaces.voice.google_stt import GoogleSTT


async def test_stt():
    """Test Google Cloud STT."""
    print("🎤 Testing Google Cloud Speech-to-Text (Chirp 2)")
    print("=" * 60)

    # Check credentials
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("⚠️  GOOGLE_CLOUD_PROJECT environment variable not set")
        print("Set it with: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        return

    try:
        stt = GoogleSTT(project_id=project_id)
        print(f"✅ GoogleSTT initialized successfully")
        print(f"   Model: {stt.model}")
        print(f"   Language: {stt.language_code}")
        print()

        # Note: Actual audio streaming would require microphone input
        print("📝 STT is ready for audio streaming")
        print("   To test with real audio, integrate with PyAudio or similar")
        print()
        print("Example usage:")
        print("   async for transcript in stt.stream_recognize(audio_stream):")
        print("       print(f'Transcript: {transcript}')")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure you have:")
        print("1. Created a Google Cloud project")
        print("2. Enabled the Speech-to-Text API")
        print("3. Set up authentication:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'")
        print("   export GOOGLE_CLOUD_PROJECT='your-project-id'")


if __name__ == "__main__":
    asyncio.run(test_stt())
