#!/usr/bin/env bash
# Build script for Render.com deployment
# Downloads static ffmpeg binary since apt-get is not available

set -e

echo "=== Installing FFmpeg for video encoding ==="

# Use current directory for bin
BIN_DIR="$PWD/bin"
mkdir -p "$BIN_DIR"

echo "Downloading static ffmpeg binary..."
wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O "$BIN_DIR/ffmpeg.tar.xz"

echo "Extracting ffmpeg..."
cd "$BIN_DIR"
tar xf ffmpeg.tar.xz --strip-components=1

# Make executable
chmod +x ffmpeg ffprobe

# Clean up
rm ffmpeg.tar.xz

echo "=== FFmpeg installed successfully ==="
./ffmpeg -version | head -1
