FROM python:3.11-slim

WORKDIR /app

# Install system libraries required by Pillow (JPEG, TIFF, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for uploads and output
RUN mkdir -p uploads web_output

EXPOSE 5000

CMD ["python", "app.py"]
