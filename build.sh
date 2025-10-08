#!/usr/bin/env bash
# Build script for Render.com deployment
# This script installs ffmpeg for video encoding

set -e

echo "Installing ffmpeg for video encoding..."

# Install ffmpeg using apt-get (Render uses Ubuntu)
apt-get update
apt-get install -y ffmpeg

echo "FFmpeg installed successfully"
ffmpeg -version
