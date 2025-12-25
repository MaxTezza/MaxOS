# Firestore + Cloud Storage Setup

## Prerequisites

1. Google Cloud project with billing enabled
2. Firestore in Native mode
3. Cloud Storage API enabled

## Enable APIs

```bash
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
```

## Initialize Firestore

```bash
# Create Firestore database (if not exists)
gcloud firestore databases create --region=us-central1

# Run setup script
python scripts/setup_firestore.py YOUR_PROJECT_ID
```

## Configuration

Update `config/settings.yaml`:

```yaml
storage:
  firestore:
    enabled: true
    project_id: "your-project-id"
    credentials: "/path/to/credentials.json"
```

## Data Model

### User Profile
```
users/{user_id}
  - profile: { name, created_at, preferences }
  - pantry: [{ item, quantity, added_at, image_url }]
```

### Conversations
```
users/{user_id}/conversations/{conversation_id}
  - timestamp
  - voice_input
  - vision_context
  - gemini_response
  - audio_url (Cloud Storage)
  - image_url (Cloud Storage)
```

### Gestures
```
users/{user_id}/gestures/{gesture_name}
  - hand_landmarks
  - confidence
  - trained_at
```

## Cost Estimates

**Light use (100 commands/day):**
- Firestore: $0.50/month (20K reads, 10K writes)
- Cloud Storage: $0.02/month (~1GB)
- **Total: ~$0.52/month**

**Heavy use (1000 commands/day):**
- Firestore: $5/month (200K reads, 100K writes)
- Cloud Storage: $0.20/month (~10GB)
- **Total: ~$5.20/month**

## Offline Mode

Set `offline_mode: true` to use only local storage (Redis + SQLite).
Data will queue for sync when connectivity returns.

## Architecture

MaxOS uses a three-tier storage architecture:

1. **Hot Cache (Redis)**: In-memory cache for active sessions with 1-hour TTL
2. **Local Persistent (SQLite)**: Transaction logs, audit trail, offline fallback
3. **Cloud Persistent (Firestore)**: User profiles, conversation history, cross-device sync
4. **Blob Storage (Cloud Storage)**: Voice recordings, images, videos

This architecture provides:
- Fast access to recent data (Redis)
- Offline capability (SQLite)
- Cross-device sync (Firestore)
- Multimodal support (Cloud Storage)

## Security

- Firestore security rules should be configured to restrict access by user ID
- Cloud Storage objects can be made public or use signed URLs
- Local SQLite database should have appropriate file permissions

## Example Usage

```python
from max_os.storage import StorageManager

# Initialize storage manager
storage = StorageManager(
    redis_url="redis://localhost:6379/0",
    sqlite_path="~/.maxos/maxos.db",
    firestore_project="your-project-id",
    offline_mode=False
)

# Store a conversation
await storage.store_conversation(
    user_id="user123",
    voice_input="What's the weather?",
    gemini_response="The weather is sunny and 72°F.",
    image_data=image_bytes  # Optional
)

# Get conversation history
history = await storage.get_conversation_history("user123", limit=50)
```

## Troubleshooting

### Authentication Errors

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Bucket Already Exists

If you see "409 Conflict", the bucket name is already taken. Bucket names are globally unique.
The setup script will detect this and continue.

### Firestore Quota Exceeded

Free tier limits:
- 50K document reads/day
- 20K document writes/day
- 20K document deletes/day

Monitor usage in the Google Cloud Console.

## Next Steps

- Configure Firestore security rules
- Set up Cloud Storage lifecycle policies for old data
- Implement data export/backup procedures
- Configure monitoring and alerting
