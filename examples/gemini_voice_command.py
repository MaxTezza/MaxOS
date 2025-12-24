"""Example: Voice command processing with Gemini.

This demonstrates how to use Gemini to process voice commands directly.
"""

import asyncio
from pathlib import Path

from max_os.core.gemini_client import GeminiClient
from max_os.core.multimodal_handler import MultimodalHandler


async def process_voice_command(audio_path: str) -> str:
    """Process a voice command using Gemini.

    Args:
        audio_path: Path to audio file

    Returns:
        Transcription and response
    """
    # Initialize Gemini client
    gemini = GeminiClient(user_id="demo_user")

    # Validate audio
    handler = MultimodalHandler()
    if not handler.validate_file(audio_path, "audio"):
        raise ValueError(f"Invalid audio file: {audio_path}")

    # Load audio
    audio_bytes = handler.load_audio(audio_path)

    # Process voice command
    response = await gemini.process(audio=audio_bytes)

    return response


async def process_voice_with_context(audio_path: str, context: str) -> str:
    """Process voice command with additional context.

    Args:
        audio_path: Path to audio file
        context: Additional context about the user or situation

    Returns:
        Contextual response
    """
    gemini = GeminiClient(user_id="demo_user")
    handler = MultimodalHandler()

    if not handler.validate_file(audio_path, "audio"):
        raise ValueError(f"Invalid audio file: {audio_path}")

    audio_bytes = handler.load_audio(audio_path)

    # Process with context
    response = await gemini.process(
        audio=audio_bytes,
        system_prompt=f"User context: {context}. Respond naturally to their voice command.",
    )

    return response


async def main():
    """Main function."""
    print("Gemini Voice Command Demo")
    print("=" * 50)

    # Example usage
    audio_path = "voice_command.wav"

    if Path(audio_path).exists():
        print(f"\nProcessing voice command: {audio_path}")

        # Simple voice processing
        response = await process_voice_command(audio_path)
        print(f"\nResponse: {response}")

        # Voice processing with context
        context = "User is in the kitchen and recently bought milk, eggs, and bread."
        contextual_response = await process_voice_with_context(audio_path, context)
        print(f"\nContextual Response: {contextual_response}")

    else:
        print(f"\nAudio file not found: {audio_path}")
        print("This is a demo. To use this example:")
        print("1. Record a voice command and save as WAV file")
        print("2. Update the 'audio_path' variable")
        print("3. Set GOOGLE_API_KEY environment variable")
        print("4. Run this script again")
        print("\nExample voice commands:")
        print("  - 'What can I make with the ingredients in my pantry?'")
        print("  - 'Play some relaxing music'")
        print("  - 'What's on my calendar today?'")


if __name__ == "__main__":
    asyncio.run(main())
