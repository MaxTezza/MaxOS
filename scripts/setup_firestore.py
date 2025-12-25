"""Initialize Firestore collections and Cloud Storage bucket."""

from __future__ import annotations

import sys

try:
    from google.cloud import firestore
    from google.cloud import storage
except ImportError:
    print("Error: google-cloud-firestore and google-cloud-storage are required.")
    print("Install with: pip install google-cloud-firestore google-cloud-storage")
    sys.exit(1)


def setup_firestore(project_id: str):
    """Create Firestore collections with indexes.

    Args:
        project_id: Google Cloud project ID
    """
    db = firestore.Client(project=project_id)

    # Create sample user document to initialize collection
    db.collection("users").document("_init").set(
        {"created_at": firestore.SERVER_TIMESTAMP, "initialized": True}
    )

    print(f"✅ Firestore initialized for project: {project_id}")


def setup_cloud_storage(project_id: str):
    """Create Cloud Storage bucket.

    Args:
        project_id: Google Cloud project ID
    """
    storage_client = storage.Client(project=project_id)
    bucket_name = f"{project_id}-maxos-storage"

    try:
        bucket = storage_client.create_bucket(bucket_name, location="us-central1")
        print(f"✅ Cloud Storage bucket created: {bucket_name}")
    except Exception as e:
        # Bucket likely already exists
        error_str = str(e)
        if "409" in error_str or "already exists" in error_str.lower():
            print(f"✅ Cloud Storage bucket already exists: {bucket_name}")
        else:
            raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python setup_firestore.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    setup_firestore(project_id)
    setup_cloud_storage(project_id)
    print("\n🎉 Firestore and Cloud Storage ready!")
