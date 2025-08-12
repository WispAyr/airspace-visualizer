# ATC Transcription System Guide

## Overview
The ATC Transcription System uses **Whisper AI** and **yt-dlp** to transcribe live Air Traffic Control communications from YouTube streams, specifically the [Glasgow Airport ATC stream](https://www.youtube.com/watch?v=vrmJx8jCAjY). This provides real-time access to runway assignments, aircraft clearances, and operational status directly from the source.

## 🎯 **What This System Does**

### **Live ATC Transcription**
- **Real-time audio processing** from YouTube live streams
- **AI-powered transcription** using OpenAI's Whisper model
- **Aviation-specific parsing** for runway, aircraft, and clearance information
- **Continuous monitoring** with 30-second audio segments

### **Information Extraction**
- **Runway assignments** (05/23, 09/27)
- **Aircraft callsigns** (EZY1234, BA1234, etc.)
- **Clearance information** (cleared, approved, denied, hold)
- **Weather updates** (wind, visibility, ceiling)
- **Traffic management** (separation, spacing, delays)

### **Integration Benefits**
- **Enhanced radar picture** with live ATC context
- **Real-time operational status** from Glasgow Airport
- **Historical ATC communications** for analysis
- **AI assistant integration** with live ATC data

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
# Make script executable
chmod +x start_atc_transcription.sh

# Start the service
./start_atc_transcription.sh
```

### **2. Start Transcription**
```bash
# Start ATC transcription for Glasgow Airport
curl -X POST http://localhost:8081/start \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=vrmJx8jCAjY",
    "airport_code": "EGPF",
    "model_size": "base"
  }'
```

### **3. Monitor Status**
```bash
# Check service status
curl http://localhost:8081/status

# Get latest transcriptions
curl http://localhost:8081/transcriptions?limit=5

# View statistics
curl http://localhost:8081/stats
```

## 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  YouTube Live   │    │   yt-dlp        │    │   Whisper AI    │
│  ATC Stream     │───►│   Audio         │───►│   Transcription │
│  (Glasgow)      │    │   Download      │    │   Model         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Audio         │    │   Parsed        │
                       │   Processing    │    │   ATC Data      │
                       │   (pydub)       │    │   (JSON)        │
                       └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Flask API     │    │   Aviation      │
                       │   Server        │    │   Radar System  │
                       │   (Port 8081)   │    │   Integration   │
                       └─────────────────┘    └─────────────────┘
```

## 📡 **API Endpoints**

### **Core Operations**
- **`POST /start`** - Start ATC transcription service
- **`POST /stop`** - Stop ATC transcription service
- **`GET /status`** - Get service status and configuration

### **Data Access**
- **`GET /transcriptions`** - Get latest transcriptions
- **`GET /stats`** - Get transcription statistics
- **`GET /search?q=query`** - Search transcriptions by keyword
- **`GET /export`** - Export transcriptions to JSON

### **Monitoring**
- **`GET /health`** - Health check endpoint
- **`GET /`** - Service information and endpoint list

## 🔧 **Configuration Options**

### **Model Sizes**
- **`tiny`** - Fastest, least accurate (39M parameters)
- **`base`** - Balanced speed/accuracy (74M parameters) ⭐ **Recommended**
- **`small`** - Better accuracy, slower (244M parameters)
- **`medium`** - High accuracy, slower (769M parameters)
- **`large`** - Best accuracy, slowest (1550M parameters)

### **Airport Codes**
- **`EGPF`** - Glasgow Airport (default)
- **`EGLL`** - London Heathrow
- **`EGCC`** - Manchester Airport
- **`EGBB`** - Birmingham Airport

### **YouTube Streams**
- **Glasgow ATC**: `https://www.youtube.com/watch?v=vrmJx8jCAjY`
- **Custom streams**: Any live YouTube ATC stream URL

## 📊 **Data Structure**

### **Transcription Object**
```json
{
  "timestamp": "2025-08-12T18:30:00",
  "raw_text": "Glasgow Tower, EZY1234, cleared for takeoff runway 23",
  "airport": "EGPF",
  "extracted_info": {
    "runway": "23",
    "callsigns": ["ezy1234"],
    "clearances": ["cleared for takeoff runway 23"]
  },
  "confidence": 0.75,
  "keywords_found": ["runway", "aircraft", "clearance"]
}
```

### **Statistics Object**
```json
{
  "total_transcriptions": 150,
  "last_transcription": "2025-08-12T18:30:00",
  "keywords_found": {
    "runway": 45,
    "aircraft": 89,
    "clearance": 67,
    "weather": 23,
    "traffic": 34
  },
  "average_confidence": 0.72
}
```

## 🎮 **Usage Examples**

### **Start Service with Custom Configuration**
```bash
curl -X POST http://localhost:8081/start \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=vrmJx8jCAjY",
    "airport_code": "EGPF",
    "model_size": "small"
  }'
```

### **Search for Specific Information**
```bash
# Search for runway 23 mentions
curl "http://localhost:8081/search?q=runway%2023"

# Search for specific aircraft callsign
curl "http://localhost:8081/search?q=ezy1234"

# Search for weather information
curl "http://localhost:8081/search?q=wind"
```

### **Export Data for Analysis**
```bash
# Export all transcriptions
curl "http://localhost:8081/export"

# Export with custom filename
curl "http://localhost:8081/export?filename=glasgow_atc_20250812.json"
```

## 🔍 **Information Extraction**

### **Runway Information**
- **Patterns**: `runway 23`, `rwy 23`, `23 approach`, `23 departure`
- **Glasgow Runways**: 05/23, 09/27
- **Usage**: Track active runways and traffic flow

### **Aircraft Callsigns**
- **Standard Format**: `EZY1234`, `BA1234`, `A1234`
- **Patterns**: 2-4 letters + 2-4 numbers
- **Usage**: Track specific aircraft and their communications

### **Clearance Types**
- **Takeoff**: `cleared for takeoff`, `cleared to depart`
- **Landing**: `cleared to land`, `cleared for approach`
- **Ground**: `cleared to pushback`, `cleared to taxi`
- **Holding**: `hold position`, `hold short of runway`

### **Weather Information**
- **Wind**: `wind 230 at 15 knots`
- **Visibility**: `visibility 10 kilometers`
- **Ceiling**: `ceiling 2000 feet`
- **Conditions**: `light rain`, `scattered clouds`

## 🚨 **Troubleshooting**

### **Common Issues**

#### **yt-dlp Not Found**
```bash
# Install yt-dlp
pip install yt-dlp

# Or use system package manager
# macOS: brew install yt-dlp
# Ubuntu: sudo apt install yt-dlp
```

#### **ffmpeg Not Available**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/
```

#### **Whisper Model Loading Issues**
```bash
# Check available models
python3 -c "import whisper; print(whisper.available_models())"

# Force reinstall
pip uninstall openai-whisper
pip install openai-whisper
```

#### **Port Already in Use**
```bash
# Check what's using port 8081
lsof -i :8081

# Kill the process
kill -9 <PID>
```

### **Performance Issues**

#### **Slow Transcription**
- Use smaller Whisper model (`tiny` or `base`)
- Reduce audio segment duration
- Check CPU/GPU resources

#### **High Memory Usage**
- Limit transcription history size
- Use smaller Whisper model
- Monitor system resources

#### **Audio Quality Issues**
- Check YouTube stream quality
- Verify ffmpeg installation
- Adjust audio format settings

## 🔗 **Integration with Aviation Radar**

### **AI Server Integration**
The ATC transcriptions can be integrated with your existing AI server to provide:
- **Real-time ATC context** for aircraft queries
- **Runway status information** for operational queries
- **Live clearance data** for flight planning

### **Web Interface Integration**
Add ATC transcription display to your radar interface:
- **Live transcription feed** in a dedicated panel
- **ATC information overlay** on the radar display
- **Search and filter** capabilities for transcriptions

### **Telegram Bot Integration**
Extend your @TACAMOBOT with ATC commands:
- **`/atc status`** - Current ATC transcription status
- **`/atc latest`** - Latest transcriptions
- **`/atc search <query>`** - Search ATC communications

## 📈 **Performance Optimization**

### **Model Selection**
- **Development/Testing**: Use `tiny` model for speed
- **Production**: Use `base` or `small` for accuracy
- **High-accuracy**: Use `medium` or `large` for critical operations

### **Audio Processing**
- **Segment Duration**: 30 seconds (balanced)
- **Audio Format**: WAV for best quality
- **Sample Rate**: 16kHz (Whisper standard)

### **Resource Management**
- **Memory**: Monitor Whisper model memory usage
- **CPU**: Multi-threading for audio processing
- **Storage**: Regular cleanup of temporary files

## 🔮 **Future Enhancements**

### **Advanced Features**
- **Multi-airport support** for multiple ATC streams
- **Real-time alerts** for specific ATC events
- **Voice synthesis** for ATC communications
- **Machine learning** for pattern recognition

### **Integration Opportunities**
- **Flight planning software** integration
- **ATC training** and simulation
- **Aviation research** and analysis
- **Emergency response** coordination

### **Commercial Applications**
- **Flight schools** for ATC training
- **Airlines** for operational monitoring
- **Airports** for capacity planning
- **Government** for aviation oversight

## 📚 **Additional Resources**

### **Documentation**
- **Whisper Documentation**: https://github.com/openai/whisper
- **yt-dlp Documentation**: https://github.com/yt-dlp/yt-dlp
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html

### **Aviation Resources**
- **Glasgow Airport**: https://www.glasgowairport.com/
- **UK ATC Frequencies**: https://www.airnav.com/airports/uk/
- **Aviation Terminology**: https://www.skybrary.aero/

### **Technical Support**
- **GitHub Issues**: Report bugs and feature requests
- **Community Forum**: Aviation enthusiast discussions
- **Professional Support**: Commercial deployment assistance

---

## 🎉 **Getting Started Checklist**

- [ ] **Install dependencies** (`./start_atc_transcription.sh`)
- [ ] **Verify ffmpeg** installation
- [ ] **Test yt-dlp** with YouTube URL
- [ ] **Start transcription service** (`POST /start`)
- [ ] **Monitor status** (`GET /status`)
- [ ] **View transcriptions** (`GET /transcriptions`)
- [ ] **Test search** (`GET /search?q=runway`)
- [ ] **Export data** (`GET /export`)
- [ ] **Integrate with radar system**

---

**The ATC Transcription System transforms your aviation radar from a passive monitoring tool into an active, intelligent system that understands and processes live air traffic control communications in real-time! 🎧✈️**
