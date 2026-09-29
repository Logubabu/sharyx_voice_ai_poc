# Stage 1: Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    libportaudio2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into a wheels/virtual env directory to copy over
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Final runtime image
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only (e.g. ffmpeg and required shared libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libasound2 \
    libportaudio2 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/share/doc -depth -type f ! -name copyright -delete \
    && find /usr/share/doc -empty -delete \
    && rm -rf /usr/share/man /usr/share/groff /usr/share/info /usr/share/lintian /usr/share/linda /var/cache/man

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

EXPOSE 8000

CMD ["python", "-m", "app.main"]

