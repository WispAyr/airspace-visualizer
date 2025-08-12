#!/usr/bin/env python3
"""
Robust ATC Transcription Server
Provides real transcription with fallback to simulated data
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
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global ATC transcriber instance
atc_transcriber = None
transcriber_thread = None

class RobustATCTranscriber:
    """Robust ATC transcriber with real Whisper capabilities and fallback"""
    
    def __init__(self, airport_code="EGPF"):
        self.airport_code = airport_code
        self.is_running = False
        self.transcription_history = []
        self.max_history = 100
        self.processing_interval = 15  # Process every 15 seconds
        
        # Load Whisper model (use base model for speed)
        logger.info("Loading Whisper model...")
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
            self.whisper_available = True
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
            self.whisper_available = False
        
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
        
        # Real ATC phrases for realistic simulation
        self.real_atc_phrases = [
            "Glasgow Tower, EZY1234, cleared for takeoff runway 23",
            "BA1234, wind 230 at 15 knots, cleared to land runway 23",
            "EZY5678, hold short of runway 05, traffic on final",
            "Glasgow Ground, EZY9999, request pushback",
            "EZY9999, pushback approved, contact tower on 118.1",
            "EZY1234, climb to flight level 60, turn right heading 090",
            "BA1234, descend to flight level 30, expect runway 23",
            "EZY5678, maintain 3000 feet, join left downwind runway 23",
            "Glasgow Approach, EZY9999, request radar vectors",
            "EZY9999, turn left heading 270, climb to 4000 feet",
            "BA1234, contact Glasgow Tower on 118.1, good day",
            "EZY1234, cleared visual approach runway 23, report final",
            "Glasgow Ground, EZY5678, request taxi to runway 23",
            "EZY5678, taxi to runway 23 via Alpha, hold short",
            "BA1234, wind check, 250 at 12 knots",
            "EZY9999, cleared for takeoff runway 23, wind 250 at 12",
            "Glasgow Tower, EZY1234, runway 23 clear for landing",
            "EZY5678, go around, climb to 3000 feet, turn right",
            "BA1234, contact Glasgow Ground on 121.7 when clear",
            "EZY9999, maintain 2000 feet, expect approach runway 23"
        ]
        
        self.last_transcription_time = None
        self.transcription_count = 0
        
    def start(self):
        """Start the ATC transcription service"""
        if self.is_running:
            return False
        
        self.is_running = True
        
        # Start transcription processing in background
        self.transcription_thread = threading.Thread(target=self._process_transcriptions)
        self.transcription_thread.daemon = True
        self.transcription_thread.start()
        
        logger.info(f"Robust ATC transcription service started for {self.airport_code}")
        return True
    
    def stop(self):
        """Stop the ATC transcription service"""
        self.is_running = False
        logger.info("Robust ATC transcription service stopped")
    
    def _process_transcriptions(self):
        """Background thread to process transcriptions"""
        while self.is_running:
            try:
                # Generate realistic ATC transcription
                self._generate_realistic_transcription()
                
                # Wait before next transcription
                time.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in transcription processing: {e}")
                time.sleep(10)  # Wait before retry
    
    def _generate_realistic_transcription(self):
        """Generate realistic ATC transcription"""
        try:
            # Select a random ATC phrase
            text = random.choice(self.real_atc_phrases)
            
            # Add some variation to make it more realistic
            if random.random() < 0.3:  # 30% chance to add noise
                text += f" {random.choice(['over', 'out', 'roger', 'wilco'])}"
            
            # Create transcription object
            transcription = {
                'timestamp': datetime.now().isoformat(),
                'raw_text': text,
                'airport': self.airport_code,
                'extracted_info': self.parse_atc_text(text),
                'confidence': random.uniform(0.85, 0.98),  # High confidence for simulated
                'keywords_found': self.extract_keywords(text),
                'source': 'realistic_simulation',
                'language': 'en',
                'segments': 1
            }
            
            self.transcription_history.append(transcription)
            if len(self.transcription_history) > self.max_history:
                self.transcription_history = self.transcription_history[-self.max_history:]
            
            self.last_transcription_time = datetime.now()
            self.transcription_count += 1
            
            logger.info(f"Generated transcription {self.transcription_count}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error generating transcription: {e}")
    
    def transcribe_audio_file(self, audio_file_path):
        """Actually transcribe an audio file using Whisper"""
        try:
            if not self.whisper_available or not self.whisper_model:
                return None
            
            if not os.path.exists(audio_file_path):
                logger.warning(f"Audio file not found: {audio_file_path}")
                return None
            
            logger.info(f"Transcribing audio file: {audio_file_path}")
            
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
                
                logger.info(f"Whisper transcription successful: {text[:100]}...")
                
                # Create transcription object
                transcription = {
                    'timestamp': datetime.now().isoformat(),
                    'raw_text': text,
                    'airport': self.airport_code,
                    'extracted_info': self.parse_atc_text(text),
                    'confidence': confidence,
                    'keywords_found': self.extract_keywords(text),
                    'source': 'whisper_audio_file',
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
                logger.warning("Whisper returned empty transcription")
                return None
                
        except Exception as e:
            logger.error(f"Error in Whisper transcription: {e}")
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
            'processing_interval': self.processing_interval,
            'whisper_model_loaded': self.whisper_available,
            'last_transcription_time': self.last_transcription_time.isoformat() if self.last_transcription_time else None,
            'transcription_count': self.transcription_count,
            'service_type': 'robust_simulation_with_whisper_fallback'
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
                'service_active': self.is_running,
                'whisper_model_loaded': self.whisper_available,
                'service_type': 'robust_simulation_with_whisper_fallback'
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
            'service_active': self.is_running,
            'whisper_model_loaded': self.whisper_available,
            'service_type': 'robust_simulation_with_whisper_fallback'
        }

# Flask routes
@app.route('/start', methods=['POST'])
def start_transcription():
    global atc_transcriber
    
    try:
        data = request.get_json() or {}
        airport_code = data.get('airport_code', 'EGPF')
        
        if atc_transcriber:
            atc_transcriber.stop()
        
        atc_transcriber = RobustATCTranscriber(airport_code)
        
        if atc_transcriber.start():
            return jsonify({
                'status': 'success',
                'message': f'Robust ATC transcription started for {airport_code}',
                'service_type': 'robust_simulation_with_whisper_fallback'
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
                'service_active': False,
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
                'service_active': False,
                'whisper_model_loaded': False
            }
        })
    
    return jsonify({
        'status': 'success',
        'data': atc_transcriber.get_stream_status()
    })

@app.route('/transcribe-file', methods=['POST'])
def transcribe_audio_file():
    """Endpoint to transcribe an uploaded audio file"""
    global atc_transcriber
    
    if not atc_transcriber:
        return jsonify({
            'status': 'error',
            'message': 'No ATC transcription service running'
        }), 400
    
    try:
        if 'audio_file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio_file']
        if audio_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No audio file selected'
            }), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Transcribe the audio file
        transcription = atc_transcriber.transcribe_audio_file(temp_path)
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if transcription:
            return jsonify({
                'status': 'success',
                'message': 'Audio file transcribed successfully',
                'data': transcription
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to transcribe audio file'
            }), 500
            
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Robust ATC Transcription Server',
        'features': [
            'Realistic ATC simulation',
            'Whisper AI transcription (when available)',
            'Audio file transcription',
            'Robust error handling'
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Robust ATC Transcription Server...")
    app.run(host='0.0.0.0', port=8081, debug=False)
