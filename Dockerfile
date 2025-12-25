FROM python:3.12-slim

# Set working directory
WORKDIR /app

# 1. Install system dependencies required for your specific requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 2. Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# 3. Copy requirements first (Best practice for faster builds)
COPY requirements.txt .

# 4. Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the code
COPY . .

# Koyeb uses 8080 by default for web services
EXPOSE 8080

CMD ["python", "
bot.py"]
