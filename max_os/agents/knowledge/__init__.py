"Knowledge agent for RAG (Retrieval-Augmented Generation) capabilities."

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from max_os.agents.base import AgentRequest, AgentResponse
from max_os.utils.llm_api import LLMAPI


class KnowledgeAgent:
    name = "knowledge"
    description = "Retrieves information from documents and generates answers."
    capabilities = ["retrieve", "generate", "summarize", "answer_questions"]
    KEYWORDS: Iterable[str] = (
        "know",
        "information",
        "docs",
        "documentation",
        "answer",
        "explain",
        "summarize",
        "find out",
    )

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or {}
        self.llm_api = LLMAPI()  # Initialize LLM API client
        self.knowledge_base_path = Path(
            self.config.get("knowledge_base_path", Path.cwd())
        )  # Set to current working directory (ai-os root)
        if not self.knowledge_base_path.is_absolute():
            self.knowledge_base_path = Path.cwd() / self.knowledge_base_path

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("knowledge.")

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text_lower = request.text.lower()

        if any(word in text_lower for word in ["summarize", "explain"]):
            return await self._handle_summarize_or_explain(request)
        elif any(word in text_lower for word in ["find", "search", "answer"]):
            return await self._handle_search_and_answer(request)
        else:
            return await self._handle_search_and_answer(request)  # Default behavior

    async def _handle_summarize_or_explain(self, request: AgentRequest) -> AgentResponse:
        # Extract file path from the request text
        file_path_str = None
        for keyword in ["summarize", "explain"]:
            if keyword in request.text.lower():  # Use lower() for keyword matching
                # Assuming the file path follows the keyword
                parts = request.text.split(keyword, 1)  # Use original text for splitting
                if len(parts) > 1:
                    file_path_str = parts[1].strip()
                    break

        if not file_path_str:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Could not identify file to summarize/explain.",
                payload={"request": request.text},
            )

        file_path = Path(file_path_str)
        if not file_path.is_absolute():
            file_path = self.knowledge_base_path / file_path

        if not file_path.exists():
            return AgentResponse(
                agent=self.name,
                status="not_found",
                message=f"File not found: {file_path}",
                payload={"file_path": str(file_path)},
            )

        if not file_path.is_file():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path is not a file: {file_path}",
                payload={"file_path": str(file_path)},
            )

        try:
            content = file_path.read_text()
            prompt = f"Summarize and explain the following content:\n\n{content}"
            response_text = await self.llm_api.generate_text(prompt)
            return AgentResponse(
                agent=self.name,
                status="success",
                message=response_text,
                payload={"file_path": str(file_path), "summary": response_text[:200]},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to summarize/explain file: {str(e)}",
                payload={"file_path": str(file_path), "error": str(e)},
            )

    async def _handle_search_and_answer(self, request: AgentRequest) -> AgentResponse:
        query = request.text
        retrieved_content = self._retrieve_relevant_content(query)

        if not retrieved_content:
            return AgentResponse(
                agent=self.name,
                status="not_found",
                message="Could not find relevant information in the knowledge base.",
                payload={"query": query},
            )

        # Augment the prompt with retrieved content
        augmented_prompt = (
            f"Based on the following context, answer the question:\n\n"
            f"Context:\n{retrieved_content}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

        try:
            # Generate response using LLM
            response_text = await self.llm_api.generate_text(augmented_prompt)
            return AgentResponse(
                agent=self.name,
                status="success",
                message=response_text,
                payload={"query": query, "retrieved_content": retrieved_content},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to generate response: {str(e)}",
                payload={"query": query, "error": str(e)},
            )

    def _retrieve_relevant_content(self, query: str) -> str:
        """
        A simple retrieval mechanism: searches for query keywords in files
        within the knowledge base path.
        """
        relevant_chunks = []
        for root, _, files in os.walk(self.knowledge_base_path):
            for file_name in files:
                file_path = Path(root) / file_name
                try:
                    content = file_path.read_text()
                    if query.lower() in content.lower():
                        # Simple chunking: take a few lines around the keyword
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                relevant_chunks.append("\n".join(lines[start:end]))
                                break  # Only one chunk per file for simplicity
                except Exception:
                    # Ignore unreadable files
                    pass
        return "\n---\n".join(relevant_chunks[:3])  # Limit to 3 relevant chunks
