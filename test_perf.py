import tempfile
import time
from pathlib import Path
import os
import mmap

# Create a big file
temp_dir = tempfile.mkdtemp()
file_path = Path(temp_dir) / "big_file.txt"

content = "Line 1\nLine 2\nLine 3\n" * 1000000
with open(file_path, "w") as f:
    f.write(content)
    f.write("This is the magic keyword!\nLine after\nAnother line after\n")
    f.write(content)

query = "magic keyword"
query_lower = query.lower()

start = time.time()
content = file_path.read_text(encoding='utf-8')
if query.lower() in content.lower():
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if query.lower() in line.lower():
            start_i = max(0, i - 2)
            end_i = min(len(lines), i + 3)
            res1 = "\n".join(lines[start_i:end_i])
            break
end = time.time()
print(f"Old Time taken: {end - start:.4f}s")

start = time.time()
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    chunk_size = 1024 * 1024
    overlap = max(1024, len(query) * 2)
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
                    res2 = "\n".join(lines[start_i:end_i])
                    break
            break
        if len(buffer) > overlap:
            buffer = buffer[-overlap:]
end = time.time()
print(f"Chunked Time taken: {end - start:.4f}s")

start = time.time()
with open(file_path, "rb") as f:
    # mmap it
    if os.fstat(f.fileno()).st_size > 0:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            # mmap doesn't have lower(), so chunk read it
            chunk_size = 1024 * 1024
            overlap = max(1024, len(query) * 2)
            buffer = b""
            mm.seek(0)
            while True:
                chunk = mm.read(chunk_size)
                if not chunk:
                    break
                buffer += chunk
                if query_lower.encode('utf-8') in buffer.lower():
                    extra = mm.read(4096)
                    if extra:
                        buffer += extra
                    text_buffer = buffer.decode('utf-8', errors='ignore')
                    lines = text_buffer.splitlines()
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            start_i = max(0, i - 2)
                            end_i = min(len(lines), i + 3)
                            res3 = "\n".join(lines[start_i:end_i])
                            break
                    break
                if len(buffer) > overlap:
                    buffer = buffer[-overlap:]
end = time.time()
print(f"mmap Chunked Time taken: {end - start:.4f}s")

print(res1 == res2 == res3)

import shutil
shutil.rmtree(temp_dir)
