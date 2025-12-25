"""Google Firestore client for persistent user data."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from google.cloud import firestore
    from google.cloud import storage
except ImportError:  # pragma: no cover - google cloud optional
    firestore = None
    storage = None


class FirestoreClient:
    """Google Firestore client for persistent user data."""

    def __init__(self, project_id: str):
        """Initialize Firestore and Cloud Storage clients.

        Args:
            project_id: Google Cloud project ID

        Raises:
            ImportError: If google-cloud-firestore or google-cloud-storage not installed
        """
        if firestore is None or storage is None:
            raise ImportError(
                "google-cloud-firestore and google-cloud-storage are required. "
                "Install with: pip install google-cloud-firestore google-cloud-storage"
            )

        self.db = firestore.AsyncClient(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        self.bucket_name = f"{project_id}-maxos-storage"

        # Ensure bucket exists
        try:
            self.bucket = self.storage_client.get_bucket(self.bucket_name)
        except Exception:
            self.bucket = self.storage_client.create_bucket(
                self.bucket_name, location="us-central1"
            )

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from Firestore.

        Args:
            user_id: User identifier

        Returns:
            User profile dictionary or None if not found
        """
        doc = await self.db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else None

    async def update_user_profile(self, user_id: str, data: Dict):
        """Update user profile in Firestore.

        Args:
            user_id: User identifier
            data: Profile data to merge
        """
        await self.db.collection("users").document(user_id).set(data, merge=True)

    async def add_conversation(
        self,
        user_id: str,
        voice_input: str,
        vision_context: Optional[Dict] = None,
        gemini_response: str = None,
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None,
    ):
        """Store conversation with multimodal context.

        Args:
            user_id: User identifier
            voice_input: Voice transcription text
            vision_context: Optional vision analysis results
            gemini_response: Optional Gemini response text
            audio_url: Optional Cloud Storage URL for audio
            image_url: Optional Cloud Storage URL for image
        """
        conversation = {
            "timestamp": firestore.SERVER_TIMESTAMP,
            "voice_input": voice_input,
            "vision_context": vision_context,
            "gemini_response": gemini_response,
            "audio_url": audio_url,
            "image_url": image_url,
        }

        await self.db.collection("users").document(user_id).collection(
            "conversations"
        ).add(conversation)

    async def get_conversation_history(
        self, user_id: str, limit: int = 50
    ) -> List[Dict]:
        """Get recent conversation history.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to retrieve

        Returns:
            List of conversation dictionaries, ordered oldest to newest
        """
        conversations = (
            self.db.collection("users")
            .document(user_id)
            .collection("conversations")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )

        results = []
        async for doc in conversations.stream():
            results.append(doc.to_dict())

        return list(reversed(results))

    async def update_pantry(self, user_id: str, items: List[Dict]):
        """Update pantry items.

        Args:
            user_id: User identifier
            items: List of pantry item dictionaries
        """
        await self.db.collection("users").document(user_id).set(
            {"pantry": items}, merge=True
        )

    async def get_pantry(self, user_id: str) -> List[Dict]:
        """Get pantry items.

        Args:
            user_id: User identifier

        Returns:
            List of pantry item dictionaries
        """
        doc = await self.db.collection("users").document(user_id).get()
        if doc.exists:
            return doc.to_dict().get("pantry", [])
        return []

    async def add_pantry_item(
        self,
        user_id: str,
        item: str,
        quantity: float = 1.0,
        image_data: Optional[bytes] = None,
    ):
        """Add item to pantry with optional image.

        Args:
            user_id: User identifier
            item: Item name
            quantity: Item quantity
            image_data: Optional image bytes to upload
        """
        image_url = None
        if image_data:
            image_url = await self.upload_image(
                f"pantry/{user_id}/{item}_{datetime.now().timestamp()}.jpg", image_data
            )

        pantry = await self.get_pantry(user_id)
        pantry.append(
            {
                "item": item,
                "quantity": quantity,
                "added_at": datetime.now().isoformat(),
                "image_url": image_url,
            }
        )
        await self.update_pantry(user_id, pantry)

    async def save_gesture(
        self,
        user_id: str,
        name: str,
        hand_landmarks: List[Dict],
        confidence: float = 1.0,
    ):
        """Save custom gesture training data.

        Args:
            user_id: User identifier
            name: Gesture name
            hand_landmarks: List of hand landmark dictionaries
            confidence: Gesture recognition confidence
        """
        gesture = {
            "name": name,
            "hand_landmarks": hand_landmarks,
            "confidence": confidence,
            "trained_at": firestore.SERVER_TIMESTAMP,
        }

        await self.db.collection("users").document(user_id).collection("gestures").document(
            name
        ).set(gesture)

    async def get_gestures(self, user_id: str) -> List[Dict]:
        """Get all trained gestures.

        Args:
            user_id: User identifier

        Returns:
            List of gesture dictionaries
        """
        gestures = self.db.collection("users").document(user_id).collection("gestures")

        results = []
        async for doc in gestures.stream():
            results.append(doc.to_dict())

        return results

    async def upload_image(self, path: str, image_data: bytes) -> str:
        """Upload image to Cloud Storage and return public URL.

        Args:
            path: Storage path for the image
            image_data: Image bytes

        Returns:
            Public URL of uploaded image
        """
        blob = self.bucket.blob(path)
        blob.upload_from_string(image_data, content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

    async def upload_audio(self, path: str, audio_data: bytes) -> str:
        """Upload audio to Cloud Storage and return public URL.

        Args:
            path: Storage path for the audio
            audio_data: Audio bytes

        Returns:
            Public URL of uploaded audio
        """
        blob = self.bucket.blob(path)
        blob.upload_from_string(audio_data, content_type="audio/wav")
        blob.make_public()
        return blob.public_url

    async def get_audio(self, url: str) -> bytes:
        """Download audio from Cloud Storage.

        Args:
            url: Cloud Storage URL or blob path

        Returns:
            Audio bytes
        """
        blob = self.bucket.blob(url)
        return blob.download_as_bytes()
