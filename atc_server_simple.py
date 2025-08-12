#!/usr/bin/env python3
"""
Simple Live ATC Transcription Server
Better error handling and logging for debugging
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import logging
import subprocess
import tempfile
import os
import whisper
import signal
import sys

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('atc_server_simple.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global ATC transcriber instance
atc_transcriber = None

class SimpleATCTranscriber:
    """Simple ATC transcriber with robust error handling"""
    
    def __init__(self, youtube_url, airport_code="EGPF"):
        self.youtube_url = youtube_url
        self.airport_code = airport_code
        self.is_running = False
        self.transcription_history = []
        self.max_history = 50
        self.processing_interval = 30  # Process every 30 seconds
        
        # Load Whisper model
        logger.info("Loading Whisper model...")
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
        
        # Thread management
        self.stream_thread = None
        self.stop_event = threading.Event()
    
    def get_stream_info(self):
        """Get live stream information using yt-dlp"""
        try:
            logger.info(f"Getting stream info for: {self.youtube_url}")
            
            # Get stream URL with timeout
            result = subprocess.run([
                'yt-dlp', '--get-url', '--no-playlist', 
                '--format', 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                self.youtube_url
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                self.stream_url = result.stdout.strip().split('\n')[0]
                logger.info(f"Live stream URL obtained: {self.stream_url[:100]}...")
                return True
            else:
                logger.error(f"Failed to get stream URL: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp command timed out")
            return False
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return False
    
    def start(self):
        """Start the live ATC transcription service"""
        if self.is_running:
            logger.warning("Service already running")
            return False
        
        if not self.whisper_available:
            logger.error("Whisper model not loaded")
            return False
        
        # Get stream info first
        if not self.get_stream_info():
            logger.error("Failed to get live stream info")
            return False
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start live stream processing in background
        self.stream_thread = threading.Thread(target=self._process_live_stream)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        logger.info(f"Live ATC transcription service started for {self.airport_code}")
        return True
    
    def stop(self):
        """Stop the live ATC transcription service"""
        logger.info("Stopping ATC transcription service...")
        self.is_running = False
        self.stop_event.set()
        
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                logger.warning("Stream thread did not stop gracefully")
        
        logger.info("Live ATC transcription service stopped")
    
    def _process_live_stream(self):
        """Background thread to process live stream"""
        logger.info("Live stream processing thread started")
        
        while self.is_running and not self.stop_event.is_set():
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
                logger.info(f"Waiting {self.processing_interval} seconds before next segment...")
                if self.stop_event.wait(self.processing_interval):
                    logger.info("Stop event received, exiting processing loop")
                    break
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in live stream processing: {e}", exc_info=True)
                time.sleep(10)  # Wait before retry
        
        logger.info("Live stream processing thread ended")
    
    def _process_audio_segment(self):
        """Process a segment of live audio"""
        try:
            if not self.stream_url:
                logger.warning("No stream URL available")
                return False
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            logger.info(f"Downloading live audio segment to {temp_path}...")
            
            # Download 15 seconds of audio using ffmpeg with timeout
            cmd = [
                'ffmpeg', '-i', self.stream_url,
                '-t', '15',  # 15 seconds
                '-c:a', 'pcm_s16le',  # Convert to WAV
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                temp_path
            ]
            
            logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg with timeout
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                file_size = os.path.getsize(temp_path)
                logger.info(f"Live audio segment downloaded successfully: {file_size} bytes")
                
                # Transcribe the audio
                transcription = self._transcribe_audio(temp_path)
                
                # Clean up audio file
                try:
                    os.unlink(temp_path)
                    logger.info("Audio file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up audio file: {e}")
                
                return transcription is not None
            else:
                logger.error(f"Failed to download live audio: return code {result.returncode}")
                logger.error(f"ffmpeg stderr: {result.stderr.decode()}")
                
                # Clean up failed file
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up failed audio file: {e}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg command timed out")
            return False
        except Exception as e:
            logger.error(f"Error processing live audio segment: {e}", exc_info=True)
            return False
    
    def _transcribe_audio(self, audio_file_path):
        """Transcribe audio using Whisper"""
        try:
            if not self.whisper_model:
                logger.warning("No Whisper model available")
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
                    'confidence': confidence,
                    'source': 'live_youtube_stream',
                    'language': result.get('language', 'en')
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
            logger.error(f"Error in live Whisper transcription: {e}", exc_info=True)
            return None
    
    def get_status(self):
        """Get detailed status"""
        return {
            'youtube_url': self.youtube_url,
            'stream_url': self.stream_url,
            'processing_interval': self.processing_interval,
            'whisper_model_loaded': self.whisper_available,
            'last_transcription_time': self.last_transcription_time.isoformat() if self.last_transcription_time else None,
            'transcription_count': self.transcription_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'service_type': 'live_youtube_stream_whisper',
            'thread_alive': self.stream_thread.is_alive() if self.stream_thread else False
        }
    
    def get_latest_transcriptions(self, limit=10):
        """Get latest transcriptions"""
        return self.transcription_history[-limit:] if self.transcription_history else []

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
        
        atc_transcriber = SimpleATCTranscriber(youtube_url, airport_code)
        
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
        logger.error(f"Error starting live transcription: {e}", exc_info=True)
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
        logger.error(f"Error stopping live transcription: {e}", exc_info=True)
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
        'details': atc_transcriber.get_status()
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

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Simple Live ATC Transcription Server',
        'features': [
            'Live YouTube stream processing',
            'Real-time Whisper AI transcription',
            'Robust error handling and logging',
            'Thread management'
        ]
    })

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if atc_transcriber:
        atc_transcriber.stop()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    logger.info("Starting Simple Live ATC Transcription Server...")
    app.run(host='0.0.0.0', port=8081, debug=False)
