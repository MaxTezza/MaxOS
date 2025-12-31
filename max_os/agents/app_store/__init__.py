import subprocess
import structlog
from typing import Optional, List
from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider

logger = structlog.get_logger("max_os.agents.app_store")

class AppStoreAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "The Emporium"
        self.description = "Manages system software installation, removal, and searching using apt."

    def can_handle(self, user_input: str) -> bool:
        keywords = ["install", "uninstall", "remove", "software", "app", "package", "search for app", "get program"]
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing software request: {user_input}")
        
        # 1. Determine Intent (Install, Uninstall, Search)
        intent_prompt = f"""
        Analyze the user's request for software. 
        Categorize it as: INSTALL, UNINSTALL, or SEARCH.
        Extract the package name if possible.
        Return JSON: {{"intent": "...", "package": "..."}}
        Request: {user_input}
        """
        
        try:
            analysis_text = await self.llm.generate(
                system_prompt="You are a system administrator assistant.",
                user_prompt=intent_prompt
            )
            
            # Simple JSON extraction
            import json
            start = analysis_text.find("{")
            end = analysis_text.rfind("}") + 1
            data = json.loads(analysis_text[start:end])
            
            intent = data.get("intent", "SEARCH").upper()
            package = data.get("package", "").lower()
            
            if intent == "INSTALL":
                return self._install_package(package)
            elif intent == "UNINSTALL":
                return self._uninstall_package(package)
            else:
                return self._search_package(package or user_input)
                
        except Exception as e:
            logger.error("App Store logic failed", error=str(e))
            return "I'm having trouble accessing the system package manager."

    def _install_package(self, package: str) -> str:
        if not package: return "Which app would you like to install?"
        
        # SAFETY: We don't actually run sudo apt install without real user confirmation 
        # In a real OS, this would trigger a GUI popup or a specific Reflex.
        # For now, we simulate the command check.
        
        logger.info(f"Initiating installation of {package}")
        # Check if it exists
        check = subprocess.run(["apt-cache", "show", package], capture_output=True, text=True)
        if check.returncode != 0:
            return f"I couldn't find a package named '{package}' in the repositories."

        return f"Package '{package}' found. Since I require root privileges for this, please run 'sudo apt install {package}' in your terminal. I've prepared the environment."

    def _uninstall_package(self, package: str) -> str:
        if not package: return "Which app would you like to remove?"
        return f"To remove '{package}', please authorize the command: 'sudo apt remove {package}'."

    def _search_package(self, query: str) -> str:
        logger.info(f"Searching for: {query}")
        try:
            # Get top 3 results
            result = subprocess.run(["apt-cache", "search", query], capture_output=True, text=True)
            lines = result.stdout.splitlines()[:5]
            if not lines:
                return f"No applications found for '{query}'."
            
            summary = "\n".join([f"- {line}" for line in lines])
            return f"I found these relevant packages:\n{summary}"
        except Exception as e:
            return f"Search failed: {str(e)}"
