# Google AI Stack Setup for MaxOS

Complete guide for setting up MaxOS with Google's full AI ecosystem: Gemini, Cloud Speech-to-Text, Cloud Text-to-Speech, and MediaPipe.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Google Cloud Setup](#google-cloud-setup)
- [Gemini API Setup](#gemini-api-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Testing](#testing)
- [Cost Estimates](#cost-estimates)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Python 3.10 or higher
- Webcam (for MediaPipe vision features)
- Microphone (optional, for voice features)
- Internet connection (for Google Cloud APIs)

### Accounts Needed

1. **Google Cloud Account** - For Speech-to-Text and Text-to-Speech
2. **Google AI Studio Account** - For Gemini API key

## Google Cloud Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Create Project"
3. Enter a project name (e.g., "maxos-ai")
4. Note your Project ID

### 2. Enable Required APIs

```bash
# Install gcloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable vision.googleapis.com  # Optional
```

### 3. Create Service Account & Credentials

```bash
# Create service account
gcloud iam service-accounts create maxos-sa \
    --display-name="MaxOS Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:maxos-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:maxos-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/texttospeech.client"

# Download credentials
gcloud iam service-accounts keys create ~/maxos-credentials.json \
    --iam-account=maxos-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 4. Set Environment Variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/maxos-credentials.json"
```

Then reload:

```bash
source ~/.bashrc  # or ~/.zshrc
```

## Gemini API Setup

### 1. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the API key

### 2. Set Environment Variable

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
```

Then reload:

```bash
source ~/.bashrc  # or ~/.zshrc
```

## Installation

### Option 1: Install from Source

```bash
# Clone the repository
git clone https://github.com/MaxTezza/MaxOS.git
cd MaxOS

# Install with Google AI stack extras
pip install -e ".[google]"
```

### Option 2: Install from PyPI (when available)

```bash
pip install "maxos[google]"
```

### Verify Installation

```bash
python -c "import max_os; from max_os.interfaces.voice.google_stt import GoogleSTT; print('✅ Installation successful!')"
```

## Configuration

### 1. Copy Example Configuration

```bash
cp config/settings.example.yaml config/settings.yaml
```

### 2. Update Configuration

Edit `config/settings.yaml`:

```yaml
llm:
  google_api_key: "your-gemini-api-key"  # Or use GOOGLE_API_KEY env var

voice:
  input:
    provider: google_cloud
    model: chirp-2
    language: en-US
    streaming: true
    google_cloud_project: "your-project-id"
    credentials: "/path/to/credentials.json"
  
  output:
    provider: google_cloud
    voice: en-US-Studio-O
    speaking_rate: 1.0
    pitch: 0.0
    google_cloud_project: "your-project-id"
    credentials: "/path/to/credentials.json"
  
  wake_word: "hey max"

vision:
  provider: mediapipe
  enable_hand_tracking: true
  enable_face_tracking: true
  enable_eye_gaze: true
  camera_index: 0

multimodal:
  enabled: true
  gemini_model: gemini-2.0-flash
  combine_voice_and_vision: true
```

## Testing

### Test Individual Components

#### 1. Test Gemini

```bash
python -c "
from max_os.core.gemini_client import GeminiClient
import asyncio

async def test():
    client = GeminiClient(model='gemini-2.0-flash')
    response = await client.process(text='Hello! Introduce yourself.')
    print(response)

asyncio.run(test())
"
```

#### 2. Test Speech-to-Text

```bash
python examples/test_google_stt.py
```

#### 3. Test Text-to-Speech

```bash
python examples/test_google_tts.py
```

#### 4. Test MediaPipe

```bash
python examples/test_mediapipe.py
```

### Run Full Demo

```bash
python examples/full_google_stack_demo.py
```

## Cost Estimates

### Free Tier (Monthly)

- **Gemini API**: First 1,500 requests/day FREE
- **Speech-to-Text**: First 60 minutes FREE
- **Text-to-Speech**: First 1M characters FREE (Standard), 100K (Studio)
- **MediaPipe**: FREE (runs locally)

### Light Usage (~100 commands/day)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| Gemini 2.0 Flash | ~3,000 requests | ~$0.50 |
| Speech-to-Text (Chirp 2) | ~30 hours | ~$2.00 |
| Text-to-Speech (Studio) | ~50K chars | ~$5.00 |
| MediaPipe | Unlimited | FREE |
| **Total** | | **~$7.50** |

### Heavy Usage (~1,000 commands/day)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| Gemini 2.0 Flash | ~30,000 requests | ~$5.00 |
| Speech-to-Text (Chirp 2) | ~300 hours | ~$20.00 |
| Text-to-Speech (Studio) | ~500K chars | ~$50.00 |
| MediaPipe | Unlimited | FREE |
| **Total** | | **~$75.00** |

**Note**: Still 10-100x cheaper than OpenAI GPT-4 equivalent!

### Pricing Details

- **Gemini 2.0 Flash**: $0.00015/1K tokens (input), $0.0006/1K tokens (output)
- **Speech-to-Text (Chirp 2)**: $0.006/15 seconds (standard)
- **Text-to-Speech (Studio)**: $16/1M characters
- **MediaPipe**: Free (local processing)

Latest pricing: https://cloud.google.com/pricing

## Troubleshooting

### Common Issues

#### 1. "google-cloud-speech not found"

```bash
pip install "maxos[google]"
```

#### 2. "Could not load credentials"

Make sure you've set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

Verify the file exists:

```bash
ls -l $GOOGLE_APPLICATION_CREDENTIALS
```

#### 3. "API not enabled"

Enable the required APIs:

```bash
gcloud services enable speech.googleapis.com texttospeech.googleapis.com
```

#### 4. "Permission denied" errors

Grant the service account proper roles:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:maxos-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"
```

#### 5. Camera not working

Check available cameras:

```bash
python -c "import cv2; print([i for i in range(10) if cv2.VideoCapture(i).isOpened()])"
```

Try different camera indices in configuration:

```yaml
vision:
  camera_index: 0  # Try 0, 1, 2, etc.
```

#### 6. MediaPipe not detecting hands

- Ensure good lighting
- Keep hands visible in frame
- Adjust detection confidence:

```python
tracker = MediaPipeTracker(
    min_detection_confidence=0.3,  # Lower threshold
    min_tracking_confidence=0.3
)
```

### Getting Help

- **GitHub Issues**: https://github.com/MaxTezza/MaxOS/issues
- **Google Cloud Support**: https://cloud.google.com/support
- **MediaPipe Docs**: https://developers.google.com/mediapipe

## Advanced Configuration

### Custom Gestures

Create `config/custom_gestures.yaml`:

```yaml
gestures:
  - name: "swipe_left"
    description: "Navigate back"
    landmarks: [...]
  
  - name: "swipe_right"
    description: "Navigate forward"
    landmarks: [...]
```

### Voice Settings

Fine-tune voice recognition:

```yaml
voice:
  input:
    sensitivity: 0.5  # Wake word sensitivity
    vad_threshold: 0.3  # Voice activity detection
    max_alternatives: 3  # Alternative transcriptions
  
  output:
    speaking_rate: 1.2  # Faster speech
    pitch: +2  # Higher pitch
    volume_gain_db: 0  # Volume adjustment
```

### Vision Settings

Optimize vision tracking:

```yaml
vision:
  model_complexity: 2  # 0=lite, 1=full, 2=heavy
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5
  smooth_landmarks: true
  refine_face_landmarks: true
```

## Next Steps

1. **Run the demo**: `python examples/full_google_stack_demo.py`
2. **Customize gestures**: Create your own gesture library
3. **Integrate with MaxOS**: Connect to filesystem/system agents
4. **Build applications**: Use the multimodal API for your projects

## Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Cloud Speech-to-Text Docs](https://cloud.google.com/speech-to-text/docs)
- [Cloud Text-to-Speech Docs](https://cloud.google.com/text-to-speech/docs)
- [MediaPipe Documentation](https://developers.google.com/mediapipe)
- [MaxOS Documentation](../README.md)
