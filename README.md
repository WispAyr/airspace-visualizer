# Airspace Visualizer - Aviation Radar & AI Assistant

A comprehensive aviation radar system with real-time aircraft tracking, weather data, NOTAMs, and AI-powered assistance accessible via web interface and Telegram bot.

## 🚀 Features

### Core Radar System
- **Real-time ADS-B tracking** with PiAware integration
- **Enhanced aircraft data** via BaseStation database
- **Airspace visualization** with UK airspace boundaries
- **Live weather data** from NOAA METAR
- **NOTAM integration** from UK aviation archive
- **AIS ship tracking** via AISStream.io

### AI Assistant
- **Semantic search** across all aviation data
- **Natural language queries** for aircraft, weather, and NOTAMs
- **Historical data analysis** from database
- **Intelligent context selection** prioritizing relevant data types
- **Real-time data integration** with live radar feeds

### Telegram Bot (@TACAMOBOT)
- **Mobile access** to all system features
- **Voice commands** and natural language queries
- **Real-time notifications** and status updates
- **Weather queries** with METAR data
- **Aircraft tracking** and database access

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   AI Server     │    │  Radar Server   │
│   (HTML/JS)     │◄──►│   (Port 11435)  │◄──►│  (Port 8080)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Telegram Bot   │    │   Ollama AI     │    │  BaseStation    │
│  (@TACAMOBOT)   │    │   (Local)       │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚁 Quick Start

### 1. Start All Services
```bash
# Quick start with port management
./quick_start_telegram.sh

# Or start individually
./start_audio_transcription.sh  # Audio processing
./start_prestwick.sh            # Radar server
python3 ai_server.py &          # AI assistant
./start_telegram_bot.sh         # Telegram bot
```

### 2. Access Systems
- **Web Interface**: http://localhost:8000/airspace_visualizer_enhanced.html
- **AI Server**: http://localhost:11435
- **Radar Server**: http://localhost:8080
- **Telegram Bot**: @TACAMOBOT

### 3. Telegram Bot Commands
```
/start          - Show help and available commands
/status         - System health and database stats
/aircraft       - Current aircraft information
/weather <ICAO> - Weather for specific airport
/notams         - Active NOTAMs
/ai <question>  - Ask AI anything about aviation
```

## 📊 Current System Status

### ✅ **Fully Implemented**
- **Real-time ADS-B tracking** with PiAware integration
- **BaseStation database** with enhanced aircraft information
- **METAR weather data** from NOAA for key UK airports
- **NOTAM parsing** from UK aviation archive
- **AI semantic search** with intelligent context selection
- **Telegram bot** with full system access
- **Web interface** with collapsible panels and AI chat

### 🔧 **Recently Enhanced**
- **Weather query handling** - AI now prioritizes METAR over NOTAMs
- **Aircraft query optimization** - Better separation of data types
- **Data validation** - Consistent aircraft status information
- **Performance optimization** - Reduced update frequency and improved layout

### 📈 **System Metrics**
- **Indexed messages**: 18+ (ADS-B, METAR, NOTAMs, ACARS)
- **Supported airports**: EGPK, EGLL, EGCC, EGBB, EGPH
- **Data sources**: PiAware, NOAA, UK NOTAM archive, BaseStation
- **AI model**: Gemma3 4B with semantic search

## 🛠️ Technical Details

### Dependencies
- **Python 3.13+** with virtual environment
- **Ollama** for local AI models
- **FAISS** for semantic search indexing
- **Flask** for web services
- **python-telegram-bot** for Telegram integration

### Data Flow
1. **PiAware** → ADS-B data → Radar server
2. **NOAA** → METAR data → AI server
3. **UK Archive** → NOTAM data → AI server
4. **BaseStation** → Aircraft details → Radar server
5. **AI Server** → Semantic index → Telegram/Web

### API Endpoints
- `/api/aircraft/*` - Aircraft data and history
- `/api/metar/<icao>` - Weather data
- `/api/notams` - NOTAM information
- `/api/database/*` - Database statistics
- `/chat` - AI conversation interface

## 📚 Documentation

- **[TELEGRAM_BOT_GUIDE.md](TELEGRAM_BOT_GUIDE.md)** - Complete Telegram bot guide
- **[AIS_INTEGRATION_GUIDE.md](AIS_INTEGRATION_GUIDE.md)** - Ship tracking setup
- **[SSR_INTEGRATION_GUIDE.md](SSR_INTEGRATION_GUIDE.md)** - Secondary radar codes
- **[AUDIO_TRANSCRIPTION_GUIDE.md](AUDIO_TRANSCRIPTION_GUIDE.md)** - Audio processing

## 🎯 What's Next

### Immediate Priorities
1. **Performance optimization** - Reduce AI server rebuild frequency
2. **Error handling** - Improve Telegram bot error recovery
3. **Data caching** - Implement smarter data refresh strategies

### Future Enhancements
1. **Alert system** - Push notifications for specific events
2. **Custom filters** - User-defined aircraft type/altitude filters
3. **Image generation** - Radar screen captures via Telegram
4. **Voice messages** - Audio responses for hands-free operation
5. **Location-based queries** - Query aircraft near specific coordinates

### Integration Opportunities
1. **Flight planning** - Integration with flight planning software
2. **ATC integration** - Real-time ATC communications
3. **Weather forecasting** - Extended weather predictions
4. **Flight tracking** - Integration with commercial flight trackers

## 🐛 Troubleshooting

### Common Issues
- **Port conflicts**: Use `./quick_start_telegram.sh` for automatic port management
- **AI not responding**: Check if AI server is running on port 11435
- **No aircraft data**: Verify PiAware connection and radar server status
- **Telegram bot errors**: Check bot token and server connectivity

### Debug Commands
```bash
# Check system status
curl "http://localhost:11435/status"
curl "http://localhost:8080/api/database/stats"

# Test AI responses
curl "http://localhost:11435/chat?q=how%20many%20aircraft"

# Rebuild AI index
curl "http://localhost:11435/rebuild"
```

## 🤝 Contributing

This system is designed for aviation professionals and enthusiasts. Contributions are welcome for:
- Additional data sources
- Enhanced AI capabilities
- Improved user interfaces
- Performance optimizations

## 📄 License

See [LICENSE](LICENSE) file for details.

---

**Status**: Production Ready ✅  
**Last Updated**: August 12, 2025  
**Version**: 2.0.0 (Telegram Bot + Enhanced AI)