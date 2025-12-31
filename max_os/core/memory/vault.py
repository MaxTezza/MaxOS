"""
The Vault.
Semantic Long-Term Memory using ChromaDB.
Stores interactions and retrieves them based on vector similarity.
"""

import chromadb
import structlog
from typing import List, Optional
import uuid
import time
import os
from datetime import datetime

logger = structlog.get_logger("max_os.core.vault")

class Vault:
    def __init__(self, persist_path: str = "~/.maxos/vault"):
        try:
            self.client = chromadb.PersistentClient(path=os.path.expanduser(persist_path))
            self.collection = self.client.get_or_create_collection(name="memories")
            logger.info("The Vault is Open (ChromaDB)")
            self.enabled = True
        except Exception as e:
            logger.error("Failed to open Vault", error=str(e))
            self.enabled = False

    def add_memory(self, text: str, meta: dict = None):
        """Stores a text memory with metadata."""
        if not self.enabled: return

        if meta is None: meta = {}
        meta["timestamp"] = datetime.now().isoformat()
        
        try:
            self.collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            logger.error("Failed to store memory", error=str(e))

    def recall(self, query: str, n_results: int = 3) -> List[str]:
        """Retrieves relevant memories based on semantic similarity."""
        if not self.enabled: return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            # Flatten results
            if results['documents']:
                 return results['documents'][0]
            return []
        except Exception as e:
            logger.error("Memory retrieval failed", error=str(e))
            return []

    def get_formatted_context(self, query: str) -> str:
        """Returns a string suitable for LLM Context."""
        memories = self.recall(query)
        if not memories:
            return ""
        
        context = "Relevant History:\n" + "\n".join([f"- {m}" for m in memories])
        return context
