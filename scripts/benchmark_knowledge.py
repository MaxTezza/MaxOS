import time
import os
import sys
from unittest.mock import MagicMock

# Mock out missing dependencies
sys.modules['structlog'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['watchdog'] = MagicMock()
sys.modules['watchdog.observers'] = MagicMock()
sys.modules['watchdog.events'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['anthropic'] = MagicMock()
sys.modules['yaml'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['googlesearch'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['mss'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['feedparser'] = MagicMock()
sys.modules['wikipedia'] = MagicMock()
sys.modules['yfinance'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['fakeredis'] = MagicMock()
sys.modules['aiofiles'] = MagicMock()
sys.modules['fastapi'] = MagicMock()
sys.modules['uvicorn'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['scikit-learn'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['SpeechRecognition'] = MagicMock()
sys.modules['aioconsole'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['click'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()
sys.modules['sklearn.metrics.pairwise'] = MagicMock()
sys.modules['aiofiles'] = MagicMock()

from pathlib import Path
from max_os.agents.knowledge import KnowledgeAgent
import tempfile
import uuid

# Create dummy knowledge base
test_kb_dir = tempfile.mkdtemp()

for i in range(500):
    with open(f"{test_kb_dir}/file_{i}.txt", "w") as f:
        f.write("Line 1\nLine 2\nLine 3\n" * 100)
        if i == 250 or i == 300 or i == 400:
            f.write("This is the magic keyword!\nLine after\nAnother line after\n")
        f.write("Line X\nLine Y\nLine Z\n" * 100)

agent = KnowledgeAgent({"knowledge_base_path": test_kb_dir})

start = time.time()
res = agent._retrieve_relevant_content("magic keyword")
end = time.time()

print(f"Baseline Time taken: {end - start:.4f}s")

# Cleanup
import shutil
shutil.rmtree(test_kb_dir)
