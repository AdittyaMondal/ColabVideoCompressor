# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /bot

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    pv \
    jq \
    python3-dev \
    ffmpeg \
    mediainfo \
    nvidia-utils-525 \
    && rm -rf /var/lib/apt/lists/*

# Install additional GPU tools
RUN apt-get update && apt-get install -y \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p downloads encode thumb \
    && chmod 777 downloads encode thumb

# Set environment variable for GPU support
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility,video

# Run the bot
CMD ["bash", "run.sh"]

# Labels
LABEL maintainer="Your Name <your.email@example.com>"
LABEL version="2.0"
LABEL description="Enhanced Video Compressor Bot with GPU Acceleration"
