"""
The Senses of MaxOS.
Handles Audio (Microphone -> STT) and Vision (Camera -> Gestures/Object Detection).
"""
import asyncio
import base64
import queue
import threading
from typing import Optional, Tuple

import cv2
import structlog
# Note: speech_recognition and pyaudio must be installed
import speech_recognition as sr

logger = structlog.get_logger("max_os.senses")

class Senses:
    def __init__(self, wake_word: str = "max"):
        self.wake_word = wake_word.lower()
        self.listening = False
        self.seeing = False
        
        # Queues for communicating with the main thread
        self.audio_queue = queue.Queue()
        self.vision_queue = queue.Queue()
        
        # Audio setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Video setup
        self.camera = None

    def start(self):
        """Start sensory loops in background threads."""
        self.listening = True
        self.seeing = True
        
        # Start Audio Thread
        threading.Thread(target=self._listen_loop, daemon=True).start()
        
        # Start Video Thread
        threading.Thread(target=self._watch_loop, daemon=True).start()
        
        logger.info("MaxOS Senses Activated (Ears & Eyes wide open)")

    def stop(self):
        self.listening = False
        self.seeing = False
        if self.camera:
            self.camera.release()

    def get_next_command(self) -> Optional[str]:
        """Non-blocking check for new voice commands."""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def get_current_frame(self) -> Optional[bytes]:
        """Get the latest camera frame (base64 encoded for Gemini)."""
        try:
            return self.vision_queue.get_nowait()
        except queue.Empty:
            return None

    def _listen_loop(self):
        """Continuous listening loop."""
        logger.info("Audio listener started")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.listening:
                try:
                    # Listen
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    # Transcribe (using Google's free API for now, switch to Gemini later if needed)
                    text = self.recognizer.recognize_google(audio)
                    text = text.lower()
                    
                    logger.debug(f"Heard: {text}")
                    
                    # Wake Word Detection
                    if self.wake_word in text:
                        command = text.split(self.wake_word, 1)[1].strip()
                        if command:
                            logger.info(f"Command detected: {command}")
                            self.audio_queue.put(command)
                            
                except sr.WaitTimeoutError:
                    continue  # Just listening silence
                except sr.UnknownValueError:
                    continue  # Unintelligible
                except Exception as e:
                    logger.error(f"Audio error: {e}")

    def _watch_loop(self):
        """Continuous camera loop."""
        logger.info("Video watcher started")
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                logger.warning("Camera not found. Vision disabled.")
                return

            while self.seeing:
                ret, frame = self.camera.read()
                if not ret:
                    continue
                
                # Simple presence/motion detection could go here
                
                # Periodically sync frame to queue (don't spam it)
                # For now, we only push frames when requested or every X seconds?
                # Actually, let's keep the queue size 1 (latest frame)
                
                # Compress to jpg
                _, buffer = cv2.imencode('.jpg', frame)
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                
                # Update queue (drop old if full)
                if self.vision_queue.full():
                    try:
                        self.vision_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.vision_queue.put(jpg_as_text)
                
                # rate limit
                cv2.waitKey(100) 
                
        except Exception as e:
            logger.error(f"Vision error: {e}")
