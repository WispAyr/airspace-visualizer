# 🎙️ ATC Audio Transcription System Guide

## Overview

The ATC Audio Transcription System uses OpenAI's Whisper AI to provide real-time transcription of air traffic control communications. This system integrates seamlessly with the Airspace Visualizer to provide both visual radar data and live audio transcription.

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install openai-whisper pyaudio numpy flask flask-cors

# On macOS, install PortAudio first:
brew install portaudio

# On Ubuntu/Debian:
sudo apt-get install portaudio19-dev

# On Windows:
# Download and install PortAudio from http://www.portaudio.com/
```

### 2. Start the Audio Transcription Server

```bash
# Option 1: Use the startup script
./start_audio_transcription.sh

# Option 2: Manual start
source .venv/bin/activate
python3 audio_transcription_server.py
```

### 3. Configure in the UI

1. Open the Airspace Visualizer: `http://localhost:8000/airspace_visualizer_enhanced.html`
2. Click the **AUDIO** tab in the control panel
3. Select your audio input device
4. Configure transcription settings
5. Click **🔴 Start Recording**

## ⚙️ Configuration Options

### Whisper Model Selection

| Model | Speed | Accuracy | Memory | Best For |
|-------|-------|----------|--------|----------|
| **Tiny** | Fastest | Lower | ~39 MB | Real-time, low-power devices |
| **Base** | Fast | Good | ~74 MB | **Recommended balance** |
| **Small** | Medium | Better | ~244 MB | Higher accuracy needed |
| **Medium** | Slow | High | ~769 MB | Professional use |
| **Large** | Slowest | Highest | ~1550 MB | Maximum accuracy |

### Audio Processing Settings

#### **Processing Chunk Size**
- **3 seconds**: Fastest response, may miss context
- **5 seconds**: **Recommended balance** of speed and accuracy
- **10 seconds**: Best accuracy, slower response

#### **Language Detection**
- **English**: Fixed English (fastest)
- **Auto-detect**: Automatic language detection
- **Spanish/French/German/Italian**: Fixed language modes

#### **Silence Threshold**
- **100-2000**: Adjusts voice activity detection
- **500**: Default recommended value
- Higher values = less sensitive (ignores quiet speech)
- Lower values = more sensitive (may pick up noise)

### Audio Enhancement Options

#### **Noise Reduction**
- Reduces background noise and static
- May slightly increase processing time
- Useful for noisy radio environments

#### **Automatic Gain Control (AGC)**
- Normalizes audio levels automatically
- Helps with varying signal strengths
- Recommended for scanner inputs

#### **High-pass Filter**
- Removes low-frequency noise (< 300Hz)
- **Enabled by default** - reduces engine noise, wind
- Essential for aviation audio

### ATC-Specific Features

#### **Emergency Call Detection**
- Highlights emergency-related communications
- Looks for keywords: "emergency", "mayday", "pan-pan"
- **Enabled by default**

#### **Callsign Extraction**
- Attempts to identify aircraft callsigns
- Links transcriptions to radar contacts
- Experimental feature

#### **Frequency Monitoring**
- Enter the monitored frequency (e.g., "118.100")
- Helps with context and logging
- Optional but recommended

## 🎧 Audio Setup

### Scanner Connection

#### **Direct Audio Cable**
```
Scanner Headphone Jack → Computer Line-In
```
- Use 3.5mm audio cable
- Adjust scanner volume to ~50%
- Monitor with headphones to check quality

#### **Audio Interface (Recommended)**
```
Scanner → Audio Interface → Computer USB
```
- Professional audio interfaces provide better quality
- Built-in noise reduction and level control
- Multiple input support for monitoring several frequencies

### Software-Defined Radio (SDR)

#### **RTL-SDR Setup**
```
RTL-SDR → Computer USB → SDR Software → Virtual Audio Cable → Transcription
```

**Popular SDR Software:**
- **SDR#** (Windows)
- **GQRX** (Linux/macOS)
- **CubicSDR** (Cross-platform)

**Virtual Audio Cable:**
- **VB-Audio Cable** (Windows)
- **BlackHole** (macOS)
- **PulseAudio** (Linux)

### Audio Quality Tips

#### **Optimal Settings**
- **Sample Rate**: 16kHz (automatically handled)
- **Bit Depth**: 16-bit (automatically handled)
- **Scanner Volume**: 40-60% to avoid clipping
- **Room Noise**: Minimize background noise

#### **Troubleshooting Audio Issues**
- **No audio detected**: Check device selection and permissions
- **Poor transcription**: Adjust silence threshold
- **Clipping/distortion**: Reduce scanner volume
- **Background noise**: Enable noise reduction and high-pass filter

## 🖥️ User Interface

### Control Panel (AUDIO Tab)

#### **Device Management**
- **Audio Input Device**: Dropdown to select microphone/line-in
- **🔄 Refresh Audio Devices**: Reload available devices
- **Recording Status**: Real-time status indicator

#### **Recording Controls**
- **🔴 Start Recording**: Begin transcription
- **⏹️ Stop Recording**: End transcription
- Status shows current recording state

#### **Configuration Sections**

**⚙️ Audio Configuration:**
- Whisper Model selection
- Confidence threshold slider
- Processing chunk size
- Language selection
- Silence threshold

**🎚️ Audio Enhancement:**
- Noise Reduction toggle
- Automatic Gain Control
- High-pass Filter

**✈️ ATC-Specific:**
- Emergency Call Detection
- Callsign Extraction
- Frequency input field

#### **Live Transcriptions Display**
- Scrolling list of recent transcriptions
- Color-coded confidence levels:
  - 🟢 **Green**: >70% confidence
  - 🟡 **Orange**: 40-70% confidence
  - 🔴 **Red**: <40% confidence
- Timestamp and confidence score for each transcription

#### **Configuration Management**
- **🗑️ Clear**: Remove all transcriptions
- **🔄 Reset**: Reset all settings to defaults
- **Status Display**: Current configuration summary

## 🔧 API Reference

### Endpoints

#### **Start Transcription**
```http
POST /api/audio/start
Content-Type: application/json

{
  "device_index": 0,
  "config": {
    "whisperModel": "base",
    "confidenceThreshold": 50,
    "language": "en"
  }
}
```

#### **Stop Transcription**
```http
POST /api/audio/stop
```

#### **Get Transcriptions**
```http
GET /api/audio/transcriptions?limit=20&since=2025-01-01T00:00:00
```

#### **Get Audio Devices**
```http
GET /api/audio/devices
```

#### **Configuration Management**
```http
GET /api/audio/config
POST /api/audio/config
Content-Type: application/json

{
  "whisperModel": "small",
  "language": "auto"
}
```

#### **System Status**
```http
GET /api/audio/status
```

## 🛠️ Advanced Configuration

### Performance Tuning

#### **For Real-Time Performance**
- Use **Tiny** or **Base** model
- Set chunk size to **3 seconds**
- Enable **High-pass Filter** only
- Use dedicated audio interface

#### **For Maximum Accuracy**
- Use **Small** or **Medium** model
- Set chunk size to **10 seconds**
- Enable all audio enhancements
- Use professional audio equipment

### Integration with Radar System

#### **Communications Log Integration**
- Enable "Show in Communications Log"
- Transcriptions appear alongside ACARS messages
- Color-coded by confidence level

#### **AI Assistant Integration**
- Transcriptions are automatically indexed
- Ask questions about recent communications
- Example: "What emergency calls were there?"

### Troubleshooting

#### **Common Issues**

**Server Won't Start**
```bash
# Check dependencies
python3 -c "import whisper, pyaudio"

# Check port availability
lsof -i :8082

# Kill conflicting processes
pkill -f audio_transcription_server
```

**No Audio Devices**
```bash
# Check audio permissions (macOS)
# System Preferences → Security & Privacy → Microphone

# Test audio devices
python3 -c "import pyaudio; pa = pyaudio.PyAudio(); [print(f'{i}: {pa.get_device_info_by_index(i)}') for i in range(pa.get_device_count())]"
```

**Poor Transcription Quality**
- Check audio levels (not clipping)
- Reduce background noise
- Try different Whisper model
- Adjust confidence threshold

**High CPU Usage**
- Use smaller Whisper model
- Increase chunk size
- Disable unnecessary enhancements

## 📊 Performance Benchmarks

### Model Performance (Apple M1 Mac)

| Model | Transcription Time | CPU Usage | Memory | Quality Score |
|-------|-------------------|-----------|---------|---------------|
| Tiny | ~0.5s per 5s audio | 15% | 39MB | 7/10 |
| Base | ~1.0s per 5s audio | 25% | 74MB | 8/10 |
| Small | ~2.0s per 5s audio | 40% | 244MB | 9/10 |
| Medium | ~4.0s per 5s audio | 60% | 769MB | 9.5/10 |

*Results may vary based on hardware and audio complexity*

## 🚨 Legal and Safety Notes

### Legal Compliance
- ✅ **Legal**: Monitoring ATC for personal/educational use
- ❌ **Illegal**: Recording/distributing without permission in some jurisdictions
- 📋 **Check Local Laws**: Verify regulations in your area

### Safety Considerations
- **NOT FOR OPERATIONAL USE**: This system is for monitoring only
- **NOT CERTIFIED**: Not approved for safety-critical applications
- **VERIFY INFORMATION**: Always use official sources for flight operations

## 🔄 Updates and Maintenance

### Keeping Up to Date
```bash
# Update Whisper
pip install --upgrade openai-whisper

# Update other dependencies
pip install --upgrade pyaudio numpy flask flask-cors
```

### Configuration Backup
- Settings are automatically saved to browser localStorage
- Export configuration: Use browser developer tools
- Import configuration: Paste into localStorage

## 🆘 Support

### Getting Help
1. **Check this guide** for common solutions
2. **Review server logs** in terminal for error messages
3. **Test basic functionality** with simple audio input
4. **Check GitHub issues** for known problems

### Reporting Issues
Please include:
- Operating system and version
- Python version
- Audio hardware details
- Error messages from server logs
- Steps to reproduce the problem

---

**Ready to monitor live ATC communications with AI-powered transcription!** 🎙️✈️📻

