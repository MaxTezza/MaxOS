import tempfile
import time
from pathlib import Path
import os
import shutil

def old_retrieval(file_path, query):
    query_lower = query.lower()
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if query_lower in content.lower():
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start_i = max(0, i - 2)
                    end_i = min(len(lines), i + 3)
                    return "\n".join(lines[start_i:end_i])
    except Exception:
        pass
    return None

def new_retrieval(file_path, query):
    query_lower = query.lower()
    chunk_size = 1024 * 1024  # 1 MB
    overlap = max(1024, len(query) * 2)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            buffer = ""
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buffer += chunk
                if query_lower in buffer.lower():
                    extra = f.read(4096)
                    if extra:
                        buffer += extra
                    lines = buffer.splitlines()
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            start_i = max(0, i - 2)
                            end_i = min(len(lines), i + 3)
                            return "\n".join(lines[start_i:end_i])
                    break  # Keep searching if not perfectly matched in lines
                if len(buffer) > overlap:
                    buffer = buffer[-overlap:]
    except Exception:
        pass
    return None

# Create a big file
temp_dir = tempfile.mkdtemp()
file_path = Path(temp_dir) / "big_file.txt"

content = "Line 1\nLine 2\nLine 3\n" * 1000000
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
    f.write("This is the magic keyword!\nLine after\nAnother line after\n")
    f.write(content)

query = "magic keyword"

start = time.time()
res1 = old_retrieval(file_path, query)
end = time.time()
old_time = end - start
print(f"Old Time taken: {old_time:.4f}s")

start = time.time()
res2 = new_retrieval(file_path, query)
end = time.time()
new_time = end - start
print(f"New Time taken: {new_time:.4f}s")

print(f"Match: {res1 == res2}")
print(f"Improvement: {old_time / new_time:.2f}x faster")

shutil.rmtree(temp_dir)
