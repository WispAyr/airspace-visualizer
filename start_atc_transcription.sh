#!/bin/bash

# Start ATC Transcription Service for Glasgow Airport
echo "🎧 Starting ATC Transcription Service for Glasgow Airport..."

# Free port if needed
echo "🔌 Freeing port 8081 if needed..."
lsof -ti:8081 | xargs kill -9 2>/dev/null || true

# Wait a moment for port to free
sleep 2

# Activate virtual environment
source .venv/bin/activate

# Install ATC transcription dependencies if not already installed
echo "📦 Installing ATC transcription dependencies..."
pip install -r requirements_atc.txt

# Check if yt-dlp is available
if ! command -v yt-dlp &> /dev/null; then
    echo "⚠️  yt-dlp not found. Installing..."
    pip install yt-dlp
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg not found. Please install ffmpeg:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    echo "   Windows: Download from https://ffmpeg.org/"
    exit 1
fi

# Start ATC transcription server
echo "🎤 Launching ATC Transcription Server..."
echo "📡 Glasgow Airport ATC Stream: https://www.youtube.com/watch?v=vrmJx8jCAjY"
echo "🌐 Server will be available at: http://localhost:8081"
echo ""
echo "📋 Available endpoints:"
echo "   - GET  /                    - Service information"
echo "   - POST /start               - Start transcription"
echo "   - POST /stop                - Stop transcription"
echo "   - GET  /status              - Service status"
echo "   - GET  /transcriptions      - Latest transcriptions"
echo "   - GET  /stats               - Transcription statistics"
echo "   - GET  /search?q=query     - Search transcriptions"
echo "   - GET  /export              - Export to JSON"
echo "   - GET  /health              - Health check"
echo ""

python3 atc_server.py
