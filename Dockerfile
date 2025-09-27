FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for lxml, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app /app/app
COPY scheduler /app/scheduler

# Default command is a no-op; we’ll override with docker compose
CMD ["bash", "-lc", "echo 'qtsbook image ready' && sleep infinity"]
