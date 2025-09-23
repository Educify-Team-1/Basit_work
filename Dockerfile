FROM python:3.11-slim
WORKDIR /app
# Install system dependencies (added curl for health check)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --timeout=1000 --retries=5 --no-cache-dir -r requirements.txt   
    # Create necessary directories
RUN mkdir -p /app/models /app/data
# Copy application code
COPY app.py matcher.py training.py dataset_generator.py ./
COPY models/ ./models/
COPY data/ ./data/
# Expose port
EXPOSE 8000
# Health check (now curl is available)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]