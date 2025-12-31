# MaxOS V3 - Docker Distribution
# Multi-stage build for a portable AI-OS environment.

# --- Stage 1: Build the Frontend ---
FROM node:18-slim AS gui-build
WORKDIR /app/max_os/interfaces/gui
COPY max_os/interfaces/gui/package*.json ./
RUN npm install
COPY max_os/interfaces/gui/ ./
RUN npm run build

# --- Stage 2: Final Image ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    xdotool \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy Backend Code
COPY max_os/ ./max_os/
COPY .env* ./

# Copy Built Frontend from Stage 1
COPY --from=gui-build /app/max_os/interfaces/gui/dist ./max_os/interfaces/gui/dist

# Expose ports for UI and API
EXPOSE 8000 5173

# Set Environment Variables
ENV PYTHONUNBUFFERED=1

# For Docker, we might want to override how the GUI is served
# But for now, we'll use the default runner
CMD ["python", "-m", "max_os.runner"]
