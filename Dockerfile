FROM python:3.12-slim

WORKDIR /code

# Install system deps needed by Playwright (Chromium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libx11-xcb1 \
    libxcb-dri3-0 libxshmfence1 libgl1 wget ca-certificates fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser.
RUN playwright install chromium

# Copy all application code and assets.
COPY app/ ./app/
COPY web/ ./web/
COPY pipeline/ ./pipeline/
COPY utils/ ./utils/
COPY contract/ ./contract/

# Ensure Python output is flushed immediately.
ENV PYTHONUNBUFFERED=1

# Start the skeleton HTTP server.
# Cloud Run injects PORT; the server reads it via os.environ.get("PORT", "8080").
CMD ["python", "app/skeleton_server.py"]
