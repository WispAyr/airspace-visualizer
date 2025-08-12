#!/usr/bin/env python3
"""
Live ATC Transcriber for Glasgow Airport
Uses Whisper to transcribe live YouTube ATC streams and integrate with aviation radar
"""

import os
import time
import json
import threading
import queue
import re
from datetime import datetime, timedelta
import requests
from urllib.parse import urlparse, parse_qs
import whisper
import torch
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ATCTranscriber:
    def __init__(self, youtube_url, airport_code="EGPF", model_size="base"):
        """
        Initialize ATC Transcriber
        
        Args:
            youtube_url: YouTube stream URL
            airport_code: ICAO airport code (default: EGPF for Glasgow)
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.youtube_url = youtube_url
        self.airport_code = airport_code
        self.model_size = model_size
        self.is_running = False
        self.transcription_queue = queue.Queue()
        self.audio_buffer = []
        self.whisper_model = None
        self.transcription_history = []
        self.max_history = 100
        
        # ATC-specific keywords and patterns
        self.atc_keywords = {
            'runway': ['runway', 'rwy', 'approach', 'departure', 'landing', 'takeoff'],
            'aircraft': ['aircraft', 'plane', 'flight', 'callsign', 'registration'],
            'clearance': ['cleared', 'permission', 'authorized', 'approved', 'denied'],
            'weather': ['wind', 'visibility', 'ceiling', 'weather', 'conditions'],
            'traffic': ['traffic', 'conflict', 'separation', 'spacing', 'hold'],
            'emergency': ['emergency', 'mayday', 'pan', 'priority', 'urgent']
        }
        
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
        
    def load_whisper_model(self):
        """Load Whisper model for transcription"""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.whisper_model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False
    
    def extract_youtube_stream_info(self):
        """Extract stream information from YouTube URL"""
        try:
            # Parse YouTube URL
            parsed_url = urlparse(self.youtube_url)
            if 'youtube.com' not in parsed_url.netloc:
                raise ValueError("Not a valid YouTube URL")
            
            # Extract video ID
            if 'watch' in parsed_url.path:
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [None])[0]
            else:
                video_id = parsed_url.path.split('/')[-1]
            
            if not video_id:
                raise ValueError("Could not extract video ID")
            
            logger.info(f"Extracted YouTube video ID: {video_id}")
            return video_id
            
        except Exception as e:
            logger.error(f"Failed to extract YouTube stream info: {e}")
            return None
    
    def download_audio_segment(self, duration_seconds=30):
        """
        Download audio segment from YouTube stream
        This is a simplified version - in production you'd use yt-dlp or similar
        """
        try:
            # For now, we'll simulate audio download
            # In production, you'd implement actual YouTube audio extraction
            logger.info(f"Downloading {duration_seconds}s audio segment from YouTube stream")
            
            # Simulate audio data (replace with actual implementation)
            audio_data = np.random.rand(16000 * duration_seconds)  # 16kHz sample rate
            return audio_data
            
        except Exception as e:
            logger.error(f"Failed to download audio segment: {e}")
            return None
    
    def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper"""
        try:
            if self.whisper_model is None:
                logger.error("Whisper model not loaded")
                return None
            
            # Convert audio data to appropriate format for Whisper
            # This depends on the actual audio format from YouTube
            audio_segment = AudioSegment.from_numpy_array(audio_data, sample_rate=16000)
            
            # Save temporary audio file for Whisper
            temp_file = f"temp_audio_{int(time.time())}.wav"
            audio_segment.export(temp_file, format="wav")
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(temp_file)
            
            # Clean up temp file
            os.remove(temp_file)
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def parse_atc_transcription(self, transcription_text):
        """Parse ATC transcription for relevant aviation information"""
        if not transcription_text:
            return None
        
        parsed_info = {
            'timestamp': datetime.now().isoformat(),
            'raw_text': transcription_text,
            'airport': self.airport_code,
            'extracted_info': {},
            'confidence': 0.0,
            'keywords_found': []
        }
        
        # Convert to lowercase for keyword matching
        text_lower = transcription_text.lower()
        
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
                parsed_info['extracted_info']['runway'] = matches[0]
                parsed_info['keywords_found'].append('runway')
                break
        
        # Extract aircraft callsigns
        callsign_patterns = [
            r'([a-z]{3}\d{3,4})',  # Standard callsign format
            r'([a-z]{2}\d{3,4})',  # Short callsign format
            r'([a-z]{1}\d{3,4})',  # Single letter prefix
        ]
        
        callsigns = []
        for pattern in callsign_patterns:
            matches = re.findall(pattern, text_lower)
            callsigns.extend(matches)
        
        if callsigns:
            parsed_info['extracted_info']['callsigns'] = list(set(callsigns))
            parsed_info['keywords_found'].append('aircraft')
        
        # Extract clearances and permissions
        clearance_keywords = ['cleared', 'permission', 'authorized', 'approved', 'denied']
        clearances = []
        for keyword in clearance_keywords:
            if keyword in text_lower:
                # Extract the sentence containing the keyword
                sentences = re.split(r'[.!?]', transcription_text)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        clearances.append(sentence.strip())
                        break
        
        if clearances:
            parsed_info['extracted_info']['clearances'] = clearances
            parsed_info['keywords_found'].append('clearance')
        
        # Extract weather information
        weather_keywords = ['wind', 'visibility', 'ceiling', 'weather', 'conditions']
        weather_info = []
        for keyword in weather_keywords:
            if keyword in text_lower:
                sentences = re.split(r'[.!?]', transcription_text)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        weather_info.append(sentence.strip())
                        break
        
        if weather_info:
            parsed_info['extracted_info']['weather'] = weather_info
            parsed_info['keywords_found'].append('weather')
        
        # Calculate confidence based on keywords found
        total_keywords = sum(len(keywords) for keywords in self.atc_keywords.values())
        parsed_info['confidence'] = len(parsed_info['keywords_found']) / total_keywords
        
        return parsed_info
    
    def process_transcription(self, transcription_result):
        """Process and store transcription results"""
        if not transcription_result or 'text' not in transcription_result:
            return None
        
        transcription_text = transcription_result['text'].strip()
        if not transcription_text:
            return None
        
        # Parse ATC-specific information
        parsed_info = self.parse_atc_transcription(transcription_text)
        if parsed_info:
            # Add to history
            self.transcription_history.append(parsed_info)
            
            # Keep only recent history
            if len(self.transcription_history) > self.max_history:
                self.transcription_history = self.transcription_history[-self.max_history:]
            
            # Add to processing queue
            self.transcription_queue.put(parsed_info)
            
            logger.info(f"Processed ATC transcription: {transcription_text[:100]}...")
            return parsed_info
        
        return None
    
    def start_transcription_loop(self):
        """Main transcription loop"""
        logger.info(f"Starting ATC transcription for {self.airport_code}")
        
        while self.is_running:
            try:
                # Download audio segment
                audio_data = self.download_audio_segment(duration_seconds=30)
                if audio_data is not None:
                    # Transcribe audio
                    transcription_result = self.transcribe_audio(audio_data)
                    if transcription_result:
                        # Process transcription
                        self.process_transcription(transcription_result)
                
                # Wait before next segment
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in transcription loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def start(self):
        """Start the ATC transcription service"""
        if self.is_running:
            logger.warning("ATC transcription service already running")
            return False
        
        # Load Whisper model
        if not self.load_whisper_model():
            return False
        
        # Extract YouTube stream info
        video_id = self.extract_youtube_stream_info()
        if not video_id:
            return False
        
        self.is_running = True
        
        # Start transcription thread
        transcription_thread = threading.Thread(target=self.start_transcription_loop)
        transcription_thread.daemon = True
        transcription_thread.start()
        
        logger.info(f"ATC transcription service started for {self.airport_code}")
        return True
    
    def stop(self):
        """Stop the ATC transcription service"""
        self.is_running = False
        logger.info("ATC transcription service stopped")
    
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
                'average_confidence': 0.0
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
            'average_confidence': avg_confidence
        }
    
    def export_transcriptions(self, filename=None):
        """Export transcriptions to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"atc_transcriptions_{self.airport_code}_{timestamp}.json"
        
        try:
            export_data = {
                'airport_code': self.airport_code,
                'export_timestamp': datetime.now().isoformat(),
                'transcriptions': self.transcription_history,
                'stats': self.get_transcription_stats()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Transcriptions exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to export transcriptions: {e}")
            return None

def main():
    """Main function for testing"""
    # Glasgow Airport ATC stream
    youtube_url = "https://www.youtube.com/watch?v=vrmJx8jCAjY"
    
    # Create transcriber
    transcriber = ATCTranscriber(youtube_url, airport_code="EGPF", model_size="base")
    
    try:
        # Start transcription
        if transcriber.start():
            logger.info("ATC transcription service started successfully")
            
            # Run for a few minutes to test
            time.sleep(300)  # 5 minutes
            
            # Get stats
            stats = transcriber.get_transcription_stats()
            logger.info(f"Transcription stats: {stats}")
            
            # Export transcriptions
            transcriber.export_transcriptions()
            
        else:
            logger.error("Failed to start ATC transcription service")
    
    except KeyboardInterrupt:
        logger.info("Stopping ATC transcription service...")
    finally:
        transcriber.stop()

if __name__ == "__main__":
    main()
