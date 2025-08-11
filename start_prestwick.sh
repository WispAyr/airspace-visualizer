#!/bin/bash
# Start Airspace Visualizer with Prestwick Regional Data

echo "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Starting Airspace Visualizer - Prestwick Region"
echo "============================================================"

# Kill any existing processes
pkill -f "python3.*mock_data_generator.py" 2>/dev/null
pkill -f "python3.*visualizer_bridge.py" 2>/dev/null  
pkill -f "python3.*ai_server.py" 2>/dev/null
pkill -f "python3 -m http.server 8000" 2>/dev/null

# Wait a moment for processes to stop
sleep 2

# Start services in background
echo "🚀 Starting Prestwick mock data generator..."
source .venv/bin/activate && REGION_CODE=PRESTWICK python3 mock_data_generator.py &
MOCK_PID=$!

sleep 3

echo "🌉 Starting visualizer bridge..."
source .venv/bin/activate && python3 visualizer_bridge.py &
BRIDGE_PID=$!

sleep 2

echo "🤖 Starting AI server..."
source .venv/bin/activate && python3 ai_server.py &
AI_PID=$!

sleep 2

echo "🌐 Starting web server..."
python3 -m http.server 8000 &
WEB_PID=$!

sleep 2

echo "============================================================"
echo "✅ Prestwick Airspace Visualizer is now running!"
echo "============================================================"
echo "📍 Region: Prestwick, Scotland"
echo "📡 Center: 55.5094°N, 4.5967°W (Prestwick Airport)"
echo "🌐 Web Interface: http://localhost:8000/airspace_visualizer.html"
echo "============================================================"
echo "🛩️  Airlines: Ryanair, Loganair, British Airways, easyJet"
echo "✈️  Aircraft Types: B737, A320, DHC6 Twin Otter, BN2T Islander"
echo "📻 ACARS Messages: Scottish aviation terminology"
echo "============================================================"
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap 'echo ""; echo "🛑 Stopping services..."; kill $MOCK_PID $BRIDGE_PID $AI_PID $WEB_PID 2>/dev/null; exit' INT

# Keep script running
wait
