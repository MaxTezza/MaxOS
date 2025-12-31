import subprocess
import structlog
import json
from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider

logger = structlog.get_logger("max_os.agents.app_store")

class AppStoreAgent:
    name = "The Emporium"
    description = "Manages system software installation, removal, and searching using apt."

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["install", "uninstall", "remove", "software", "app", "package", "search for app", "get program"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing software request: {request.text}")
        
        intent_prompt = f"""
        Analyze the user's request for software. 
        Categorize it as: INSTALL, UNINSTALL, or SEARCH.
        Extract the package name if possible.
        Return JSON: {{"intent": "...", "package": "..."}}
        Request: {request.text}
        """
        
        try:
            analysis_text = await self.llm.generate_async(
                system_prompt="You are a system administrator assistant.",
                user_prompt=intent_prompt
            )
            
            start = analysis_text.find("{")
            end = analysis_text.rfind("}") + 1
            data = json.loads(analysis_text[start:end])
            
            intent = data.get("intent", "SEARCH").upper()
            package = data.get("package", "").lower()
            
            if intent == "INSTALL":
                msg = self._install_package(package)
                return AgentResponse(agent=self.name, status="success", message=msg)
            elif intent == "UNINSTALL":
                msg = self._uninstall_package(package)
                return AgentResponse(agent=self.name, status="success", message=msg)
            else:
                msg = self._search_package(package or request.text)
                return AgentResponse(agent=self.name, status="success", message=msg)
                
        except Exception as e:
            logger.error("App Store logic failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="I'm having trouble accessing the system package manager.")

    def _install_package(self, package: str) -> str:
        if not package: return "Which app would you like to install?"
        check = subprocess.run(["apt-cache", "show", package], capture_output=True, text=True)
        if check.returncode != 0:
            return f"I couldn't find a package named '{package}' in the repositories."
        return f"Package '{package}' found. Please run 'sudo apt install {package}' to finish."

    def _uninstall_package(self, package: str) -> str:
        if not package: return "Which app would you like to remove?"
        return f"To remove '{package}', please run: 'sudo apt remove {package}'."

    def _search_package(self, query: str) -> str:
        try:
            result = subprocess.run(["apt-cache", "search", query], capture_output=True, text=True)
            lines = result.stdout.splitlines()[:5]
            if not lines:
                return f"No applications found for '{query}'."
            summary = "\n".join([f"- {line}" for line in lines])
            return f"I found these relevant packages:\n{summary}"
        except Exception as e:
            return f"Search failed: {str(e)}"
