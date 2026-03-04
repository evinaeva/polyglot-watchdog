FROM python:3.12-slim

WORKDIR /code

# Install system dependencies required by Python packages (e.g. lxml) and clean up apt cache.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies. Requirements are kept minimal and support OCR and Playwright.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the container image
COPY app/ ./app/
COPY utils/ ./utils/
COPY pipeline/ ./pipeline/

# Install Playwright browsers and their native dependencies. This step must run after
# copying the code because `playwright install` downloads large browser binaries.
RUN playwright install --with-deps

# Ensure Python output is flushed immediately
ENV PYTHONUNBUFFERED=1

# Run the deterministic CLI pipeline by default. The pipeline crawls a website,
# performs OCR on screenshots and writes a report to output/issues.json.
CMD ["python", "pipeline/pipeline_runner.py"]
