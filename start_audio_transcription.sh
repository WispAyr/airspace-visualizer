#!/bin/bash

# ATC Audio Transcription Startup Script
# This script starts the Whisper-based ATC audio transcription server

echo "🎙️  Starting ATC Audio Transcription System"
echo "============================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements_audio.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if required packages are installed
echo "🔍 Checking dependencies..."

python3 -c "import whisper" 2>/dev/null || {
    echo "❌ Whisper not installed. Installing..."
    pip install openai-whisper
}

python3 -c "import pyaudio" 2>/dev/null || {
    echo "❌ PyAudio not installed. Installing..."
    echo "📝 Note: On macOS, you may need: brew install portaudio"
    echo "📝 Note: On Ubuntu, you may need: sudo apt-get install portaudio19-dev"
    pip install pyaudio
}

python3 -c "import flask" 2>/dev/null || {
    echo "❌ Flask not installed. Installing..."
    pip install flask flask-cors
}

echo "✅ Dependencies checked"

# Kill any existing audio transcription server
echo "🔄 Stopping any existing audio transcription server..."
pkill -f "audio_transcription_server.py" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Free up port 8082 if needed
echo "🧹 Freeing port 8082..."
lsof -ti:8082 | xargs kill -9 2>/dev/null || true

# Start the audio transcription server
echo "🚀 Starting Audio Transcription Server on port 8082..."
echo "📡 API will be available at: http://localhost:8082"
echo "🎧 Device list: http://localhost:8082/api/audio/devices"
echo "🎙️  Transcriptions: http://localhost:8082/api/audio/transcriptions"
echo ""
echo "⚠️  Important Notes:"
echo "   - Ensure your audio input device is working"
echo "   - For ATC audio, connect your scanner/radio to audio input"
echo "   - First run will download Whisper model (~140MB)"
echo "   - Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 audio_transcription_server.py

