FROM python:3.12-slim

# Install the "Build Essentials" that most bot scripts need
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
