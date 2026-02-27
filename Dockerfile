FROM python:3.11-slim

# Instal system dependencies yang dibutuhkan OpenCV dan psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements dulu (supaya cache Docker layer efisien)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi
COPY . .

# Buat folder uploads
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Jalankan aplikasi dengan Gunicorn
# Menggunakan 4 worker untuk concurrency, timeout 120 detik untuk proses biometrik yang berat
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "run:app"]
