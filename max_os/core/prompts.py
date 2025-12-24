"""System prompts and few-shot examples for LLM-powered intent classification."""

from __future__ import annotations


def get_system_prompt() -> str:
    """
    Generate the system prompt for MaxOS intent classification.
    
    Returns:
        System prompt describing capabilities and expected output format.
    """
    return """You are MaxOS, an AI-powered operating system assistant. Your job is to classify user intents and extract entities from natural language commands.

Available intents:
- file.search: Search for files by pattern, size, or date
- file.copy: Copy files from source to destination
- file.move: Move files from source to destination
- file.delete: Delete files (moves to trash)
- file.list: List directory contents
- file.info: Get file/directory information
- file.manage: General file management operations
- file.organize: Organize directories
- file.archive: Archive or compress files
- system.health: Check system resource usage (CPU, memory, disk)
- system.processes: List running processes
- system.service: Manage systemd services
- system.metrics: Collect resource metrics
- system.general: General system requests
- dev.git_status: Show git repository status
- dev.git_commit: Commit changes to git
- dev.scaffold: Scaffold a software project
- dev.deploy: Coordinate deployment
- dev.test: Run developer tests
- network.interfaces: Show network interfaces
- network.ping: Test network connectivity
- network.manage: Manage Wi-Fi connections
- network.vpn: Manage VPN connections
- network.firewall: Adjust firewall
- knowledge.query: Retrieve information from knowledge base
- agent.evolver: Self-improvement workflows

Extract entities like:
- source_path: Source file or directory path
- dest_path: Destination file or directory path
- pattern: Search pattern (e.g., "*.pdf", "*.jpg")
- size_threshold: File size threshold in bytes
- size_operator: Comparison operator for size (greater_than, less_than, equal_to)
- service_name: Name of systemd service
- search_term: General search term
- count: Number of items to show/list

Return ONLY valid JSON in this exact format:
{
  "intent": "intent.name",
  "confidence": 0.95,
  "entities": {
    "entity_name": "entity_value"
  },
  "summary": "Brief description of what the user wants"
}

Confidence scores:
- 0.9-1.0: Very clear, specific intent with all required entities
- 0.7-0.89: Clear intent but missing some optional entities
- 0.5-0.69: Reasonable guess but could be ambiguous
- 0.3-0.49: Low confidence, multiple possible interpretations
- 0.0-0.29: Very unclear or unrecognizable intent

IMPORTANT: Return ONLY the JSON object, no additional text or explanation."""


def get_few_shot_examples() -> list[dict[str, str]]:
    """
    Get few-shot examples for intent classification.
    
    Returns:
        List of example user inputs and expected outputs.
    """
    return [
        {
            "user": "copy Documents/report.pdf to Backup folder",
            "assistant": """{
  "intent": "file.copy",
  "confidence": 0.95,
  "entities": {
    "source_path": "Documents/report.pdf",
    "dest_path": "Backup"
  },
  "summary": "Copy report.pdf from Documents to Backup folder"
}"""
        },
        {
            "user": "search Downloads for .psd files larger than 200MB",
            "assistant": """{
  "intent": "file.search",
  "confidence": 0.92,
  "entities": {
    "pattern": "*.psd",
    "search_path": "Downloads",
    "size_threshold": "200",
    "size_operator": "greater_than",
    "size_unit": "MB"
  },
  "summary": "Search for PSD files larger than 200MB in Downloads"
}"""
        },
        {
            "user": "show system health",
            "assistant": """{
  "intent": "system.health",
  "confidence": 0.98,
  "entities": {},
  "summary": "Check system resource usage including CPU, memory, and disk"
}"""
        },
        {
            "user": "list running processes",
            "assistant": """{
  "intent": "system.processes",
  "confidence": 0.97,
  "entities": {},
  "summary": "List all currently running processes"
}"""
        },
        {
            "user": "check docker service status",
            "assistant": """{
  "intent": "system.service",
  "confidence": 0.95,
  "entities": {
    "service_name": "docker"
  },
  "summary": "Check the status of the docker systemd service"
}"""
        },
        {
            "user": "show git status",
            "assistant": """{
  "intent": "dev.git_status",
  "confidence": 0.98,
  "entities": {},
  "summary": "Show git repository status"
}"""
        },
        {
            "user": "ping google.com",
            "assistant": """{
  "intent": "network.ping",
  "confidence": 0.96,
  "entities": {
    "host": "google.com"
  },
  "summary": "Test network connectivity to google.com"
}"""
        },
        {
            "user": "move old logs to archive",
            "assistant": """{
  "intent": "file.move",
  "confidence": 0.85,
  "entities": {
    "pattern": "*log*",
    "dest_path": "archive"
  },
  "summary": "Move log files to archive directory"
}"""
        },
        {
            "user": "delete temporary files",
            "assistant": """{
  "intent": "file.delete",
  "confidence": 0.88,
  "entities": {
    "pattern": "*temp*"
  },
  "summary": "Delete temporary files"
}"""
        },
        {
            "user": "list files in Documents",
            "assistant": """{
  "intent": "file.list",
  "confidence": 0.96,
  "entities": {
    "path": "Documents"
  },
  "summary": "List contents of Documents directory"
}"""
        },
    ]


def build_llm_prompt(user_input: str, context: dict | None = None) -> str:
    """
    Build the complete prompt for LLM intent classification.
    
    Args:
        user_input: The user's natural language command
        context: Optional context information (e.g., git_status, active_window)
    
    Returns:
        Complete prompt string with system message and few-shot examples
    """
    system_msg = get_system_prompt()
    
    # Add context if available
    context_str = ""
    if context:
        context_items = []
        if context.get("git_status"):
            context_items.append(f"Git status: {context['git_status']}")
        if context.get("active_window"):
            context_items.append(f"Active window: {context['active_window']}")
        if context.get("last_action"):
            context_items.append(f"Last action: {context['last_action']}")
        
        if context_items:
            context_str = "\n\nCurrent context:\n" + "\n".join(context_items)
    
    # Build few-shot examples
    examples = get_few_shot_examples()
    examples_str = "\n\nExamples:\n"
    for i, example in enumerate(examples[:5], 1):  # Use first 5 examples to keep prompt reasonable
        examples_str += f"\nUser: {example['user']}\nAssistant: {example['assistant']}\n"
    
    # Build final prompt
    prompt = f"""{system_msg}{context_str}{examples_str}

Now classify this user input:
User: {user_input}
Assistant:"""
    
    return prompt
