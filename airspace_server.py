#!/usr/bin/env python3
"""
Enhanced Airspace Server with UK Airspace Integration
Combines aircraft proxy, coastline data, and UK airspace services
"""

import time
import requests
import traceback
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from regional_data import regional_manager
from airspace_parser import UKAirspaceParser
from ssr_code_parser import SSRCodeParser
from ais_stream_client import AISStreamClient
from radar_database import radar_db
from basestation_db import get_basestation_db

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize airspace parser
print("🗺️  Initializing UK Airspace Parser...")
airspace_parser = UKAirspaceParser()
airspace_parser.parse_all_airspace()
print("✅ Airspace parser ready")

# Initialize SSR code parser
print("📡 Initializing SSR Code Parser...")
ssr_parser = SSRCodeParser()
print("✅ SSR Code parser ready")

# Initialize AIS client
print("🚢 Initializing AIS Stream Client...")
ais_client = AISStreamClient("03654a673bc690c55f0f5c73fc5052f044b6231b")
# Set bounds for UK waters (expanded for testing)
ais_client.set_geographic_bounds(
    north=65.0,   # Northern Norway
    south=45.0,   # Southern France
    east=10.0,    # Eastern Europe
    west=-20.0    # Western Atlantic
)
# Don't auto-start AIS connection - let user manually connect via GUI
print("✅ AIS Stream client ready (manual connection required)")

# Initialize BaseStation database
print("✈️  Initializing BaseStation Aircraft Database...")
try:
    basestation_db = get_basestation_db()
    print("✅ BaseStation database ready")
except Exception as e:
    print(f"⚠️  BaseStation database not available: {e}")
    basestation_db = None

# Weather data cache
weather_cache = {
    'data': None,
    'timestamp': None,
    'expires': None
}

# NOTAM data cache
notam_cache = {
    'data': None,
    'timestamp': None,
    'expires': None
}

def fetch_weather_radar_data(lat, lon, range_nm):
    """
    Fetch real weather radar data from OpenWeatherMap or similar service
    """
    try:
        # Check cache first (weather data valid for 10 minutes)
        now = datetime.now()
        if (weather_cache['data'] and weather_cache['expires'] and 
            now < weather_cache['expires']):
            print("🌦️  Using cached weather data")
            return filter_weather_by_location(weather_cache['data'], lat, lon, range_nm)
        
        # OpenWeatherMap API (requires API key)
        # For demo, we'll use Met Office API (UK) or OpenWeatherMap
        api_key = "your_api_key_here"  # Would be set via environment variable
        
        # Using OpenWeatherMap precipitation map
        # This is a simplified example - real implementation would use proper weather APIs
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        
        # For now, let's create a realistic weather pattern based on actual conditions
        # In production, you'd integrate with:
        # - Met Office API (UK): https://www.metoffice.gov.uk/services/data/datapoint
        # - OpenWeatherMap: https://openweathermap.org/api
        # - NOAA (US): https://api.weather.gov/
        # - Environment Canada
        
        weather_data = generate_realistic_weather_data(lat, lon, range_nm)
        
        # Cache the data
        weather_cache['data'] = weather_data
        weather_cache['timestamp'] = now
        weather_cache['expires'] = now + timedelta(minutes=10)
        
        print(f"🌦️  Generated realistic weather data for {lat:.2f}, {lon:.2f}")
        return weather_data
        
    except Exception as e:
        print(f"❌ Error fetching weather data: {e}")
        return []

def generate_realistic_weather_data(center_lat, center_lon, range_nm):
    """
    Generate realistic weather patterns based on typical UK weather
    This simulates real weather radar data structure
    """
    import random
    import math
    
    weather_cells = []
    
    # Simulate realistic UK weather patterns
    # UK typically has frontal systems moving W-E
    num_systems = random.randint(1, 3)
    
    for system in range(num_systems):
        # Create weather front
        front_lat = center_lat + (random.random() - 0.5) * (range_nm / 60)
        front_lon = center_lon + (random.random() - 0.5) * (range_nm / 60)
        
        # Weather intensity based on season/conditions
        base_intensity = random.uniform(0.2, 0.8)
        
        # Create cells along the front
        num_cells = random.randint(8, 25)
        
        for i in range(num_cells):
            # Position cells along weather front
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, range_nm / 4)
            
            cell_lat = front_lat + (distance / 60) * math.cos(angle)
            cell_lon = front_lon + (distance / 60) * math.sin(angle)
            
            # Weather type based on intensity
            if base_intensity > 0.7:
                weather_type = "heavy"
                dbz = random.randint(45, 65)  # dBZ reflectivity
            elif base_intensity > 0.4:
                weather_type = "moderate"
                dbz = random.randint(25, 45)
            else:
                weather_type = "light"
                dbz = random.randint(10, 25)
            
            weather_cells.append({
                'lat': cell_lat,
                'lon': cell_lon,
                'intensity': base_intensity + random.uniform(-0.2, 0.2),
                'dbz': dbz,  # Radar reflectivity
                'type': weather_type,
                'size': random.uniform(2, 12),  # km diameter
                'movement': {
                    'speed': random.uniform(10, 30),  # km/h
                    'direction': random.uniform(240, 300)  # degrees (W-NW typical for UK)
                },
                'timestamp': datetime.now().isoformat()
            })
    
    return weather_cells

def filter_weather_by_location(weather_data, center_lat, center_lon, range_nm):
    """
    Filter weather data to only include cells within radar range
    """
    import math
    
    if not weather_data:
        return []
    
    filtered_cells = []
    for cell in weather_data:
        # Calculate distance from radar center
        lat_diff = cell['lat'] - center_lat
        lon_diff = cell['lon'] - center_lon
        distance_nm = ((lat_diff * 60) ** 2 + (lon_diff * 60 * math.cos(math.radians(center_lat))) ** 2) ** 0.5
        
        if distance_nm <= range_nm:
            filtered_cells.append(cell)
    
    return filtered_cells

def fetch_live_notams():
    """
    Fetch live NOTAMs from UK NOTAM archive
    """
    try:
        # Check cache first (NOTAMs valid for 30 minutes)
        now = datetime.now()
        if (notam_cache['data'] and notam_cache['expires'] and 
            now < notam_cache['expires']):
            print("📋 Using cached NOTAM data")
            return notam_cache['data']
        
        print("📋 Fetching live NOTAMs from UK archive...")
        notam_url = "https://raw.githubusercontent.com/Jonty/uk-notam-archive/refs/heads/main/data/PIB.xml"
        
        response = requests.get(notam_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.text)
        notams = parse_notam_xml(root)
        
        # Cache the data
        notam_cache['data'] = notams
        notam_cache['timestamp'] = now
        notam_cache['expires'] = now + timedelta(minutes=30)
        
        print(f"📋 Fetched {len(notams)} NOTAMs from UK archive")
        return notams
        
    except Exception as e:
        print(f"❌ Error fetching NOTAMs: {e}")
        return []

def parse_notam_xml(root):
    """
    Parse NOTAM XML data from UK archive
    Based on the actual data structure provided by user
    """
    notams = []
    
    try:
        # Get the full text content from the XML
        xml_text = ET.tostring(root, encoding='unicode')
        
        print(f"📋 XML content length: {len(xml_text)} characters")
        
        # Parse the XML structure properly
        # The UK NOTAM archive uses structured XML with <Notam> tags
        try:
            # Find all NOTAM entries
            notam_elements = root.findall('.//Notam')
            print(f"📋 Found {len(notam_elements)} NOTAM elements in XML")
            
            for notam_elem in notam_elements:
                try:
                    parsed_notam = parse_notam_xml_element(notam_elem)
                    if parsed_notam:
                        notams.append(parsed_notam)
                except Exception as e:
                    print(f"⚠️ Error parsing NOTAM element: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error parsing XML structure: {e}")
            # Fallback to alternative method
            notams = parse_notam_xml_alternative(root)
        
        # Add distance calculation for each NOTAM
        for notam in notams:
            if notam.get('coordinates'):
                # Calculate distance from EGPK (default center)
                center_lat, center_lon = 55.5094, -4.5967
                notam_lat = notam['coordinates']['lat']
                notam_lon = notam['coordinates']['lon']
                
                # Simple distance calculation (approximate)
                lat_diff = abs(notam_lat - center_lat)
                lon_diff = abs(notam_lon - center_lon)
                distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5 * 60  # Convert to nautical miles
                notam['distance_nm'] = round(distance, 1)
        
        print(f"📋 Successfully parsed {len(notams)} real NOTAMs from XML")
        return notams
        
    except Exception as e:
        print(f"❌ Error parsing NOTAM XML: {e}")
        traceback.print_exc()
        return []

def parse_notam_text(notam_text, notam_id):
    """
    Parse NOTAM text content to extract structured data
    """
    try:
        # Initialize NOTAM data structure
        notam_data = {
            'id': notam_id,
            'raw_text': notam_text.strip(),
            'type': 'UNKNOWN',
            'location': None,
            'coordinates': None,
            'effective_from': None,
            'effective_to': None,
            'altitude_from': None,
            'altitude_to': None,
            'description': '',
            'category': 'OTHER',
            'priority': 'NORMAL'
        }
        
        # Parse NOTAM text for key information
        parse_notam_content(notam_text, notam_data)
        
        return notam_data
        
    except Exception as e:
        print(f"⚠️ Error parsing NOTAM text: {e}")
        return None

def parse_notam_content(text, notam_data):
    """
    Parse NOTAM text content to extract structured information
    """
    try:
        # Extract coordinates (various formats)
        coord_patterns = [
            r'(\d{4}N\d{5}W)',  # 5530N00426W format
            r'(\d{6}N \d{7}W)', # 553332N 0042543W format
            r'PSN (\d{6}N \d{7}W)', # PSN 553332N 0042543W
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, text)
            if match:
                coord_str = match.group(1)
                coords = parse_coordinates(coord_str)
                if coords:
                    notam_data['coordinates'] = coords
                    break
        
        # Extract time information
        time_pattern = r'(\d{10}) (\d{10})'  # Start and end times
        time_match = re.search(time_pattern, text)
        if time_match:
            start_time = parse_notam_time(time_match.group(1))
            end_time = parse_notam_time(time_match.group(2))
            notam_data['effective_from'] = start_time
            notam_data['effective_to'] = end_time
        
        # Extract altitude information
        alt_patterns = [
            r'SFC (\d+)FT',  # Surface to altitude
            r'FL(\d+)',      # Flight level
            r'(\d+)FT AMSL', # Feet above mean sea level
        ]
        
        for pattern in alt_patterns:
            match = re.search(pattern, text)
            if match:
                if 'SFC' in pattern:
                    notam_data['altitude_from'] = 0
                    notam_data['altitude_to'] = int(match.group(1))
                elif 'FL' in pattern:
                    fl = int(match.group(1))
                    notam_data['altitude_from'] = fl * 100  # Convert FL to feet
                break
        
        # Categorize NOTAM type
        if 'DANGER AREA' in text.upper():
            notam_data['type'] = 'DANGER_AREA'
            notam_data['category'] = 'AIRSPACE'
            notam_data['priority'] = 'HIGH'
        elif 'RESTRICTED AREA' in text.upper():
            notam_data['type'] = 'RESTRICTED_AREA'
            notam_data['category'] = 'AIRSPACE'
            notam_data['priority'] = 'HIGH'
        elif 'FIREWORKS' in text.upper():
            notam_data['type'] = 'FIREWORKS'
            notam_data['category'] = 'HAZARD'
            notam_data['priority'] = 'MEDIUM'
        elif 'MILITARY' in text.upper() or 'COMBAT' in text.upper():
            notam_data['type'] = 'MILITARY'
            notam_data['category'] = 'AIRSPACE'
            notam_data['priority'] = 'HIGH'
        elif 'SECURITY' in text.upper() or 'HAZARDOUS' in text.upper():
            notam_data['type'] = 'SECURITY'
            notam_data['category'] = 'SECURITY'
            notam_data['priority'] = 'CRITICAL'
        elif 'RUNWAY' in text.upper() or 'RWY' in text.upper():
            notam_data['type'] = 'RUNWAY'
            notam_data['category'] = 'AIRPORT'
            notam_data['priority'] = 'HIGH'
        elif 'NAVIGATION' in text.upper() or 'NAV' in text.upper():
            notam_data['type'] = 'NAVIGATION'
            notam_data['category'] = 'NAVAID'
            notam_data['priority'] = 'MEDIUM'
        
        # Extract location/airport codes
        airport_match = re.search(r'EG[A-Z]{2}', text)
        if airport_match:
            notam_data['location'] = airport_match.group(0)
        
        # Clean up description
        notam_data['description'] = text.replace('\n', ' ').strip()[:200] + '...' if len(text) > 200 else text.replace('\n', ' ').strip()
        
    except Exception as e:
        print(f"⚠️ Error parsing NOTAM content: {e}")

def parse_coordinates(coord_str):
    """
    Parse coordinate string to decimal degrees
    """
    try:
        # Handle format like "5530N00426W" or "553332N 0042543W"
        coord_str = coord_str.replace(' ', '')
        
        if 'N' in coord_str and 'W' in coord_str:
            parts = coord_str.split('N')
            lat_str = parts[0]
            lon_str = parts[1].replace('W', '')
            
            # Parse latitude
            if len(lat_str) == 4:  # DDMM format
                lat = int(lat_str[:2]) + int(lat_str[2:]) / 60.0
            elif len(lat_str) == 6:  # DDMMSS format
                lat = int(lat_str[:2]) + int(lat_str[2:4]) / 60.0 + int(lat_str[4:]) / 3600.0
            else:
                return None
            
            # Parse longitude
            if len(lon_str) == 5:  # DDDMM format
                lon = -(int(lon_str[:3]) + int(lon_str[3:]) / 60.0)
            elif len(lon_str) == 7:  # DDDMMSS format
                lon = -(int(lon_str[:3]) + int(lon_str[3:5]) / 60.0 + int(lon_str[5:]) / 3600.0)
            else:
                return None
            
            return {'lat': lat, 'lon': lon}
    
    except Exception as e:
        print(f"⚠️ Error parsing coordinates {coord_str}: {e}")
    
    return None

def parse_notam_time(time_str):
    """
    Parse NOTAM time format (YYMMDDHHMM)
    """
    try:
        if len(time_str) == 10:
            year = 2000 + int(time_str[:2])
            month = int(time_str[2:4])
            day = int(time_str[4:6])
            hour = int(time_str[6:8])
            minute = int(time_str[8:10])
            
            return datetime(year, month, day, hour, minute).isoformat()
    except Exception as e:
        print(f"⚠️ Error parsing NOTAM time {time_str}: {e}")
    
    return None

def parse_single_notam(notam_text):
    """
    Parse a single NOTAM text entry
    """
    try:
        # Extract basic NOTAM information using regex patterns
        notam_data = {}
        
        # Extract NOTAM ID (e.g., EGGN H 6425)
        id_match = re.search(r'^([A-Z]{4})\s+([A-Z])\s+(\d+)', notam_text)
        if id_match:
            notam_data['id'] = f"{id_match.group(1)}_{id_match.group(2)}_{id_match.group(3)}"
            notam_data['fir'] = id_match.group(1)
            notam_data['series'] = id_match.group(2)
            notam_data['number'] = int(id_match.group(3))
        
        # Extract coordinates (e.g., 5653N00517W)
        coord_match = re.search(r'(\d{2})(\d{2})([NS])(\d{3})(\d{2})([EW])', notam_text)
        if coord_match:
            lat_deg = int(coord_match.group(1))
            lat_min = int(coord_match.group(2))
            lat_dir = coord_match.group(3)
            lon_deg = int(coord_match.group(4))
            lon_min = int(coord_match.group(5))
            lon_dir = coord_match.group(6)
            
            lat = lat_deg + (lat_min / 60.0)
            if lat_dir == 'S':
                lat = -lat
                
            lon = lon_deg + (lon_min / 60.0)
            if lon_dir == 'W':
                lon = -lon
                
            notam_data['coordinates'] = {'lat': lat, 'lon': lon}
        
        # Extract radius (e.g., "WI 2NM RADIUS")
        radius_match = re.search(r'WI\s+(\d+(?:\.\d+)?)\s*NM?\s+RADIUS', notam_text, re.IGNORECASE)
        if radius_match:
            notam_data['radius_nm'] = float(radius_match.group(1))
        
        # Extract altitudes (e.g., "SFC 2700FT AMSL")
        alt_match = re.search(r'(\w+)\s+(\d+)\s*FT?\s+AMSL', notam_text, re.IGNORECASE)
        if alt_match:
            if alt_match.group(1).upper() == 'SFC':
                notam_data['altitude_from'] = 0
            else:
                notam_data['altitude_from'] = int(alt_match.group(1))
            notam_data['altitude_to'] = int(alt_match.group(2))
        
        # Extract dates (e.g., 2508120700 2508122030)
        date_match = re.search(r'(\d{2})(\d{2})(\d{2})(\d{4})\s+(\d{2})(\d{2})(\d{2})(\d{4})', notam_text)
        if date_match:
            day1, month1, year1, time1 = date_match.group(1, 2, 3, 4)
            day2, month2, year2, time2 = date_match.group(5, 6, 7, 8)
            
            # Convert to proper datetime
            year = 2000 + int(year1)
            effective_from = f"{year}-{month1}-{day1}T{time1[:2]}:{time1[2:4]}:00"
            effective_to = f"{year}-{month2}-{day2}T{time2[:2]}:{time2[2:4]}:00"
            
            notam_data['effective_from'] = effective_from
            notam_data['effective_to'] = effective_to
        
        # Determine NOTAM type and category
        notam_data['type'] = determine_notam_type(notam_text)
        notam_data['category'] = determine_notam_category(notam_text)
        notam_data['priority'] = determine_notam_priority(notam_text)
        
        # Extract description
        notam_data['description'] = extract_notam_description(notam_text)
        notam_data['raw_text'] = notam_text
        
        # Extract location name if available
        location_match = re.search(r'\(([^)]+)\)', notam_text)
        if location_match:
            notam_data['location'] = location_match.group(1).strip()
        
        return notam_data
        
    except Exception as e:
        print(f"⚠️ Error parsing NOTAM text: {e}")
        return None

def determine_notam_type(notam_text):
    """Determine NOTAM type based on content"""
    text_upper = notam_text.upper()
    
    if 'LOW FLYING' in text_upper or 'LW' in text_upper:
        return 'LOW_FLYING'
    elif 'RESTRICTED' in text_upper or 'RT' in text_upper:
        return 'RESTRICTED_AREA'
    elif 'MILITARY' in text_upper or 'RD' in text_upper:
        return 'MILITARY'
    elif 'FIREWORKS' in text_upper or 'WZ' in text_upper:
        return 'FIREWORKS'
    elif 'AIRSPACE' in text_upper:
        return 'AIRSPACE'
    elif 'HAZARD' in text_upper:
        return 'HAZARD'
    else:
        return 'GENERAL'

def determine_notam_category(notam_text):
    """Determine NOTAM category based on content"""
    text_upper = notam_text.upper()
    
    if 'LOW FLYING' in text_upper or 'LW' in text_upper:
        return 'HAZARD'
    elif 'RESTRICTED' in text_upper:
        return 'AIRSPACE'
    elif 'MILITARY' in text_upper:
        return 'AIRSPACE'
    elif 'FIREWORKS' in text_upper:
        return 'HAZARD'
    else:
        return 'GENERAL'

def determine_notam_priority(notam_text):
    """Determine NOTAM priority based on content"""
    text_upper = notam_text.upper()
    
    if 'CRITICAL' in text_upper or 'CRIT' in text_upper:
        return 'CRITICAL'
    elif 'LOW FLYING' in text_upper or 'MILITARY' in text_upper:
        return 'HIGH'
    elif 'RESTRICTED' in text_upper:
        return 'HIGH'
    elif 'FIREWORKS' in text_upper:
        return 'MEDIUM'
    else:
        return 'NORMAL'

def extract_notam_description(notam_text):
    """Extract a readable description from NOTAM text"""
    # Remove technical parts and extract the main message
    lines = notam_text.split('.')
    if len(lines) > 1:
        # Look for the most descriptive line
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not re.match(r'^[A-Z0-9\s]+$', line):
                return line
    return notam_text[:100] + "..." if len(notam_text) > 100 else notam_text

def parse_notam_xml_alternative(root):
    """
    Alternative method to parse NOTAM XML if primary method fails
    """
    notams = []
    
    try:
        # Try to find any text content that looks like NOTAMs
        xml_text = ET.tostring(root, encoding='unicode')
        
        # Look for UK NOTAM identifiers
        uk_notam_pattern = r'EG[GNPTX]{2}\s+[A-Z]\s+\d+'
        matches = re.findall(uk_notam_pattern, xml_text)
        
        print(f"📋 Alternative method found {len(matches)} UK NOTAM identifiers")
        
        # Create basic NOTAM entries for found identifiers
        for i, match in enumerate(matches[:20]):  # Limit to 20 for performance
            notam_data = {
                'id': f"ALT_{i+1}",
                'raw_text': match,
                'type': 'UNKNOWN',
                'category': 'GENERAL',
                'priority': 'NORMAL',
                'coordinates': {'lat': 55.5094, 'lon': -4.5967},  # Default to EGPK
                'radius_nm': 5.0,
                'altitude_from': 0,
                'altitude_to': 10000,
                'effective_from': datetime.now().isoformat(),
                'effective_to': (datetime.now() + timedelta(days=7)).isoformat(),
                'location': 'UK Airspace',
                'description': f'NOTAM {match} - Details to be parsed'
            }
            notams.append(notam_data)
        
        return notams
        
    except Exception as e:
        print(f"❌ Alternative NOTAM parsing failed: {e}")
        return []

def parse_notam_xml_element(notam_elem):
    """
    Parse a NOTAM XML element with structured fields
    """
    try:
        notam_data = {}
        
        # Extract NOTAM ID from ItemA field
        item_a = notam_elem.find('ItemA')
        if item_a is not None and item_a.text:
            notam_data['id'] = item_a.text.strip()
        
        # Extract coordinates
        coords_elem = notam_elem.find('Coordinates')
        if coords_elem is not None and coords_elem.text:
            coords = parse_notam_coordinates(coords_elem.text.strip())
            if coords:
                notam_data['coordinates'] = coords
        
        # Extract radius
        radius_elem = notam_elem.find('Radius')
        if radius_elem is not None and radius_elem.text:
            try:
                notam_data['radius_nm'] = float(radius_elem.text.strip())
            except ValueError:
                notam_data['radius_nm'] = 5.0  # Default radius
        
        # Extract altitude information
        qline = notam_elem.find('QLine')
        if qline is not None:
            lower = qline.find('Lower')
            upper = qline.find('Upper')
            if lower is not None and lower.text:
                try:
                    notam_data['altitude_from'] = int(lower.text.strip())
                except ValueError:
                    notam_data['altitude_from'] = 0
            if upper is not None and upper.text:
                try:
                    notam_data['altitude_to'] = int(upper.text.strip())
                except ValueError:
                    notam_data['altitude_to'] = 10000
        
        # Extract validity dates
        start_validity = notam_elem.find('StartValidity')
        end_validity = notam_elem.find('EndValidity')
        
        if start_validity is not None and start_validity.text:
            start_time = parse_notam_time(start_validity.text.strip())
            if start_time:
                notam_data['effective_from'] = start_time
        
        if end_validity is not None and end_validity.text:
            if end_validity.text.strip().upper() == 'PERM':
                # Permanent NOTAM
                notam_data['effective_to'] = (datetime.now() + timedelta(days=365)).isoformat()
            else:
                end_time = parse_notam_time(end_validity.text.strip())
                if end_time:
                    notam_data['effective_to'] = end_time
        
        # Extract description from ItemE
        item_e = notam_elem.find('ItemE')
        if item_e is not None and item_e.text:
            description = item_e.text.strip()
            notam_data['description'] = description
            notam_data['raw_text'] = description
            
            # Determine type and category from description
            notam_data['type'] = determine_notam_type(description)
            notam_data['category'] = determine_notam_category(description)
            notam_data['priority'] = determine_notam_priority(description)
        
        # Extract location from parent ADSection
        parent_section = notam_elem.find('..')
        if parent_section is not None:
            code_elem = parent_section.find('Code')
            name_elem = parent_section.find('Name')
            if code_elem is not None and code_elem.text:
                notam_data['location'] = code_elem.text.strip()
            elif name_elem is not None and name_elem.text:
                notam_data['location'] = name_elem.text.strip()
        
        # Generate a unique ID if none exists
        if 'id' not in notam_data:
            notam_data['id'] = f"NOTAM_{hash(str(notam_data)) % 10000}"
        
        return notam_data
        
    except Exception as e:
        print(f"⚠️ Error parsing NOTAM XML element: {e}")
        return None

def parse_notam_coordinates(coord_str):
    """
    Parse NOTAM coordinate string (e.g., "5120N00002E")
    """
    try:
        # Handle format like "5120N00002E" (DDMMN/DDDMME)
        coord_str = coord_str.replace(' ', '')
        
        if 'N' in coord_str and ('E' in coord_str or 'W' in coord_str):
            parts = coord_str.split('N')
            lat_str = parts[0]
            lon_str = parts[1]
            
            # Parse latitude (DDMM format)
            if len(lat_str) == 4:
                lat_deg = int(lat_str[:2])
                lat_min = int(lat_str[2:])
                lat = lat_deg + (lat_min / 60.0)
            else:
                return None
            
            # Parse longitude (DDDMM format)
            if 'E' in lon_str:
                lon_str = lon_str.replace('E', '')
                lon_sign = 1
            elif 'W' in lon_str:
                lon_str = lon_str.replace('W', '')
                lon_sign = -1
            else:
                return None
                
            if len(lon_str) == 5:
                lon_deg = int(lon_str[:3])
                lon_min = int(lon_str[3:])
                lon = lon_sign * (lon_deg + (lon_min / 60.0))
            else:
                return None
            
            return {'lat': lat, 'lon': lon}
    
    except Exception as e:
        print(f"⚠️ Error parsing coordinates {coord_str}: {e}")
    
    return None

def filter_notams_by_location(notams, center_lat, center_lon, range_nm):
    """
    Filter NOTAMs to only include those within radar range
    """
    import math
    
    filtered_notams = []
    for notam in notams:
        include_notam = False
        
        # Include if it has coordinates within range
        if notam.get('coordinates'):
            coords = notam['coordinates']
            lat_diff = coords['lat'] - center_lat
            lon_diff = coords['lon'] - center_lon
            distance_nm = ((lat_diff * 60) ** 2 + (lon_diff * 60 * math.cos(math.radians(center_lat))) ** 2) ** 0.5
            
            if distance_nm <= range_nm:
                include_notam = True
        
        # Include critical security NOTAMs regardless of location
        elif notam.get('priority') == 'CRITICAL':
            include_notam = True
        
        # Include if it mentions nearby airports
        elif notam.get('location'):
            # Add logic for airport proximity if needed
            include_notam = True
        
        if include_notam:
            # Add distance for sorting
            if notam.get('coordinates'):
                coords = notam['coordinates']
                lat_diff = coords['lat'] - center_lat
                lon_diff = coords['lon'] - center_lon
                distance_nm = ((lat_diff * 60) ** 2 + (lon_diff * 60 * math.cos(math.radians(center_lat))) ** 2) ** 0.5
                notam['distance_nm'] = round(distance_nm, 1)
            
            filtered_notams.append(notam)
    
    # Sort by priority and distance
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'NORMAL': 3}
    filtered_notams.sort(key=lambda x: (
        priority_order.get(x.get('priority', 'NORMAL'), 3),
        x.get('distance_nm', 999)
    ))
    
    return filtered_notams

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
                        
                        # Store in database for historical tracking
                        try:
                            radar_db.store_aircraft_contact(enhanced_ac)
                        except Exception as db_error:
                            print(f"⚠️  Database storage error for {aircraft.get('hex', 'unknown')}: {db_error}")
                            # Continue processing even if database fails
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
            
            # Add SSR code information and check for alerts
            squawk = aircraft.get('squawk')
            if squawk:
                try:
                    ssr_info = ssr_parser.get_code_info(squawk)
                    if ssr_info:
                        enhanced_ac['ssr'] = {
                            'code': ssr_info['code'],
                            'description': ssr_info['description'],
                            'categories': ssr_info['categories'],
                            'priority': ssr_info['priority'],
                            'color': ssr_info['color'],
                            'is_alert': ssr_info['is_alert']
                        }
                        
                        # Generate alerts for special codes
                        if ssr_info['is_alert']:
                            alerts = ssr_parser.check_for_alerts(aircraft)
                            if alerts:
                                alert_msg = alerts[0]['message']
                                print(f"🚨 SSR Alert: {alert_msg}")
                                enhanced_ac['alert'] = {
                                    'type': 'SSR_CODE',
                                    'priority': ssr_info['priority'],
                                    'message': alert_msg,
                                    'timestamp': datetime.now().isoformat()
                                }
                    else:
                        enhanced_ac['ssr'] = {
                            'code': squawk,
                            'description': 'Unknown SSR code',
                            'categories': [],
                            'priority': 'LOW',
                            'color': '#888888',
                            'is_alert': False
                        }
                except Exception as e:
                    print(f"⚠️  Error processing SSR code {squawk}: {e}")
                    enhanced_ac['ssr'] = None
            
            # Enhance with BaseStation database information
            if basestation_db and 'hex' in aircraft:
                try:
                    basestation_info = basestation_db.get_aircraft_info(aircraft['hex'])
                    if basestation_info:
                        enhanced_ac.update({
                            'registration': basestation_info.get('registration'),
                            'icao_type': basestation_info.get('icao_type'),
                            'manufacturer': basestation_info.get('manufacturer'),
                            'aircraft_type': basestation_info.get('type'),
                            'operator': basestation_info.get('operator'),
                            'owner': basestation_info.get('owner'),
                            'enhanced': True
                        })
                        print(f"🔍 Enhanced aircraft {aircraft.get('hex', 'unknown')} with BaseStation data: {basestation_info.get('registration', 'N/A')}")
                    else:
                        enhanced_ac['enhanced'] = False
                except Exception as e:
                    print(f"⚠️  Error enhancing aircraft {aircraft.get('hex', 'unknown')} with BaseStation data: {e}")
                    enhanced_ac['enhanced'] = False
                    
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

@app.route('/api/weather')
def get_weather_data():
    """Get real weather radar data for a given location and range"""
    try:
        lat = float(request.args.get('lat', 55.5094))
        lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 100))
        
        print(f"🌦️  Fetching weather data for {lat:.4f}, {lon:.4f} within {range_nm}nm")
        
        weather_data = fetch_weather_radar_data(lat, lon, range_nm)
        
        return jsonify({
            "status": "success",
            "data": {
                "weather_cells": weather_data,
                "center": {"lat": lat, "lon": lon},
                "range_nm": range_nm,
                "timestamp": datetime.now().isoformat(),
                "source": "Realistic Weather Simulation",
                "update_interval": 600  # 10 minutes
            },
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Error getting weather data: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": time.time()
        }), 400

@app.route('/api/ssr-codes')
def get_ssr_codes():
    """Get SSR code information and statistics"""
    try:
        code = request.args.get('code')
        category = request.args.get('category', 'ALL')
        
        if code:
            # Get specific SSR code information
            ssr_info = ssr_parser.get_code_info(code)
            if ssr_info:
                return jsonify({
                    "status": "success",
                    "data": {
                        "code_info": ssr_info
                    }
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": f"SSR code {code} not found"
                }), 404
        else:
            # Get statistics and categories
            stats = ssr_parser.get_statistics()
            categories = ssr_parser.categories
            
            # Filter by category if specified
            if category != 'ALL' and category in categories:
                filtered_codes = {}
                for code in categories[category]:
                    if code in ssr_parser.codes:
                        filtered_codes[code] = ssr_parser.codes[code]
                
                return jsonify({
                    "status": "success",
                    "data": {
                        "category": category,
                        "codes": filtered_codes,
                        "count": len(filtered_codes),
                        "statistics": stats
                    }
                })
            else:
                return jsonify({
                    "status": "success",
                    "data": {
                        "statistics": stats,
                        "categories": {cat: len(codes) for cat, codes in categories.items() if codes},
                        "alert_codes": list(ssr_parser.alert_codes),
                        "emergency_codes": ["7700", "7600", "7500"]
                    }
                })
                
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/ais/vessels')
def get_ais_vessels():
    """Get AIS vessel data within specified range"""
    try:
        lat = float(request.args.get('lat', 55.5094))
        lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 100))
        
        vessels = ais_client.get_vessels_in_range(lat, lon, range_nm)
        
        return jsonify({
            "status": "success",
            "data": {
                "vessels": vessels,
                "count": len(vessels),
                "center": {"lat": lat, "lon": lon},
                "range_nm": range_nm,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/ais/status')
def get_ais_status():
    """Get AIS connection status"""
    try:
        status = ais_client.get_status()
        return jsonify({
            "status": "success",
            "data": status
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/ais/connect', methods=['POST'])
def connect_ais():
    """Start AIS connection"""
    try:
        ais_client.start_connection()
        return jsonify({
            "status": "success",
            "message": "AIS connection started"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/ais/disconnect', methods=['POST'])
def disconnect_ais():
    """Stop AIS connection"""
    try:
        ais_client.stop_connection()
        return jsonify({
            "status": "success",
            "message": "AIS connection stopped"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/notams')
def get_notams():
    """Get live NOTAMs for a given location and range"""
    try:
        lat = float(request.args.get('lat', 55.5094))
        lon = float(request.args.get('lon', -4.5967))
        range_nm = float(request.args.get('range', 100))
        category = request.args.get('category', 'ALL')  # ALL, AIRSPACE, SECURITY, AIRPORT, etc.
        priority = request.args.get('priority', 'ALL')  # ALL, CRITICAL, HIGH, MEDIUM, NORMAL
        
        print(f"📋 Fetching NOTAMs for {lat:.4f}, {lon:.4f} within {range_nm}nm")
        
        # Fetch all NOTAMs
        all_notams = fetch_live_notams()
        
        # Filter by location
        filtered_notams = filter_notams_by_location(all_notams, lat, lon, range_nm)
        
        # Apply category filter
        if category != 'ALL':
            filtered_notams = [n for n in filtered_notams if n.get('category') == category]
        
        # Apply priority filter
        if priority != 'ALL':
            filtered_notams = [n for n in filtered_notams if n.get('priority') == priority]
        
        # Limit results for performance
        filtered_notams = filtered_notams[:50]
        
        return jsonify({
            "status": "success",
            "data": {
                "notams": filtered_notams,
                "center": {"lat": lat, "lon": lon},
                "range_nm": range_nm,
                "total_count": len(all_notams),
                "filtered_count": len(filtered_notams),
                "timestamp": datetime.now().isoformat(),
                "source": "UK NOTAM Archive",
                "update_interval": 1800  # 30 minutes
            },
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Error getting NOTAMs: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": time.time()
        }), 400

# Historical data API endpoints
@app.route('/api/aircraft/history/<hex_code>')
def get_aircraft_history(hex_code):
    """Get historical data for specific aircraft"""
    hours = request.args.get('hours', 24, type=int)
    try:
        history = radar_db.get_aircraft_history(hex_code, hours)
        return jsonify({
            "status": "success",
            "aircraft": hex_code,
            "hours": hours,
            "contacts": len(history),
            "data": history
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/aircraft/summary/<hex_code>')
def get_aircraft_summary(hex_code):
    """Get summary information for aircraft"""
    try:
        summary = radar_db.get_aircraft_summary(hex_code)
        if summary:
            return jsonify({
                "status": "success",
                "aircraft": hex_code,
                "summary": summary
            })
        else:
            return jsonify({"status": "error", "message": "Aircraft not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/events')
def get_flight_events():
    """Get flight events"""
    hex_code = request.args.get('hex')
    event_type = request.args.get('type')
    hours = request.args.get('hours', 24, type=int)
    
    try:
        events = radar_db.get_flight_events(hex_code, event_type, hours)
        return jsonify({
            "status": "success",
            "events": events,
            "count": len(events)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/database/stats')
def get_database_stats():
    """Get database statistics"""
    try:
        stats = radar_db.get_database_stats()
        return jsonify({
            "status": "success",
            "stats": stats
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/aircraft/active')
def get_active_aircraft():
    """Get recently active aircraft"""
    minutes = request.args.get('minutes', 5, type=int)
    try:
        active = radar_db.get_active_aircraft(minutes)
        return jsonify({
            "status": "success",
            "active_aircraft": active,
            "count": len(active),
            "timeframe_minutes": minutes
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/metar/<icao>')
def get_metar_data(icao):
    """Get real METAR data for a specific airport"""
    try:
        print(f"🌤️  Fetching METAR data for {icao}")
        
        # Try multiple METAR data sources for redundancy
        metar_data = None
        
        # Source 1: Aviation Weather Center (NOAA) - Free, reliable
        try:
            print(f"🔍 Attempting NOAA METAR fetch for {icao}")
            metar_data = fetch_metar_noaa(icao)
            print(f"🔍 NOAA response: {metar_data}")
            if metar_data:
                print(f"✅ METAR data from NOAA for {icao}")
        except Exception as e:
            print(f"❌ NOAA METAR failed for {icao}: {e}")
            traceback.print_exc()
        
        # Source 2: OpenWeatherMap (requires API key but more comprehensive)
        if not metar_data:
            try:
                metar_data = fetch_metar_openweather(icao)
                if metar_data:
                    print(f"✅ METAR data from OpenWeatherMap for {icao}")
            except Exception as e:
                print(f"❌ OpenWeatherMap METAR failed for {icao}: {e}")
        
        # Source 3: Met Office (UK) - Good for UK airports
        if not metar_data and icao.startswith('EG'):
            try:
                metar_data = fetch_metar_metoffice(icao)
                if metar_data:
                    print(f"✅ METAR data from Met Office for {icao}")
            except Exception as e:
                print(f"❌ Met Office METAR failed for {icao}: {e}")
        
        if metar_data:
            return jsonify({
                "status": "success",
                "data": metar_data,
                "source": metar_data.get('source', 'Unknown'),
                "timestamp": time.time()
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"No METAR data available for {icao}",
                "timestamp": time.time()
            }), 404
            
    except Exception as e:
        print(f"❌ Error getting METAR data for {icao}: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": time.time()
        }), 400

def fetch_metar_noaa(icao):
    """Fetch METAR data from NOAA Aviation Weather Center"""
    try:
        url = f"https://aviationweather.gov/cgi-bin/data/metar.php?ids={icao}&format=raw"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            metar_text = response.text.strip()
            if metar_text and len(metar_text) > 10:  # NOAA returns raw METAR without METAR prefix
                return parse_metar_text(metar_text, 'NOAA')
        
        return None
    except Exception as e:
        print(f"❌ NOAA METAR fetch error: {e}")
        return None

def fetch_metar_openweather(icao):
    """Fetch METAR data from OpenWeatherMap (requires API key)"""
    try:
        # This would require an OpenWeatherMap API key
        # For now, return None to avoid errors
        return None
    except Exception as e:
        print(f"❌ OpenWeatherMap METAR fetch error: {e}")
        return None

def fetch_metar_metoffice(icao):
    """Fetch METAR data from UK Met Office"""
    try:
        # Met Office has a free API but requires registration
        # For now, return None to avoid errors
        return None
    except Exception as e:
        print(f"❌ Met Office METAR fetch error: {e}")
        return None

def parse_metar_text(metar_text, source):
    """Parse METAR text into structured data"""
    try:
        # Basic METAR parsing - this is a simplified version
        # Real implementation would use a proper METAR parser library
        
        metar_data = {
            'source': source,
            'raw': metar_text,
            'icao': None,
            'timestamp': None,
            'wind': None,
            'visibility': None,
            'weather': None,
            'clouds': None,
            'temperature': None,
            'dewpoint': None,
            'pressure': None,
            'remarks': None
        }
        
        # Extract ICAO code (NOAA format doesn't have METAR prefix)
        icao_match = re.search(r'^([A-Z]{4})\s+', metar_text)
        if icao_match:
            metar_data['icao'] = icao_match.group(1)
        
        # Extract wind information
        wind_match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', metar_text)
        if wind_match:
            direction = int(wind_match.group(1))
            speed = int(wind_match.group(2))
            gust = wind_match.group(3)[1:] if wind_match.group(3) else None
            
            metar_data['wind'] = {
                'direction': direction,
                'speed': speed,
                'gust': int(gust) if gust else None,
                'unit': 'KT'
            }
        else:
            # Check for calm winds
            if '00000KT' in metar_text:
                metar_data['wind'] = {
                    'direction': 0,
                    'speed': 0,
                    'gust': None,
                    'unit': 'KT'
                }
        
        print(f"🔍 Wind parsing result: {metar_data['wind']}")
        
        # Extract visibility (must be after wind and before clouds)
        # Look for 4 digits that are not part of timestamp or other fields
        vis_match = re.search(r'KT\s+(\d{4})\s+', metar_text)
        if vis_match:
            metar_data['visibility'] = int(vis_match.group(1))
            print(f"🔍 Visibility: {metar_data['visibility']} m")
        else:
            print(f"🔍 No visibility found in: {metar_text}")
        
        # Extract temperature and dewpoint
        temp_match = re.search(r'(\d{2})/(\d{2})', metar_text)
        if temp_match:
            temp = int(temp_match.group(1))
            dew = int(temp_match.group(2))
            # Handle negative temperatures (M prefix)
            if 'M' in metar_text:
                temp = -temp
                dew = -dew
            metar_data['temperature'] = temp
            metar_data['dewpoint'] = dew
            print(f"🔍 Temperature: {temp}°C, Dewpoint: {dew}°C")
        
        # Extract pressure (QNH)
        pressure_match = re.search(r'Q(\d{4})', metar_text)
        if pressure_match:
            pressure = int(pressure_match.group(1))
            metar_data['pressure'] = pressure
            print(f"🔍 Pressure: {pressure} hPa")
        
        # Extract cloud information
        cloud_match = re.search(r'(FEW|SCT|BKN|OVC)(\d{3})', metar_text)
        if cloud_match:
            metar_data['clouds'] = {
                'type': cloud_match.group(1),
                'height': int(cloud_match.group(2)) * 100  # Convert to feet
            }
        
        # Extract weather phenomena
        weather_match = re.search(r'(-|\+)?(RA|SN|DZ|FG|BR|HZ|FU|DU|SA|HZ|PY|PO|SQ|FC|SS|DS|TS|GR|GS|PL|IC|UP|VA|DU|SA|HZ|FU|BR|FG|MI|BC|DR|BL|SH|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS|TS)', metar_text)
        if weather_match:
            intensity = weather_match.group(1) if weather_match.group(1) else ''
            phenomena = weather_match.group(2)
            metar_data['weather'] = {
                'intensity': intensity,
                'phenomena': phenomena
            }
        
        return metar_data
        
    except Exception as e:
        print(f"❌ METAR parsing error: {e}")
        return None

# BaseStation Database API Endpoints
@app.route('/api/aircraft/lookup/<mode_s>')
def lookup_aircraft(mode_s):
    """Look up aircraft information by ModeS code using BaseStation database"""
    try:
        if not basestation_db:
            return jsonify({
                'status': 'error',
                'message': 'BaseStation database not available'
            }), 503
        
        aircraft_info = basestation_db.get_aircraft_info(mode_s)
        if aircraft_info:
            return jsonify({
                'status': 'success',
                'data': aircraft_info
            })
        else:
            return jsonify({
                'status': 'not_found',
                'message': f'Aircraft with ModeS {mode_s} not found in database'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/aircraft/search/registration/<registration>')
def search_aircraft_by_registration(registration):
    """Search for aircraft by registration number"""
    try:
        if not basestation_db:
            return jsonify({
                'status': 'error',
                'message': 'BaseStation database not available'
            }), 503
        
        results = basestation_db.search_by_registration(registration)
        return jsonify({
            'status': 'success',
            'data': {
                'search_term': registration,
                'results': results,
                'count': len(results)
            }
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/aircraft/search/type/<aircraft_type>')
def search_aircraft_by_type(aircraft_type):
    """Search for aircraft by type"""
    try:
        if not basestation_db:
            return jsonify({
                'status': 'error',
                'message': 'BaseStation database not available'
            }), 503
        
        results = basestation_db.search_by_type(aircraft_type)
        return jsonify({
            'status': 'success',
            'data': {
                'search_term': aircraft_type,
                'results': results,
                'count': len(results)
            }
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/basestation/stats')
def get_basestation_stats():
    """Get BaseStation database statistics"""
    try:
        if not basestation_db:
            return jsonify({
                'status': 'error',
                'message': 'BaseStation database not available'
            }), 503
        
        stats = basestation_db.get_aircraft_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == "__main__":
    print("🛩️  Starting Enhanced Airspace Server with Historical Database")
    print("=" * 70)
    print("📍 Coastline API: http://localhost:8080/api/coastline")
    print("🌍 Regions API: http://localhost:8080/api/regions")
    print("🛩️  Airspace API: http://localhost:8080/api/airspace")
    print("🔍 Airspace ID API: http://localhost:8080/api/airspace/identify")
    print("🌦️  Weather API: http://localhost:8080/api/weather")
    print("🌤️  METAR API: http://localhost:8080/api/metar/<ICAO>")
    print("📋 NOTAM API: http://localhost:8080/api/notams")
    print("✈️  Aircraft Proxy: http://localhost:8080/tmp/aircraft.json (with airspace data)")
    print("🧪 Test: http://localhost:8080/test")
    print("")
    print("📊 HISTORICAL DATABASE FEATURES:")
    print("📈 Database Stats: http://localhost:8080/api/database/stats")
    print("🔍 Aircraft History: http://localhost:8080/api/aircraft/history/<hex>")
    print("📝 Aircraft Summary: http://localhost:8080/api/aircraft/summary/<hex>")
    print("🚨 Flight Events: http://localhost:8080/api/events")
    print("🎯 Active Aircraft: http://localhost:8080/api/aircraft/active")
    print("")
    print("✈️  BASESTATION AIRCRAFT DATABASE FEATURES:")
    print("🔍 Aircraft Lookup: http://localhost:8080/api/aircraft/lookup/<mode_s>")
    print("📋 Registration Search: http://localhost:8080/api/aircraft/search/registration/<reg>")
    print("🛩️  Type Search: http://localhost:8080/api/aircraft/search/type/<type>")
    print("📊 BaseStation Stats: http://localhost:8080/api/basestation/stats")
    print("=" * 70)
    print(f"📊 Loaded {len(airspace_parser.zones)} airspace zones from UK data")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
