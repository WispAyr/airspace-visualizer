#!/usr/bin/env python3
"""
Live Real ATC Transcription Server
Actually processes live YouTube streams for real ATC traffic
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
import whisper
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global ATC transcriber instance
atc_transcriber = None

class LiveRealATCTranscriber:
    """Live ATC transcriber that actually processes real YouTube streams"""
    
    def __init__(self, youtube_url, airport_code="EGPF"):
        self.youtube_url = youtube_url
        self.airport_code = airport_code
        self.is_running = False
        self.transcription_history = []
        self.max_history = 100
        self.processing_interval = 20  # Process every 20 seconds
        
        # Load Whisper model
        logger.info("Loading Whisper model for live transcription...")
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
            self.whisper_available = True
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
            self.whisper_available = False
        
        # Stream info
        self.stream_url = None
        self.last_transcription_time = None
        self.transcription_count = 0
        self.error_count = 0
        self.success_count = 0
        
        # Glasgow Airport info
        self.glasgow_info = {
            'icao': 'EGPF',
            'name': 'Glasgow Airport',
            'runways': ['05/23', '09/27'],
            'frequencies': {
                'tower': '118.1 MHz',
                'ground': '121.7 MHz',
                'approach': '119.1 MHz'
            }
        }
    
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
                logger.info(f"Live stream URL obtained: {self.stream_url[:100]}...")
                return True
            else:
                logger.error(f"Failed to get stream URL: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return False
    
    def start(self):
        """Start the live ATC transcription service"""
        if self.is_running:
            return False
        
        if not self.whisper_available:
            logger.error("Whisper model not loaded")
            return False
        
        # Get stream info first
        if not self.get_stream_info():
            logger.error("Failed to get live stream info")
            return False
        
        self.is_running = True
        
        # Start live stream processing in background
        self.stream_thread = threading.Thread(target=self._process_live_stream)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        logger.info(f"Live ATC transcription service started for {self.airport_code}")
        return True
    
    def stop(self):
        """Stop the live ATC transcription service"""
        self.is_running = False
        logger.info("Live ATC transcription service stopped")
    
    def _process_live_stream(self):
        """Background thread to process live stream"""
        while self.is_running:
            try:
                logger.info("Processing live stream segment...")
                
                # Download and transcribe audio segment
                if self._process_audio_segment():
                    self.success_count += 1
                    logger.info(f"Live transcription successful (success: {self.success_count}, errors: {self.error_count})")
                else:
                    self.error_count += 1
                    logger.warning(f"Live transcription failed (success: {self.success_count}, errors: {self.error_count})")
                
                # Wait before next segment
                time.sleep(self.processing_interval)
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in live stream processing: {e}")
                time.sleep(10)  # Wait before retry
    
    def _process_audio_segment(self):
        """Process a segment of live audio"""
        try:
            if not self.stream_url:
                logger.warning("No stream URL available")
                return False
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Download 20 seconds of audio using ffmpeg
            cmd = [
                'ffmpeg', '-i', self.stream_url,
                '-t', '20',  # 20 seconds
                '-c:a', 'pcm_s16le',  # Convert to WAV
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                temp_path
            ]
            
            logger.info("Downloading live audio segment...")
            result = subprocess.run(cmd, capture_output=True, timeout=45)
            
            if result.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                logger.info("Live audio segment downloaded successfully")
                
                # Transcribe the audio
                transcription = self._transcribe_audio(temp_path)
                
                # Clean up audio file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                return transcription is not None
            else:
                logger.error(f"Failed to download live audio: {result.stderr}")
                # Clean up failed file
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"Error processing live audio segment: {e}")
            return False
    
    def _transcribe_audio(self, audio_file_path):
        """Transcribe audio using Whisper"""
        try:
            if not self.whisper_model:
                return None
            
            logger.info("Transcribing live audio with Whisper...")
            
            # Transcribe the audio
            result = self.whisper_model.transcribe(
                audio_file_path,
                language="en",
                task="transcribe",
                verbose=False
            )
            
            if result and result.get('text', '').strip():
                text = result['text'].strip()
                confidence = result.get('avg_logprob', 0.0)
                
                logger.info(f"Live transcription: {text[:100]}...")
                
                # Create transcription object
                transcription = {
                    'timestamp': datetime.now().isoformat(),
                    'raw_text': text,
                    'airport': self.airport_code,
                    'extracted_info': self.parse_atc_text(text),
                    'confidence': confidence,
                    'keywords_found': self.extract_keywords(text),
                    'source': 'live_youtube_stream',
                    'language': result.get('language', 'en'),
                    'segments': len(result.get('segments', [])),
                    'audio_file': audio_file_path
                }
                
                self.transcription_history.append(transcription)
                if len(self.transcription_history) > self.max_history:
                    self.transcription_history = self.transcription_history[-self.max_history:]
                
                self.last_transcription_time = datetime.now()
                self.transcription_count += 1
                
                return transcription
            else:
                logger.warning("Whisper returned empty transcription from live stream")
                return None
                
        except Exception as e:
            logger.error(f"Error in live Whisper transcription: {e}")
            return None
    
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
    
    def get_stream_status(self):
        """Get detailed stream status"""
        return {
            'youtube_url': self.youtube_url,
            'stream_url': self.stream_url,
            'processing_interval': self.processing_interval,
            'whisper_model_loaded': self.whisper_available,
            'last_transcription_time': self.last_transcription_time.isoformat() if self.last_transcription_time else None,
            'transcription_count': self.transcription_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'service_type': 'live_youtube_stream_whisper'
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
                'whisper_model_loaded': self.whisper_available,
                'success_rate': 0.0,
                'service_type': 'live_youtube_stream_whisper'
            }
        
        # Count keywords found
        keyword_counts = {}
        for transcription in self.transcription_history:
            for keyword in transcription.get('keywords_found', []):
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Calculate average confidence
        confidences = [t.get('confidence', 0.0) for t in self.transcription_history]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate success rate
        total_attempts = self.success_count + self.error_count
        success_rate = (self.success_count / total_attempts * 100) if total_attempts > 0 else 0.0
        
        return {
            'total_transcriptions': len(self.transcription_history),
            'last_transcription': self.transcription_history[-1]['timestamp'] if self.transcription_history else None,
            'keywords_found': keyword_counts,
            'average_confidence': avg_confidence,
            'live_stream_active': self.is_running,
            'whisper_model_loaded': self.whisper_available,
            'success_rate': success_rate,
            'service_type': 'live_youtube_stream_whisper'
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
        
        atc_transcriber = LiveRealATCTranscriber(youtube_url, airport_code)
        
        if atc_transcriber.start():
            return jsonify({
                'status': 'success',
                'message': f'Live ATC transcription started for {airport_code}',
                'youtube_url': youtube_url,
                'service_type': 'live_youtube_stream_whisper'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start live ATC transcription'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting live transcription: {e}")
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
            'message': 'Live ATC transcription stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping live transcription: {e}")
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
            'message': 'No live ATC transcription service running'
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
        'service': 'Live Real ATC Transcription Server',
        'features': [
            'Live YouTube stream processing',
            'Real-time Whisper AI transcription',
            'Live Glasgow Airport ATC traffic',
            'Robust error handling and recovery'
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Live Real ATC Transcription Server...")
    app.run(host='0.0.0.0', port=8081, debug=False)
