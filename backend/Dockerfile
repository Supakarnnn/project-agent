FROM python:3.13-slim

WORKDIR /app

# ปรับ environment ให้ build และ run ได้ลื่น
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ติดตั้ง dependencies ที่จำเป็นต่อการ build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 1️⃣ ติดตั้ง PyTorch ก่อน (CUDA 12.8 build)
RUN pip install --default-timeout=2000 --no-cache-dir \
    torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu128

# 2️⃣ ติดตั้ง Python dependencies จาก requirements.txt
COPY requirements.txt .
RUN pip install --default-timeout=2000 --no-cache-dir -r requirements.txt

# 3️⃣ คัดลอก source code ทั้งหมด
COPY . .

# เปิดพอร์ต API
EXPOSE 8001

# 4️⃣ คำสั่งรัน FastAPI (Uvicorn)
CMD ["uvicorn", "client:app", "--host", "0.0.0.0", "--port", "8001"]
