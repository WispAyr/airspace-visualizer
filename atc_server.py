#!/usr/bin/env python3
"""
ATC Transcription Server
Flask server to integrate live ATC transcriptions with the aviation radar system
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import logging
from atc_transcriber_enhanced import EnhancedATCTranscriber

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global ATC transcriber instance
atc_transcriber = None
transcriber_thread = None

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        "service": "ATC Transcription Server",
        "status": "running",
        "endpoints": {
            "/": "This help message",
            "/start": "Start ATC transcription",
            "/stop": "Stop ATC transcription",
            "/status": "Get transcription status",
            "/transcriptions": "Get latest transcriptions",
            "/stats": "Get transcription statistics",
            "/export": "Export transcriptions to JSON"
        }
    })

@app.route('/start', methods=['POST'])
def start_transcription():
    """Start ATC transcription service"""
    global atc_transcriber, transcriber_thread
    
    try:
        data = request.get_json() or {}
        youtube_url = data.get('youtube_url', 'https://www.youtube.com/watch?v=vrmJx8jCAjY')
        airport_code = data.get('airport_code', 'EGPF')
        model_size = data.get('model_size', 'base')
        
        if atc_transcriber and atc_transcriber.is_running:
            return jsonify({
                "status": "error",
                "message": "ATC transcription service already running"
            }), 400
        
        # Create new transcriber
        atc_transcriber = EnhancedATCTranscriber(
            youtube_url=youtube_url,
            airport_code=airport_code,
            model_size=model_size
        )
        
        # Start transcription in background thread
        def run_transcriber():
            atc_transcriber.start()
        
        transcriber_thread = threading.Thread(target=run_transcriber)
        transcriber_thread.daemon = True
        transcriber_thread.start()
        
        # Wait a moment for service to start
        time.sleep(2)
        
        if atc_transcriber.is_running:
            return jsonify({
                "status": "success",
                "message": f"ATC transcription service started for {airport_code}",
                "youtube_url": youtube_url,
                "airport_code": airport_code,
                "model_size": model_size
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to start ATC transcription service"
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting transcription: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to start transcription: {str(e)}"
        }), 500

@app.route('/stop', methods=['POST'])
def stop_transcription():
    """Stop ATC transcription service"""
    global atc_transcriber
    
    try:
        if atc_transcriber and atc_transcriber.is_running:
            atc_transcriber.stop()
            return jsonify({
                "status": "success",
                "message": "ATC transcription service stopped"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No ATC transcription service running"
            }), 400
            
    except Exception as e:
        logger.error(f"Error stopping transcription: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to stop transcription: {str(e)}"
        }), 500

@app.route('/status')
def get_status():
    """Get transcription service status"""
    global atc_transcriber
    
    try:
        if not atc_transcriber:
            return jsonify({
                "status": "stopped",
                "message": "No ATC transcription service configured",
                "airport_code": None,
                "youtube_url": None,
                "is_running": False
            })
        
        return jsonify({
            "status": "running" if atc_transcriber.is_running else "stopped",
            "airport_code": atc_transcriber.airport_code,
            "youtube_url": atc_transcriber.youtube_url,
            "is_running": atc_transcriber.is_running,
            "model_size": atc_transcriber.model_size,
            "transcription_count": len(atc_transcriber.transcription_history) if atc_transcriber.transcription_history else 0
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get status: {str(e)}"
        }), 500

@app.route('/transcriptions')
def get_transcriptions():
    """Get latest transcriptions"""
    global atc_transcriber
    
    try:
        if not atc_transcriber:
            return jsonify({
                "status": "error",
                "message": "No ATC transcription service configured"
            }), 400
        
        limit = request.args.get('limit', 10, type=int)
        transcriptions = atc_transcriber.get_latest_transcriptions(limit=limit)
        
        return jsonify({
            "status": "success",
            "airport_code": atc_transcriber.airport_code,
            "transcriptions": transcriptions,
            "count": len(transcriptions)
        })
        
    except Exception as e:
        logger.error(f"Error getting transcriptions: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get transcriptions: {str(e)}"
        }), 500

@app.route('/stats')
def get_stats():
    """Get transcription statistics"""
    global atc_transcriber
    
    try:
        if not atc_transcriber:
            return jsonify({
                "status": "error",
                "message": "No ATC transcription service configured"
            }), 400
        
        stats = atc_transcriber.get_transcription_stats()
        
        return jsonify({
            "status": "success",
            "airport_code": atc_transcriber.airport_code,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get stats: {str(e)}"
        }), 500

@app.route('/export')
def export_transcriptions():
    """Export transcriptions to JSON file"""
    global atc_transcriber
    
    try:
        if not atc_transcriber:
            return jsonify({
                "status": "error",
                "message": "No ATC transcription service configured"
            }), 400
        
        filename = request.args.get('filename', None)
        exported_file = atc_transcriber.export_transcriptions(filename)
        
        if exported_file:
            return jsonify({
                "status": "success",
                "message": "Transcriptions exported successfully",
                "filename": exported_file
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to export transcriptions"
            }), 500
        
    except Exception as e:
        logger.error(f"Error exporting transcriptions: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to export transcriptions: {str(e)}"
        }), 500

@app.route('/search')
def search_transcriptions():
    """Search transcriptions by keyword or content"""
    global atc_transcriber
    
    try:
        if not atc_transcriber:
            return jsonify({
                "status": "error",
                "message": "No ATC transcription service configured"
            }), 400
        
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({
                "status": "error",
                "message": "Search query required"
            }), 400
        
        # Search through transcriptions
        results = []
        for transcription in atc_transcriber.transcription_history:
            if (query in transcription['raw_text'].lower() or
                any(query in str(v).lower() for v in transcription['extracted_info'].values())):
                results.append(transcription)
        
        return jsonify({
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching transcriptions: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to search transcriptions: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    global atc_transcriber
    
    try:
        health_status = {
            "service": "ATC Transcription Server",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "transcriber_running": atc_transcriber.is_running if atc_transcriber else False,
            "transcription_count": len(atc_transcriber.transcription_history) if atc_transcriber and atc_transcriber.transcription_history else 0
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "service": "ATC Transcription Server",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting ATC Transcription Server...")
    app.run(host='0.0.0.0', port=8081, debug=False)
