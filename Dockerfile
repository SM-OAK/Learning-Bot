FROM python:3.10-slim-bullseye

# Ye tools FuzzyWuzzy aur Levenshtein ke liye zaroori hain
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "bot.py"]
