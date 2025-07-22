FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy shared modules first (when building from monorepo root)
COPY shared/ /app/shared/

# Copy service-specific requirements and install
COPY services/crew-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/crew-api/src/ /app/src/
COPY services/crew-api/main.py .

# Create directories for generated crews
RUN mkdir -p src/crews/generated

# Set Python path to include shared modules
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Start the application
CMD ["python", "main.py"]
