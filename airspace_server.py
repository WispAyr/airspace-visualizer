#!/usr/bin/env python3
"""
Enhanced Airspace Server with UK Airspace Integration
Combines aircraft proxy, coastline data, and UK airspace services
"""

import time
import requests
import traceback
from flask import Flask, jsonify, request
from regional_data import regional_manager
from airspace_parser import UKAirspaceParser

# Initialize Flask app
app = Flask(__name__)

# Initialize airspace parser
print("🗺️  Initializing UK Airspace Parser...")
airspace_parser = UKAirspaceParser()
airspace_parser.parse_all_airspace()
print("✅ Airspace parser ready")

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/api/coastline')
def get_coastline():
    """Get coastline data for a given region and range."""
    try:
        center_lat = float(request.args.get('lat', 55.5094))
        center_lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 50))
        region_code = request.args.get('region', 'PRESTWICK')

        features = regional_manager.generate_geographic_features(center_lat, center_lon, range_nm, region_code)
        print(f"🗺️  Loaded {len(features)} coastline points within {range_nm}nm of {center_lat:.4f}, {center_lon:.4f}")

        return jsonify({
            "status": "success",
            "data": {"features": features},
            "timestamp": time.time()
        })
    except Exception as e:
        print(f"❌ Error generating coastline data: {e}")
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

@app.route('/api/airspace')
def get_airspace():
    """Get airspace data for radar visualization"""
    try:
        center_lat = float(request.args.get('lat', 55.5094))
        center_lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 50))
        
        print(f"🛩️  Loading airspace within {range_nm}nm of {center_lat:.4f}, {center_lon:.4f}")
        
        # Get airspace data for visualization
        airspace_data = airspace_parser.export_for_visualization(center_lat, center_lon, range_nm)
        
        print(f"✅ Loaded {airspace_data['summary']['total_zones']} airspace zones")
        
        return jsonify({
            "status": "success",
            "data": airspace_data,
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Error loading airspace data: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }), 400

@app.route('/api/airspace/identify')
def identify_airspace():
    """Identify airspace for a specific position"""
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        altitude = request.args.get('altitude', type=int)
        
        print(f"🔍 Identifying airspace for position {lat:.4f}, {lon:.4f}")
        
        # Find airspace zones
        zones = airspace_parser.find_airspace_for_position(lat, lon)
        
        # Get AI-friendly description
        ai_description = airspace_parser.get_airspace_info_for_ai(lat, lon, altitude)
        
        zone_data = []
        for zone in zones:
            zone_data.append({
                "name": zone.name,
                "type": zone.type,
                "description": zone.description,
                "altitude_min": zone.altitude_min,
                "altitude_max": zone.altitude_max
            })
        
        return jsonify({
            "status": "success",
            "data": {
                "position": {"lat": lat, "lon": lon, "altitude": altitude},
                "zones": zone_data,
                "ai_description": ai_description,
                "zone_count": len(zones)
            },
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Error identifying airspace: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }), 400

@app.route('/tmp/aircraft.json')
def proxy_aircraft():
    """Proxy PiAware aircraft data with CORS headers and airspace identification"""
    try:
        print("🔄 Fetching aircraft data from PiAware...")
        response = requests.get('http://10.0.0.20:8080/data/aircraft.json', timeout=5)
        print(f"📡 PiAware response: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        aircraft_count = len(data.get('aircraft', []))
        
        # Enhance aircraft data with airspace information
        enhanced_aircraft = []
        for aircraft in data.get('aircraft', []):
            enhanced_ac = aircraft.copy()
            
            # Add airspace information if position is available
            if aircraft.get('lat') and aircraft.get('lon'):
                try:
                    zones = airspace_parser.find_airspace_for_position(
                        aircraft['lat'], aircraft['lon']
                    )
                    
                    if zones:
                        # Add the most relevant airspace (highest priority)
                        primary_zone = zones[0]
                        enhanced_ac['airspace'] = {
                            'name': primary_zone.name,
                            'type': primary_zone.type,
                            'description': primary_zone.description
                        }
                        enhanced_ac['airspace_zones'] = len(zones)
                    else:
                        enhanced_ac['airspace'] = {
                            'name': 'Uncontrolled',
                            'type': 'Class G',
                            'description': 'Uncontrolled airspace'
                        }
                        enhanced_ac['airspace_zones'] = 0
                        
                except Exception as e:
                    print(f"⚠️  Error identifying airspace for aircraft {aircraft.get('hex', 'unknown')}: {e}")
                    enhanced_ac['airspace'] = None
                    
            enhanced_aircraft.append(enhanced_ac)
        
        # Update the data with enhanced aircraft information
        enhanced_data = data.copy()
        enhanced_data['aircraft'] = enhanced_aircraft
        
        print(f"✈️  Successfully proxied {aircraft_count} aircraft from PiAware with airspace data")

        return jsonify(enhanced_data)
        
    except Exception as e:
        print(f"❌ ERROR fetching aircraft data from PiAware: {e}")
        traceback.print_exc()
        return jsonify({
            "now": time.time(),
            "aircraft": [],
            "error": str(e)
        }), 503

@app.route('/test')
def test_endpoint():
    """Test endpoint to verify server is working"""
    return jsonify({
        "status": "Enhanced Airspace Server working", 
        "timestamp": time.time(),
        "services": [
            "Aircraft Proxy",
            "Coastline Data", 
            "UK Airspace Data",
            "Airspace Identification"
        ],
        "airspace_zones": len(airspace_parser.zones)
    })

@app.route('/')
def home():
    """Server information"""
    return jsonify({
        "name": "Enhanced Airspace Server",
        "version": "2.0",
        "services": {
            "aircraft_proxy": "/tmp/aircraft.json",
            "coastline": "/api/coastline",
            "regions": "/api/regions", 
            "airspace": "/api/airspace",
            "airspace_identify": "/api/airspace/identify",
            "test": "/test"
        },
        "airspace_summary": {
            "total_zones": len(airspace_parser.zones),
            "types": list(airspace_parser.zones_by_type.keys())
        }
    })

if __name__ == "__main__":
    print("🛩️  Starting Enhanced Airspace Server")
    print("=" * 70)
    print("📍 Coastline API: http://localhost:8080/api/coastline")
    print("🌍 Regions API: http://localhost:8080/api/regions")
    print("🛩️  Airspace API: http://localhost:8080/api/airspace")
    print("🔍 Airspace ID API: http://localhost:8080/api/airspace/identify")
    print("✈️  Aircraft Proxy: http://localhost:8080/tmp/aircraft.json (with airspace data)")
    print("🧪 Test: http://localhost:8080/test")
    print("=" * 70)
    print(f"📊 Loaded {len(airspace_parser.zones)} airspace zones from UK data")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
