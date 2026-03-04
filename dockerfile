FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Cloud Run requires PORT
ENV PORT=8080

WORKDIR /app

# Install system deps required for Playwright and OCR tooling
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy repo
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (required for screenshot stage)
RUN pip install playwright && playwright install --with-deps chromium

# Default command
CMD ["python", "pipeline/pipeline_runner.py"]
