#!/bin/bash

# Complete Quick Start Script for Aviation Radar System
echo "🚁 Starting Complete Aviation Radar System with ATC Transcription..."

# Free ports if they're in use
echo "🔌 Freeing ports if needed..."
lsof -ti:11435 | xargs kill -9 2>/dev/null || true
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:8081 | xargs kill -9 2>/dev/null || true

# Wait a moment for ports to free
sleep 2

# Activate virtual environment
source .venv/bin/activate

# Start AI server
echo "🤖 Starting AI Server..."
python3 ai_server.py &
AI_PID=$!

# Wait for AI server to start
sleep 5

# Start radar server
echo "📡 Starting Radar Server..."
python3 airspace_server.py &
RADAR_PID=$!

# Wait for radar server to start
sleep 5

# Start ATC transcription server
echo "🎧 Starting ATC Transcription Server..."
python3 atc_server.py &
ATC_PID=$!

# Wait for ATC server to start
sleep 5

# Start Telegram bot
echo "📱 Starting Telegram Bot..."
export TELEGRAM_TOKEN="6730537017:AAGnK4toKXph8kodfSE80msciRdUPqgVIvw"
python3 telegram_bot.py &
BOT_PID=$!

echo "✅ All services started!"
echo "🤖 AI Server PID: $AI_PID (Port 11435)"
echo "📡 Radar Server PID: $RADAR_PID (Port 8080)"
echo "🎧 ATC Transcription PID: $ATC_PID (Port 8081)"
echo "📱 Telegram Bot PID: $BOT_PID"
echo ""
echo "🌐 Access your systems at:"
echo "   - Web Interface: http://localhost:8000/airspace_visualizer_enhanced.html"
echo "   - AI Server: http://localhost:11435"
echo "   - Radar Server: http://localhost:8080"
echo "   - ATC Transcription: http://localhost:8081"
echo ""
echo "📱 Telegram Bot: @TACAMOBOT"
echo ""
echo "🎧 ATC Transcription Commands:"
echo "   - Start: curl -X POST http://localhost:8081/start"
echo "   - Status: curl http://localhost:8081/status"
echo "   - Latest: curl http://localhost:8081/transcriptions"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo '🛑 Stopping all services...'; kill $AI_PID $RADAR_PID $ATC_PID $BOT_PID 2>/dev/null; exit" INT

# Keep script running
wait
