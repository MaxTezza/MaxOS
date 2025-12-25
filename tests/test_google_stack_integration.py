"""Integration tests for full Google AI stack."""

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_google_stt_initialization():
    """Test Google Cloud Speech-to-Text initialization."""
    with patch("max_os.interfaces.voice.google_stt.speech_v2"):
        from max_os.interfaces.voice.google_stt import GoogleSTT

        stt = GoogleSTT(project_id="test-project")
        assert stt.language_code == "en-US"
        assert stt.model == "chirp-2"
        assert stt.project_id == "test-project"


@pytest.mark.asyncio
async def test_google_stt_streaming():
    """Test Google Cloud Speech-to-Text streaming."""
    with (
        patch("max_os.interfaces.voice.google_stt.speech_v2") as mock_speech,
        patch("max_os.interfaces.voice.google_stt.Duration"),
    ):
        from max_os.interfaces.voice.google_stt import GoogleSTT

        # Mock streaming response
        mock_result = Mock()
        mock_result.is_final = True
        mock_result.alternatives = [Mock(transcript="hello world")]

        mock_response = Mock()
        mock_response.results = [mock_result]

        # Create an async generator for the mock response
        async def mock_stream(*args, **kwargs):
            yield mock_response

        mock_client = AsyncMock()
        mock_client.streaming_recognize = mock_stream
        mock_speech.SpeechAsyncClient.return_value = mock_client

        stt = GoogleSTT(project_id="test-project")
        results = []

        async def dummy_audio_stream():
            yield b"audio data"

        async for transcript in stt.stream_recognize(dummy_audio_stream()):
            results.append(transcript)
            break

        assert results[0] == "hello world"


@pytest.mark.asyncio
async def test_google_tts_initialization():
    """Test Google Cloud TTS initialization."""
    with patch("max_os.interfaces.voice.google_tts.texttospeech_v1") as mock_tts:
        from max_os.interfaces.voice.google_tts import GoogleTTS

        # Mock VoiceSelectionParams to return actual values
        mock_voice = Mock()
        mock_voice.name = "en-US-Studio-O"
        mock_voice.language_code = "en-US"
        mock_tts.VoiceSelectionParams.return_value = mock_voice

        tts = GoogleTTS(voice_name="en-US-Studio-O")
        assert tts.voice.name == "en-US-Studio-O"
        assert tts.voice.language_code == "en-US"


@pytest.mark.asyncio
async def test_google_tts_synthesis():
    """Test Google Cloud TTS synthesis."""
    with patch("max_os.interfaces.voice.google_tts.texttospeech_v1") as mock_tts:
        from max_os.interfaces.voice.google_tts import GoogleTTS

        # Mock synthesis response
        mock_response = Mock()
        mock_response.audio_content = b"fake audio data"

        mock_client = AsyncMock()
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)
        mock_tts.TextToSpeechAsyncClient.return_value = mock_client

        tts = GoogleTTS()
        audio = await tts.synthesize("Hello world")

        assert audio == b"fake audio data"


@pytest.mark.asyncio
async def test_google_tts_emotion():
    """Test Google Cloud TTS emotion synthesis."""
    with patch("max_os.interfaces.voice.google_tts.texttospeech_v1") as mock_tts:
        from max_os.interfaces.voice.google_tts import GoogleTTS

        # Mock synthesis response
        mock_response = Mock()
        mock_response.audio_content = b"emotional audio data"

        mock_client = AsyncMock()
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)
        mock_tts.TextToSpeechAsyncClient.return_value = mock_client

        tts = GoogleTTS()
        audio = await tts.synthesize_with_emotion("I'm excited!", emotion="excited")

        assert audio == b"emotional audio data"


def test_mediapipe_initialization():
    """Test MediaPipe tracker initialization."""
    with (
        patch("max_os.interfaces.vision.mediapipe_tracker.mp") as mock_mp,
        patch("max_os.interfaces.vision.mediapipe_tracker.cv2"),
        patch("max_os.interfaces.vision.mediapipe_tracker.np"),
    ):
        from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker

        mock_holistic = Mock()
        mock_mp.solutions.holistic.Holistic.return_value = mock_holistic

        tracker = MediaPipeTracker()
        assert tracker.holistic == mock_holistic


def test_mediapipe_hand_tracking():
    """Test MediaPipe hand tracking."""
    with (
        patch("max_os.interfaces.vision.mediapipe_tracker.mp") as mock_mp,
        patch("max_os.interfaces.vision.mediapipe_tracker.cv2") as mock_cv2,
        patch("max_os.interfaces.vision.mediapipe_tracker.np") as mock_np,
    ):
        from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker

        # Mock numpy array
        mock_np.zeros = Mock(return_value=Mock())

        # Mock cv2
        mock_cv2.cvtColor = Mock(return_value=Mock())
        mock_cv2.COLOR_BGR2RGB = 0
        mock_cv2.COLOR_RGB2BGR = 1

        # Mock MediaPipe results
        mock_results = Mock()
        mock_results.face_landmarks = None
        mock_results.pose_landmarks = None
        mock_results.left_hand_landmarks = None
        mock_results.right_hand_landmarks = None

        mock_holistic = Mock()
        mock_holistic.process = Mock(return_value=mock_results)
        mock_mp.solutions.holistic.Holistic.return_value = mock_holistic

        tracker = MediaPipeTracker()
        fake_frame = Mock()
        fake_frame.flags = Mock()

        results = tracker.process_frame(fake_frame)

        assert "face_landmarks" in results
        assert "left_hand_landmarks" in results
        assert "right_hand_landmarks" in results
        assert "gestures" in results
        assert "eye_gaze" in results


def test_mediapipe_gesture_detection():
    """Test MediaPipe gesture detection."""
    with (
        patch("max_os.interfaces.vision.mediapipe_tracker.mp") as mock_mp,
        patch("max_os.interfaces.vision.mediapipe_tracker.cv2"),
        patch("max_os.interfaces.vision.mediapipe_tracker.np"),
    ):
        from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker

        mock_holistic = Mock()
        mock_mp.solutions.holistic.Holistic.return_value = mock_holistic

        tracker = MediaPipeTracker()

        # Mock hand landmarks for fist (all fingers closed)
        mock_hand = Mock()
        mock_landmarks = []
        for i in range(21):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = 0.5 if i in [4, 8, 12, 16, 20] else 0.4
            mock_landmarks.append(landmark)
        mock_hand.landmark = mock_landmarks

        gesture = tracker._classify_hand_gesture(mock_hand)
        assert gesture in ["fist", "open_palm", "pointing", "peace_sign", "thumbs_up", None]


@pytest.mark.asyncio
async def test_multimodal_controller_initialization():
    """Test multimodal controller initialization."""
    with (
        patch("max_os.interfaces.multimodal_controller.cv2") as mock_cv2,
        patch("max_os.interfaces.voice.google_stt.speech_v2"),
        patch("max_os.interfaces.voice.google_stt.Duration"),
        patch("max_os.interfaces.voice.google_tts.texttospeech_v1"),
        patch("max_os.interfaces.vision.mediapipe_tracker.mp"),
        patch("max_os.interfaces.vision.mediapipe_tracker.cv2"),
        patch("max_os.interfaces.vision.mediapipe_tracker.np"),
        patch("max_os.core.gemini_client.genai") as mock_genai,
        patch("max_os.core.gemini_client.Image"),
        patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
    ):
        from max_os.interfaces.multimodal_controller import MultimodalController

        # Mock VideoCapture
        mock_capture = Mock()
        mock_cv2.VideoCapture.return_value = mock_capture

        # Mock genai configure
        mock_genai.configure = Mock()
        mock_genai.GenerativeModel.return_value = Mock()

        controller = MultimodalController()

        assert controller.stt is not None
        assert controller.tts is not None
        assert controller.vision is not None
        assert controller.gemini is not None
        assert controller.camera == mock_capture
        assert controller.wake_word == "hey max"


@pytest.mark.asyncio
async def test_gemini_multimodal_text_only():
    """Test Gemini client with text only."""
    with (
        patch("max_os.core.gemini_client.genai") as mock_genai,
        patch("max_os.core.gemini_client.Image"),
    ):
        from max_os.core.gemini_client import GeminiClient

        # Mock model response
        mock_response = Mock()
        mock_response.text = "Hello! I'm Gemini."

        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = Mock()

        client = GeminiClient(api_key="test-api-key")
        response = await client.process(text="Hello!")

        assert response == "Hello! I'm Gemini."


@pytest.mark.asyncio
async def test_gemini_multimodal_with_image():
    """Test Gemini client with text and image."""
    with (
        patch("max_os.core.gemini_client.genai") as mock_genai,
        patch("max_os.core.gemini_client.Image") as mock_image_module,
    ):
        from max_os.core.gemini_client import GeminiClient

        # Mock PIL Image
        mock_img = Mock()
        mock_image_module.open.return_value = mock_img

        # Mock model response
        mock_response = Mock()
        mock_response.text = "I see a cat in the image."

        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = Mock()

        client = GeminiClient(api_key="test-api-key")
        response = await client.process(text="What's in this image?", image="cat.jpg")

        assert response == "I see a cat in the image."


def test_missing_dependencies_google_stt():
    """Test GoogleSTT with missing dependencies."""
    with patch("max_os.interfaces.voice.google_stt.speech_v2", None):
        from max_os.interfaces.voice.google_stt import GoogleSTT

        with pytest.raises(RuntimeError, match="google-cloud-speech package not installed"):
            GoogleSTT()


def test_missing_dependencies_google_tts():
    """Test GoogleTTS with missing dependencies."""
    with patch("max_os.interfaces.voice.google_tts.texttospeech_v1", None):
        from max_os.interfaces.voice.google_tts import GoogleTTS

        with pytest.raises(RuntimeError, match="google-cloud-texttospeech package not installed"):
            GoogleTTS()


def test_missing_dependencies_mediapipe():
    """Test MediaPipe with missing dependencies."""
    with patch("max_os.interfaces.vision.mediapipe_tracker.mp", None):
        from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker

        with pytest.raises(RuntimeError, match="mediapipe"):
            MediaPipeTracker()
