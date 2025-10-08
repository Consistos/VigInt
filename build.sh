#!/usr/bin/env bash
# Build script for Render.com deployment
# Downloads static ffmpeg binary since apt-get is not available

set -e

echo "Downloading static ffmpeg binary for video encoding..."

# Create bin directory in Render's structure
BIN_DIR="/opt/render/project/.render/bin"
mkdir -p $BIN_DIR

# Download static ffmpeg binary from johnvansickle.com (trusted source for static builds)
cd $BIN_DIR
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ffmpeg.tar.xz

# Extract
tar xf ffmpeg.tar.xz --strip-components=1

# Clean up
rm ffmpeg.tar.xz

# Add to PATH
export PATH="$BIN_DIR:$PATH"

echo "FFmpeg installed successfully"
ffmpeg -version

echo "FFmpeg available at: $(which ffmpeg)"
