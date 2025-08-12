#!/usr/bin/env python3
"""
ATC Audio Transcription Server using OpenAI Whisper
Captures live audio from ATC frequencies and transcribes using Whisper AI
"""

import os
import sys
import time
import json
import threading
import queue
import wave
import pyaudio
import whisper
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class ATCAudioTranscriber:
    def __init__(self):
        self.model = None
        self.audio_queue = queue.Queue()
        self.transcription_buffer = []
        self.is_recording = False
        self.audio_thread = None
        self.transcription_thread = None
        
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000  # Whisper works best with 16kHz
        
        # Configuration settings (defaults)
        self.config = {
            'whisperModel': 'base',
            'confidenceThreshold': 50,
            'chunkSize': 5,
            'language': 'en',
            'silenceThreshold': 500,
            'noiseReduction': False,
            'autoGain': False,
            'highpassFilter': True,
            'emergencyDetection': True,
            'callsignExtraction': False,
            'monitoredFrequency': ''
        }
        
        # Transcription settings
        self.MIN_AUDIO_LENGTH = 1.0  # Minimum seconds of audio to process
        self.MAX_BUFFER_SIZE = 100  # Keep last 100 transcriptions
        
        print("🎙️  Initializing ATC Audio Transcription Server...")
        self.load_whisper_model()
        
    def load_whisper_model(self, model_name="base"):
        """Load Whisper model for transcription"""
        try:
            print(f"🤖 Loading Whisper model: {model_name} (this may take a moment)...")
            # Options: tiny, base, small, medium, large
            self.model = whisper.load_model(model_name)
            self.config['whisperModel'] = model_name
            print(f"✅ Whisper model '{model_name}' loaded successfully")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {e}")
            print("💡 Try: pip install openai-whisper")
            sys.exit(1)
    
    def update_config(self, new_config):
        """Update configuration settings"""
        if new_config:
            self.config.update(new_config)
            print(f"⚙️  Updated configuration: {new_config}")
            
            # Reload model if changed
            if 'whisperModel' in new_config and new_config['whisperModel'] != self.config.get('whisperModel'):
                self.load_whisper_model(new_config['whisperModel'])
    
    def start_audio_capture(self, device_index=None):
        """Start capturing audio from microphone or audio device"""
        try:
            self.audio = pyaudio.PyAudio()
            
            # List available audio devices
            print("🎧 Available audio devices:")
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                print(f"   {i}: {info['name']} - {info['maxInputChannels']} channels")
            
            # Use default input device if none specified
            if device_index is None:
                device_index = self.audio.get_default_input_device_info()['index']
            
            print(f"🎙️  Using audio device {device_index}")
            
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK
            )
            
            self.is_recording = True
            self.audio_thread = threading.Thread(target=self._audio_capture_loop)
            self.transcription_thread = threading.Thread(target=self._transcription_loop)
            
            self.audio_thread.start()
            self.transcription_thread.start()
            
            print("🔴 Audio capture started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting audio capture: {e}")
            return False
    
    def stop_audio_capture(self):
        """Stop audio capture"""
        self.is_recording = False
        
        if self.audio_thread:
            self.audio_thread.join()
        if self.transcription_thread:
            self.transcription_thread.join()
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        
        print("⏹️  Audio capture stopped")
    
    def _audio_capture_loop(self):
        """Continuous audio capture loop"""
        audio_buffer = []
        chunk_count = 0
        chunks_per_segment = int(self.RATE * self.config['chunkSize'] / self.CHUNK)
        
        while self.is_recording:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio_buffer.append(data)
                chunk_count += 1
                
                # Process audio in segments
                if chunk_count >= chunks_per_segment:
                    # Convert to numpy array
                    audio_data = b''.join(audio_buffer)
                    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Check if audio has sufficient volume (not just silence)
                    if self._has_speech(audio_np):
                        self.audio_queue.put({
                            'audio': audio_np,
                            'timestamp': datetime.now()
                        })
                    
                    # Reset buffer
                    audio_buffer = []
                    chunk_count = 0
                    
            except Exception as e:
                print(f"❌ Audio capture error: {e}")
                time.sleep(0.1)
    
    def _has_speech(self, audio_data):
        """Simple voice activity detection"""
        # Calculate RMS (Root Mean Square) to detect audio level
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > (self.config['silenceThreshold'] / 32768.0)
    
    def _transcription_loop(self):
        """Continuous transcription processing loop"""
        while self.is_recording:
            try:
                # Get audio from queue (with timeout to allow clean shutdown)
                try:
                    audio_item = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Transcribe audio with configuration
                language = None if self.config['language'] == 'auto' else self.config['language']
                result = self.model.transcribe(
                    audio_item['audio'],
                    fp16=False,  # Use fp32 for better compatibility
                    language=language
                )
                
                text = result['text'].strip()
                
                # Only keep transcriptions with actual content
                if len(text) > 3 and not self._is_noise(text):
                    transcription = {
                        'id': f"atc_{int(time.time() * 1000)}",
                        'timestamp': audio_item['timestamp'].isoformat(),
                        'text': text,
                        'confidence': self._estimate_confidence(result),
                        'type': 'ATC_AUDIO',
                        'source': 'Whisper AI',
                        'frequency': 'Unknown'  # Could be enhanced with frequency detection
                    }
                    
                    self.transcription_buffer.append(transcription)
                    
                    # Keep buffer size manageable
                    if len(self.transcription_buffer) > self.MAX_BUFFER_SIZE:
                        self.transcription_buffer.pop(0)
                    
                    print(f"🎙️  ATC: {text}")
                
                self.audio_queue.task_done()
                
            except Exception as e:
                print(f"❌ Transcription error: {e}")
                time.sleep(0.1)
    
    def _is_noise(self, text):
        """Filter out common noise patterns"""
        noise_patterns = [
            'thank you', 'thanks', 'you', 'uh', 'um', 'ah',
            'noise', 'static', 'beep', 'tone'
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in noise_patterns) and len(text) < 10
    
    def _estimate_confidence(self, result):
        """Estimate transcription confidence"""
        # Whisper doesn't directly provide confidence, so we estimate
        # based on the presence of segments and average log probability
        if 'segments' in result and result['segments']:
            avg_logprob = np.mean([seg.get('avg_logprob', -1.0) for seg in result['segments']])
            # Convert log probability to approximate confidence (0-1)
            confidence = max(0, min(1, (avg_logprob + 1.0) / 1.0))
            return round(confidence, 2)
        return 0.5  # Default moderate confidence
    
    def get_recent_transcriptions(self, limit=20):
        """Get recent transcriptions"""
        return self.transcription_buffer[-limit:] if self.transcription_buffer else []
    
    def clear_transcriptions(self):
        """Clear transcription buffer"""
        self.transcription_buffer = []
        print("🗑️  Transcription buffer cleared")

# Global transcriber instance
transcriber = ATCAudioTranscriber()

@app.route('/api/audio/start', methods=['POST'])
def start_transcription():
    """Start audio transcription"""
    try:
        data = request.get_json() or {}
        device_index = data.get('device_index')
        config = data.get('config', {})
        
        # Update configuration if provided
        if config:
            transcriber.update_config(config)
        
        if transcriber.start_audio_capture(device_index):
            return jsonify({
                "status": "success",
                "message": "Audio transcription started",
                "config": transcriber.config,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to start audio transcription"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/audio/stop', methods=['POST'])
def stop_transcription():
    """Stop audio transcription"""
    try:
        transcriber.stop_audio_capture()
        return jsonify({
            "status": "success",
            "message": "Audio transcription stopped",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/audio/transcriptions')
def get_transcriptions():
    """Get recent transcriptions"""
    try:
        limit = int(request.args.get('limit', 20))
        since = request.args.get('since')  # ISO timestamp
        
        transcriptions = transcriber.get_recent_transcriptions(limit)
        
        # Filter by timestamp if provided
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            transcriptions = [
                t for t in transcriptions 
                if datetime.fromisoformat(t['timestamp']) > since_dt
            ]
        
        return jsonify({
            "status": "success",
            "data": {
                "transcriptions": transcriptions,
                "count": len(transcriptions),
                "is_recording": transcriber.is_recording
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/audio/devices')
def get_audio_devices():
    """Get available audio input devices"""
    try:
        audio = pyaudio.PyAudio()
        devices = []
        
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Only input devices
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': info['defaultSampleRate']
                })
        
        audio.terminate()
        
        return jsonify({
            "status": "success",
            "data": {
                "devices": devices,
                "default_device": pyaudio.PyAudio().get_default_input_device_info()['index']
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/audio/clear', methods=['POST'])
def clear_transcriptions():
    """Clear transcription buffer"""
    try:
        transcriber.clear_transcriptions()
        return jsonify({
            "status": "success",
            "message": "Transcriptions cleared"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/audio/status')
def get_status():
    """Get transcription system status"""
    return jsonify({
        "status": "success",
        "data": {
            "is_recording": transcriber.is_recording,
            "model_loaded": transcriber.model is not None,
            "buffer_size": len(transcriber.transcription_buffer),
            "queue_size": transcriber.audio_queue.qsize(),
            "config": transcriber.config
        }
    })

@app.route('/api/audio/config', methods=['GET', 'POST'])
def manage_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify({
            "status": "success",
            "data": {
                "config": transcriber.config
            }
        })
    
    elif request.method == 'POST':
        try:
            new_config = request.get_json() or {}
            transcriber.update_config(new_config)
            return jsonify({
                "status": "success",
                "message": "Configuration updated",
                "data": {
                    "config": transcriber.config
                }
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

@app.route('/test')
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        "status": "success",
        "message": "ATC Audio Transcription Server is running",
        "whisper_model": "base" if transcriber.model else "not loaded",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🎙️  Starting ATC Audio Transcription Server")
    print("=" * 60)
    print("🎧 Audio Transcription API: http://localhost:8082/api/audio/")
    print("🎤 Device List: http://localhost:8082/api/audio/devices")
    print("📝 Transcriptions: http://localhost:8082/api/audio/transcriptions")
    print("🧪 Test: http://localhost:8082/test")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=8082, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        transcriber.stop_audio_capture()
        print("👋 Goodbye!")
