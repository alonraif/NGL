FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including performance tools and libmagic for file validation
RUN apt-get update && apt-get install -y \
    tar \
    gzip \
    bzip2 \
    pbzip2 \
    pigz \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads temp

EXPOSE 5000

CMD ["python", "app.py"]
