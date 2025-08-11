#!/usr/bin/env python3
"""
Simple Coastline Server for Airspace Visualizer
Only serves coastline data - no aircraft data needed
"""

import time
import requests
from flask import Flask, jsonify, request
from regional_data import regional_manager

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Create Flask app
app = Flask(__name__)

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/api/coastline')
def get_coastline():
    """Get coastline data for a region within radar range"""
    try:
        lat = float(request.args.get('lat', 55.5094))
        lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 100))
        region_code = request.args.get('region', 'PRESTWICK')
        
        print(f"Loading coastline for {region_code} region at {lat:.4f}, {lon:.4f} within {range_nm}nm")
        
        # Generate coastline features using regional manager
        features = regional_manager.generate_geographic_features(
            lat, lon, range_nm, region_code
        )
        
        print(f"Loaded {len(features)} coastline points within {range_nm}nm of {lat:.4f}, {lon:.4f}")
        
        return jsonify({
            "status": "success",
            "data": {
                "features": features,
                "center": {"lat": lat, "lon": lon},
                "range_nm": range_nm,
                "region": region_code
            },
            "timestamp": time.time()
        })
    except Exception as e:
        print(f"Error generating coastline: {e}")
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": time.time()
        }), 400

@app.route('/api/regions')
def get_regions():
    """Get available regions"""
    try:
        regions = regional_manager.get_available_regions()
        return jsonify({
            "status": "success",
            "regions": regions,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": time.time()
        }), 400

@app.route('/test')
def test_endpoint():
    """Test endpoint to verify server is working"""
    return jsonify({"status": "server working", "timestamp": time.time()})

@app.route('/tmp/aircraft.json')
def proxy_aircraft():
    """Proxy PiAware aircraft data with CORS headers"""
    try:
        print("🔄 Fetching aircraft data from PiAware...")
        response = requests.get('http://10.0.0.20:8080/data/aircraft.json', timeout=5)
        print(f"📡 PiAware response: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        aircraft_count = len(data.get('aircraft', []))
        print(f"✈️  Successfully proxied {aircraft_count} aircraft from PiAware")
        
        # Return with CORS headers
        return jsonify(data)
    except Exception as e:
        print(f"❌ ERROR fetching aircraft data from PiAware: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "now": time.time(),
            "aircraft": [],
            "error": str(e)
        }), 503

if __name__ == "__main__":
    print("🗺️  Starting Coastline Server for Airspace Visualizer")
    print("=" * 60)
    print("📍 Coastline API: http://localhost:8080/api/coastline")
    print("🌍 Regions API: http://localhost:8080/api/regions")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
