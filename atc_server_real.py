#!/usr/bin/env python3
"""
Real Live ATC Transcription Server
Actually transcribes live YouTube streams using Whisper AI
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import logging
import requests
import re
import subprocess
import tempfile
import os
import wave
import numpy as np
from io import BytesIO
import whisper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global ATC transcriber instance
atc_transcriber = None
transcriber_thread = None
stream_process = None

class RealATCTranscriber:
    """Real ATC transcriber that actually processes live YouTube streams with Whisper"""
    
    def __init__(self, youtube_url, airport_code="EGPF"):
        self.youtube_url = youtube_url
        self.airport_code = airport_code
        self.is_running = False
        self.transcription_history = []
        self.max_history = 100
        self.stream_process = None
        self.audio_buffer = []
        self.processing_interval = 30  # Process audio every 30 seconds
        
        # Load Whisper model (use base model for speed)
        logger.info("Loading Whisper model...")
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
        
        # Glasgow Airport specific information
        self.glasgow_info = {
            'icao': 'EGPF',
            'name': 'Glasgow Airport',
            'runways': ['05/23', '09/27'],
            'frequencies': {
                'tower': '118.1 MHz',
                'ground': '121.7 MHz',
                'approach': '119.1 MHz'
            },
            'elevation': '26 ft',
            'timezone': 'GMT/BST'
        }
        
        # Stream info
        self.stream_url = None
        self.stream_quality = None
        self.last_audio_chunk = None
        self.last_transcription_time = None
        
    def get_stream_info(self):
        """Get live stream information using yt-dlp"""
        try:
            logger.info(f"Getting stream info for: {self.youtube_url}")
            
            # Get stream URL
            result = subprocess.run([
                'yt-dlp', '--get-url', '--no-playlist', 
                '--format', 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                self.youtube_url
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.stream_url = result.stdout.strip().split('\n')[0]
                logger.info(f"Stream URL obtained: {self.stream_url[:100]}...")
                return True
            else:
                logger.error(f"Failed to get stream URL: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return False
    
    def start_live_stream(self):
        """Start processing the live stream"""
        if not self.get_stream_info():
            logger.error("Failed to get stream info")
            return False
        
        try:
            logger.info("Starting live stream processing...")
            
            # Start stream processing in background
            self.stream_thread = threading.Thread(target=self._process_live_stream)
            self.stream_thread.daemon = True
            self.stream_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting live stream: {e}")
            return False
    
    def _process_live_stream(self):
        """Background thread to process live stream audio"""
        while self.is_running:
            try:
                # Download a 30-second audio segment
                if self._download_audio_segment():
                    # Process the audio with Whisper
                    self._transcribe_audio()
                
                # Wait before next segment
                time.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in stream processing: {e}")
                time.sleep(10)  # Wait before retry
    
    def _download_audio_segment(self):
        """Download a segment of live audio"""
        try:
            if not self.stream_url:
                return False
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Download 30 seconds of audio using ffmpeg
            cmd = [
                'ffmpeg', '-i', self.stream_url,
                '-t', '30',  # 30 seconds
                '-c:a', 'pcm_s16le',  # Convert to WAV
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Audio segment downloaded successfully")
                self.last_audio_chunk = temp_path
                return True
            else:
                logger.error(f"Failed to download audio: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading audio segment: {e}")
            return False
    
    def _transcribe_audio(self):
        """Actually transcribe audio using Whisper"""
        try:
            if not self.whisper_model or not self.last_audio_chunk:
                return
            
            # Check if file exists and has content
            if not os.path.exists(self.last_audio_chunk) or os.path.getsize(self.last_audio_chunk) == 0:
                logger.warning("Audio file is empty or doesn't exist")
                return
            
            logger.info("Transcribing audio with Whisper...")
            
            # Transcribe the audio
            result = self.whisper_model.transcribe(
                self.last_audio_chunk,
                language="en",
                task="transcribe",
                verbose=False
            )
            
            if result and result.get('text', '').strip():
                text = result['text'].strip()
                confidence = result.get('avg_logprob', 0.0)
                
                logger.info(f"Transcription successful: {text[:100]}...")
                
                # Create transcription object
                transcription = {
                    'timestamp': datetime.now().isoformat(),
                    'raw_text': text,
                    'airport': self.airport_code,
                    'extracted_info': self.parse_atc_text(text),
                    'confidence': confidence,
                    'keywords_found': self.extract_keywords(text),
                    'source': 'live_stream_whisper',
                    'audio_file': self.last_audio_chunk,
                    'language': result.get('language', 'en'),
                    'segments': len(result.get('segments', []))
                }
                
                self.transcription_history.append(transcription)
                if len(self.transcription_history) > self.max_history:
                    self.transcription_history = self.transcription_history[-self.max_history:]
                
                self.last_transcription_time = datetime.now()
                
                # Clean up audio file
                try:
                    os.unlink(self.last_audio_chunk)
                except:
                    pass
                    
            else:
                logger.warning("Whisper returned empty transcription")
                
        except Exception as e:
            logger.error(f"Error in Whisper transcription: {e}")
            # Clean up audio file on error
            try:
                if self.last_audio_chunk and os.path.exists(self.last_audio_chunk):
                    os.unlink(self.last_audio_chunk)
            except:
                pass
    
    def parse_atc_text(self, text):
        """Parse ATC text for relevant aviation information"""
        text_lower = text.lower()
        
        extracted_info = {}
        
        # Extract runway information
        runway_patterns = [
            r'runway\s+(\d{2})',
            r'rwy\s+(\d{2})',
            r'(\d{2})\s+runway',
            r'approach\s+runway\s+(\d{2})',
            r'landing\s+runway\s+(\d{2})'
        ]
        
        for pattern in runway_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                extracted_info['runway'] = matches[0]
                break
        
        # Extract aircraft callsigns
        callsign_patterns = [
            r'([a-z]{3}\d{3,4})',
            r'([a-z]{2}\d{3,4})',
            r'([a-z]{1}\d{3,4})'
        ]
        
        callsigns = []
        for pattern in callsign_patterns:
            matches = re.findall(pattern, text_lower)
            callsigns.extend(matches)
        
        if callsigns:
            extracted_info['callsigns'] = list(set(callsigns))
        
        # Extract clearances
        clearance_keywords = ['cleared', 'permission', 'authorized', 'approved', 'denied', 'hold']
        clearances = []
        for keyword in clearance_keywords:
            if keyword in text_lower:
                sentences = re.split(r'[.!?]', text)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        clearances.append(sentence.strip())
                        break
        
        if clearances:
            extracted_info['clearances'] = clearances
        
        return extracted_info
    
    def extract_keywords(self, text):
        """Extract keywords from ATC text"""
        text_lower = text.lower()
        keywords = []
        
        if any(word in text_lower for word in ['runway', 'rwy', 'approach', 'departure', 'landing', 'takeoff']):
            keywords.append('runway')
        
        if any(word in text_lower for word in ['aircraft', 'plane', 'flight', 'callsign', 'registration']):
            keywords.append('aircraft')
        
        if any(word in text_lower for word in ['cleared', 'permission', 'authorized', 'approved', 'denied']):
            keywords.append('clearance')
        
        if any(word in text_lower for word in ['wind', 'visibility', 'ceiling', 'weather', 'conditions']):
            keywords.append('weather')
        
        return keywords
    
    def start(self):
        """Start the ATC transcription service"""
        if self.is_running:
            return False
        
        if not self.whisper_model:
            logger.error("Whisper model not loaded")
            return False
        
        self.is_running = True
        
        # Start live stream processing
        if self.start_live_stream():
            logger.info(f"Real ATC transcription service started for {self.airport_code}")
            return True
        else:
            logger.error("Failed to start live stream processing")
            self.is_running = False
            return False
    
    def stop(self):
        """Stop the ATC transcription service"""
        self.is_running = False
        
        # Stop stream processing
        if self.stream_process:
            try:
                self.stream_process.terminate()
                self.stream_process = None
            except:
                pass
        
        logger.info("Real ATC transcription service stopped")
    
    def get_stream_status(self):
        """Get detailed stream status"""
        return {
            'stream_url': self.stream_url,
            'stream_quality': self.stream_quality,
            'last_audio_chunk': self.last_audio_chunk,
            'processing_interval': self.processing_interval,
            'audio_buffer_size': len(self.audio_buffer),
            'whisper_model_loaded': self.whisper_model is not None,
            'last_transcription_time': self.last_transcription_time.isoformat() if self.last_transcription_time else None
        }
    
    def get_latest_transcriptions(self, limit=10):
        """Get latest transcriptions"""
        return self.transcription_history[-limit:] if self.transcription_history else []
    
    def get_transcription_stats(self):
        """Get transcription statistics"""
        if not self.transcription_history:
            return {
                'total_transcriptions': 0,
                'last_transcription': None,
                'keywords_found': {},
                'average_confidence': 0.0,
                'live_stream_active': self.is_running,
                'whisper_model_loaded': self.whisper_model is not None
            }
        
        # Count keywords found
        keyword_counts = {}
        for transcription in self.transcription_history:
            for keyword in transcription.get('keywords_found', []):
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Calculate average confidence
        confidences = [t.get('confidence', 0.0) for t in self.transcription_history]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'total_transcriptions': len(self.transcription_history),
            'last_transcription': self.transcription_history[-1]['timestamp'] if self.transcription_history else None,
            'keywords_found': keyword_counts,
            'average_confidence': avg_confidence,
            'live_stream_active': self.is_running,
            'whisper_model_loaded': self.whisper_model is not None
        }

# Flask routes
@app.route('/start', methods=['POST'])
def start_transcription():
    global atc_transcriber
    
    try:
        data = request.get_json() or {}
        youtube_url = data.get('youtube_url', 'https://www.youtube.com/watch?v=vrmJx8jCAjY')
        airport_code = data.get('airport_code', 'EGPF')
        
        if atc_transcriber:
            atc_transcriber.stop()
        
        atc_transcriber = RealATCTranscriber(youtube_url, airport_code)
        
        if atc_transcriber.start():
            return jsonify({
                'status': 'success',
                'message': f'Real ATC transcription started for {airport_code}',
                'youtube_url': youtube_url
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start ATC transcription'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting transcription: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/stop', methods=['POST'])
def stop_transcription():
    global atc_transcriber
    
    try:
        if atc_transcriber:
            atc_transcriber.stop()
            atc_transcriber = None
        
        return jsonify({
            'status': 'success',
            'message': 'ATC transcription stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping transcription: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    global atc_transcriber
    
    if not atc_transcriber:
        return jsonify({
            'status': 'stopped',
            'message': 'No ATC transcription service running'
        })
    
    return jsonify({
        'status': 'running' if atc_transcriber.is_running else 'stopped',
        'airport_code': atc_transcriber.airport_code,
        'youtube_url': atc_transcriber.youtube_url,
        'stream_status': atc_transcriber.get_stream_status(),
        'stats': atc_transcriber.get_transcription_stats()
    })

@app.route('/transcriptions', methods=['GET'])
def get_transcriptions():
    global atc_transcriber
    
    if not atc_transcriber:
        return jsonify({
            'status': 'success',
            'data': []
        })
    
    limit = request.args.get('limit', 10, type=int)
    transcriptions = atc_transcriber.get_latest_transcriptions(limit)
    
    return jsonify({
        'status': 'success',
        'data': transcriptions
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    global atc_transcriber
    
    if not atc_transcriber:
        return jsonify({
            'status': 'success',
            'data': {
                'total_transcriptions': 0,
                'live_stream_active': False,
                'whisper_model_loaded': False
            }
        })
    
    return jsonify({
        'status': 'success',
        'data': atc_transcriber.get_transcription_stats()
    })

@app.route('/stream-status', methods=['GET'])
def get_stream_status():
    global atc_transcriber
    
    if not atc_transcriber:
        return jsonify({
            'status': 'success',
            'data': {
                'stream_active': False,
                'whisper_model_loaded': False
            }
        })
    
    return jsonify({
        'status': 'success',
        'data': atc_transcriber.get_stream_status()
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Real ATC Transcription Server'
    })

if __name__ == '__main__':
    logger.info("Starting Real ATC Transcription Server...")
    app.run(host='0.0.0.0', port=8081, debug=False)
