FROM python:3.12-slim

WORKDIR /code

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and web assets.
COPY app/ ./app/
COPY web/ ./web/

# Ensure Python output is flushed immediately.
ENV PYTHONUNBUFFERED=1

# Start the skeleton HTTP server.
# Cloud Run injects PORT; the server reads it via os.environ.get("PORT", "8080").
CMD ["python", "app/skeleton_server.py"]
