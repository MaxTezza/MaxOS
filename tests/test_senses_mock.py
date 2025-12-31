import queue
import time
from unittest.mock import MagicMock, patch

import pytest
from max_os.core.senses import Senses

def test_senses_initialization():
    """Test that Senses initializes correctly."""
    with patch("speech_recognition.Microphone"), \
         patch("speech_recognition.Recognizer"), \
         patch("cv2.VideoCapture"):
        senses = Senses()
        assert senses.listening is False
        assert senses.seeing is False
        assert senses.wake_word == "max"

def test_Start_stop():
    """Test start and stop methods update state."""
    with patch("speech_recognition.Microphone"), \
         patch("speech_recognition.Recognizer"), \
         patch("cv2.VideoCapture"), \
         patch("threading.Thread"):
        senses = Senses()
        senses.start()
        assert senses.listening is True
        assert senses.seeing is True
        
        senses.stop()
        assert senses.listening is False
        assert senses.seeing is False

def test_get_next_command():
    """Test command queue retrieval."""
    with patch("speech_recognition.Microphone"), \
         patch("speech_recognition.Recognizer"), \
         patch("cv2.VideoCapture"):
        senses = Senses()
        senses.audio_queue.put("hello world")
        assert senses.get_next_command() == "hello world"
        assert senses.get_next_command() is None

def test_get_current_frame():
    """Test frame queue retrieval."""
    with patch("speech_recognition.Microphone"), \
         patch("speech_recognition.Recognizer"), \
         patch("cv2.VideoCapture"):
        senses = Senses()
        senses.vision_queue.put(b"fake_image_data")
        assert senses.get_current_frame() == b"fake_image_data"
        assert senses.get_current_frame() is None

if __name__ == "__main__":
    # fast manual run
    test_senses_initialization()
    test_Start_stop()
    test_get_next_command()
    test_get_current_frame()
    print("All mock tests passed!")
