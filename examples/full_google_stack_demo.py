"""
MaxOS - Full Google AI Stack Demo

Demonstrates:
- Gemini 2.0 Flash multimodal understanding
- Google Cloud Speech (Chirp 2) real-time transcription
- Google Cloud TTS (Studio voices) natural speech
- MediaPipe hand/face tracking
- Combined voice + vision control

NO KEYBOARD OR MOUSE NEEDED!
"""

import asyncio
import sys

from max_os.interfaces.multimodal_controller import MultimodalController


async def main():
    """Run the full Google AI stack demo."""
    print("🚀 MaxOS - Google AI Stack Demo")
    print("=" * 70)
    print("✅ Gemini 2.0 Flash - Language understanding")
    print("✅ Chirp 2 - Voice recognition")
    print("✅ Studio Voice - Natural speech")
    print("✅ MediaPipe - Hand/eye tracking")
    print("=" * 70)
    print()
    print("FEATURES:")
    print("  🎤 Voice Control: Say 'Hey Max' to activate")
    print("  👁️  Eye Gaze: Look at items to move cursor")
    print("  👋 Hand Gestures:")
    print("     👍 Thumbs up - Approve")
    print("     ✌️  Peace sign - Screenshot")
    print("     👆 Pointing - Select")
    print("     ✊ Fist - Grab/drag")
    print("     ✋ Open palm - Stop")
    print()
    print("CONTROLS:")
    print("  - Press 'q' in the vision window to quit")
    print("  - Ctrl+C to exit")
    print()
    print("=" * 70)
    print()

    # Check prerequisites
    try:
        import cv2  # noqa: F401
        import google.generativeai as genai  # noqa: F401
        import mediapipe as mp  # noqa: F401
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print()
        print("Install Google AI stack with:")
        print("  pip install 'maxos[google]'")
        sys.exit(1)

    # Check API keys
    import os

    if not os.environ.get("GOOGLE_API_KEY"):
        print("⚠️  Warning: GOOGLE_API_KEY not set")
        print("   Set with: export GOOGLE_API_KEY='your-api-key'")
        print()

    print("Starting multimodal controller...")
    print()

    try:
        controller = MultimodalController(
            gemini_model="gemini-2.0-flash",
            camera_index=0,
            wake_word="hey max",
            cursor_mode="gaze",
        )

        await controller.run()

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Make sure your camera is connected and accessible")
        print("2. Check that GOOGLE_API_KEY is set")
        print("3. For Cloud Speech/TTS, set GOOGLE_APPLICATION_CREDENTIALS")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
