"""Unified voice + vision + Gemini control - NO keyboard/mouse needed."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

from max_os.core.gemini_client import GeminiClient


class MultimodalController:
    """Unified voice + vision + Gemini control - NO keyboard/mouse needed."""

    def __init__(
        self,
        gemini_model: str = "gemini-2.0-flash",
        camera_index: int = 0,
        wake_word: str = "hey max",
        cursor_mode: str = "gaze",
    ):
        """Initialize multimodal controller.

        Args:
            gemini_model: Gemini model to use
            camera_index: Camera device index
            wake_word: Wake word for voice activation
            cursor_mode: Cursor control mode ("gaze" or "hand")
        """
        if cv2 is None:
            raise RuntimeError(
                "opencv-python not installed. Install with: pip install 'maxos[google]'"
            )

        # Lazy imports to avoid dependency issues
        try:
            from max_os.interfaces.voice.google_stt import GoogleSTT
            from max_os.interfaces.voice.google_tts import GoogleTTS
            from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker
        except ImportError as e:
            raise RuntimeError(
                f"Google AI stack dependencies not installed: {e}. "
                "Install with: pip install 'maxos[google]'"
            )

        self.stt = GoogleSTT()
        self.tts = GoogleTTS()
        self.vision = MediaPipeTracker()
        self.gemini = GeminiClient(model=gemini_model)

        self.camera = cv2.VideoCapture(camera_index)
        self.voice_active = False
        self.cursor_mode = cursor_mode
        self.wake_word = wake_word.lower()
        self.running = False

    async def run(self):
        """Main control loop - process voice + vision simultaneously."""
        self.running = True

        # Start voice listener
        voice_task = asyncio.create_task(self._listen_for_voice())

        # Start vision loop
        vision_task = asyncio.create_task(self._process_vision())

        try:
            await asyncio.gather(voice_task, vision_task)
        except KeyboardInterrupt:
            self.running = False
            print("\nShutting down...")
        finally:
            self.cleanup()

    async def _listen_for_voice(self):
        """Continuous voice listening with wake word."""
        print(f"Listening for wake word: '{self.wake_word}'")

        # This is a simplified implementation
        # In production, would use actual audio stream from microphone
        while self.running:
            try:
                # Simulate listening - would use actual microphone stream
                # async for transcript in self.stt.stream_recognize(self._get_audio_stream()):
                #     await self._process_voice_command(transcript)
                
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Voice processing error: {e}")
                await asyncio.sleep(1)

    async def _process_voice_command(self, transcript: str):
        """Process voice command.

        Args:
            transcript: Transcribed text
        """
        # Wake word detection
        if self.wake_word in transcript.lower():
            self.voice_active = True
            await self._speak("Yes?")
            return

        if self.voice_active:
            # Get current camera frame for context
            ret, frame = self.camera.read()

            # Send to Gemini with multimodal context
            response = await self.gemini.process(
                text=transcript,
                image=frame if ret else None,
            )

            # Speak response
            await self._speak(response)

            # Execute any commands
            await self._execute_command(response)

            # Deactivate after response
            self.voice_active = False

    async def _process_vision(self):
        """Process camera for gestures and eye tracking."""
        print("Starting vision processing...")

        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue

            # Process with MediaPipe
            results = self.vision.process_frame(frame)

            # Eye gaze cursor control
            if self.cursor_mode == "gaze" and results["eye_gaze"]:
                self._move_cursor_to_gaze(results["eye_gaze"])

            # Hand gesture commands
            for gesture in results["gestures"]:
                await self._handle_gesture(gesture)

            # Draw overlay
            self.vision.draw_landmarks(frame, results)

            # Add status text
            status_text = f"Mode: {self.cursor_mode} | Voice: {'Active' if self.voice_active else 'Waiting'}"
            cv2.putText(
                frame,
                status_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            # Display gestures
            if results["gestures"]:
                gesture_text = f"Gestures: {', '.join(results['gestures'])}"
                cv2.putText(
                    frame,
                    gesture_text,
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2,
                )

            cv2.imshow("MaxOS Vision", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.running = False
                break

            await asyncio.sleep(0.01)  # ~100 FPS

    async def _speak(self, text: str):
        """Convert text to speech and play.

        Args:
            text: Text to speak
        """
        print(f"MaxOS: {text}")
        # In production, would actually play audio
        # audio = await self.tts.synthesize(text)
        # play_audio(audio)

    def _move_cursor_to_gaze(self, gaze: Dict[str, Any]):
        """Move system cursor based on eye gaze.

        Args:
            gaze: Gaze coordinates dictionary
        """
        # In production, would use pyautogui or similar
        # screen_width, screen_height = pyautogui.size()
        # x = int(gaze["x"] * screen_width)
        # y = int(gaze["y"] * screen_height)
        # pyautogui.moveTo(x, y)
        pass

    async def _handle_gesture(self, gesture: str):
        """Execute commands based on hand gestures.

        Args:
            gesture: Gesture name
        """
        gesture_commands = {
            "right_thumbs_up": "approve last action",
            "right_peace_sign": "screenshot",
            "right_pointing": "select item",
            "right_fist": "grab/drag",
            "right_open_palm": "release/stop",
        }

        if gesture in gesture_commands:
            command = gesture_commands[gesture]
            print(f"Gesture detected: {gesture} -> {command}")
            # Send to Gemini for execution
            # await self.gemini.process(command)

    async def _execute_command(self, response: str):
        """Execute system commands from Gemini response.

        Args:
            response: Gemini response text
        """
        # Parse response for executable commands
        # This would integrate with the existing MaxOS command system
        pass

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, "camera"):
            self.camera.release()
        if hasattr(self, "vision"):
            self.vision.close()
        cv2.destroyAllWindows()
