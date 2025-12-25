"""Test Google Cloud Text-to-Speech (Studio voices)."""

import asyncio

from max_os.interfaces.voice.google_tts import GoogleTTS


async def test_tts():
    """Test Google Cloud TTS."""
    print("🔊 Testing Google Cloud Text-to-Speech (Studio Voice)")
    print("=" * 60)

    try:
        tts = GoogleTTS(voice_name="en-US-Studio-O")
        print("✅ GoogleTTS initialized successfully")
        print(f"   Voice: {tts.voice.name}")
        print(f"   Language: {tts.voice.language_code}")
        print()

        # Test basic synthesis
        text = "Hello! I am Max OS, your AI-powered operating system assistant."
        print(f"📝 Synthesizing: '{text}'")

        audio = await tts.synthesize(text)
        print(f"✅ Audio generated: {len(audio)} bytes")
        print()

        # Test emotion synthesis
        print("🎭 Testing emotion synthesis...")
        emotional_text = "I'm excited to help you today!"
        audio = await tts.synthesize_with_emotion(emotional_text, emotion="excited")
        print(f"✅ Emotional audio generated: {len(audio)} bytes")
        print()

        print("💡 To play the audio, you can:")
        print("   1. Save to file: with open('output.wav', 'wb') as f: f.write(audio)")
        print("   2. Use PyAudio or similar to play directly")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure you have:")
        print("1. Created a Google Cloud project")
        print("2. Enabled the Text-to-Speech API")
        print("3. Set up authentication:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'")


if __name__ == "__main__":
    asyncio.run(test_tts())
