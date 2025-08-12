#!/bin/bash

# Quick Start Script for TACAMOBOT Telegram Bot
echo "🚁 Starting TACAMOBOT Telegram Bot..."

# Free ports if they're in use
echo "🔌 Freeing ports if needed..."
lsof -ti:11435 | xargs kill -9 2>/dev/null || true
lsof -ti:8080 | xargs kill -9 2>/dev/null || true

# Wait a moment for ports to free
sleep 2

# Start AI server
echo "🤖 Starting AI Server..."
source .venv/bin/activate
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

# Start Telegram bot
echo "📱 Starting Telegram Bot..."
export TELEGRAM_TOKEN="6730537017:AAGnK4toKXph8kodfSE80msciRdUPqgVIvw"
python3 telegram_bot.py &
BOT_PID=$!

echo "✅ All services started!"
echo "🤖 AI Server PID: $AI_PID"
echo "📡 Radar Server PID: $RADAR_PID"
echo "📱 Telegram Bot PID: $BOT_PID"
echo ""
echo "🌐 Access your systems at:"
echo "   - Web Interface: http://localhost:8000/airspace_visualizer_enhanced.html"
echo "   - AI Server: http://localhost:11435"
echo "   - Radar Server: http://localhost:8080"
echo ""
echo "📱 Telegram Bot: @TACAMOBOT"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo '🛑 Stopping all services...'; kill $AI_PID $RADAR_PID $BOT_PID 2>/dev/null; exit" INT

# Keep script running
wait
