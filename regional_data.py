#!/usr/bin/env python3
"""
Regional Data Manager for Airspace Visualizer
Handles loading and managing regional airport and geographic data
"""

import json
import os
import math
import re
from typing import Dict, List, Optional, Tuple

class RegionalDataManager:
    def __init__(self, regions_dir: str = "regions"):
        self.regions_dir = regions_dir
        self.current_region = None
        self.available_regions = self._discover_regions()
        
    def _discover_regions(self) -> Dict[str, str]:
        """Discover available region files"""
        regions = {}
        if os.path.exists(self.regions_dir):
            for file in os.listdir(self.regions_dir):
                if file.endswith('.json'):
                    region_code = file.replace('.json', '').upper()
                    regions[region_code] = os.path.join(self.regions_dir, file)
        return regions
    
    def load_region(self, region_code: str) -> Optional[Dict]:
        """Load a specific region's data"""
        region_code = region_code.upper()
        if region_code not in self.available_regions:
            return None
            
        try:
            with open(self.available_regions[region_code], 'r') as f:
                region_data = json.load(f)
                self.current_region = region_data
                return region_data
        except Exception as e:
            print(f"Error loading region {region_code}: {e}")
            return None
    
    def get_region_center(self, region_code: str = None) -> Tuple[float, float]:
        """Get the center coordinates for a region"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        if region_data and 'region' in region_data:
            center = region_data['region']['center']
            return center['lat'], center['lon']
        
        # Default to Gulf Coast if no region loaded
        return 30.5, -87.5
    
    def get_airports(self, region_code: str = None) -> List[Dict]:
        """Get airports for a region"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        return region_data.get('airports', []) if region_data else []
    
    def get_airlines(self, region_code: str = None) -> List[Dict]:
        """Get airlines for a region"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        return region_data.get('airlines', []) if region_data else []
    
    def get_aircraft_types(self, region_code: str = None) -> List[Dict]:
        """Get aircraft types for a region"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        return region_data.get('aircraft_types', []) if region_data else []
    
    def get_acars_messages(self, region_code: str = None) -> List[str]:
        """Get ACARS messages for a region"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        return region_data.get('acars_messages', []) if region_data else []
    
    def generate_geographic_features(self, center_lat: float, center_lon: float, range_nm: float, region_code: str = None) -> List[Dict]:
        """Generate geographic features for a region within radar range"""
        if region_code:
            region_data = self.load_region(region_code)
        else:
            region_data = self.current_region
            
        if not region_data:
            return []
        
        features = []
        
        # First, try to load coastline from C15_COAST file if available
        coastline_file = "data/C15_COAST_N_Europe.out"
        if os.path.exists(coastline_file):
            coastline_features = self.parse_coastline_file(coastline_file, center_lat, center_lon, range_nm)
            features.extend(coastline_features)
        
        # Process geographic features from region JSON (coastlines, rivers, etc.)
        for geo_feature in region_data.get('geographic_features', []):
            feature_type = geo_feature['type']
            feature_name = geo_feature['name']
            
            # Skip coastline if we already loaded from C15_COAST file
            if feature_type == 'coastline' and os.path.exists(coastline_file):
                continue
            
            for coord in geo_feature.get('coordinates', []):
                distance = self._haversine_distance(center_lat, center_lon, coord['lat'], coord['lon'])
                if distance <= range_nm:
                    features.append({
                        'lat': coord['lat'],
                        'lon': coord['lon'],
                        'type': feature_type,
                        'name': feature_name,
                        'distance_nm': distance
                    })
        
        # Process airports
        for airport in region_data.get('airports', []):
            distance = self._haversine_distance(center_lat, center_lon, airport['lat'], airport['lon'])
            if distance <= range_nm:
                features.append({
                    'lat': airport['lat'],
                    'lon': airport['lon'],
                    'type': 'airport',
                    'name': f"{airport['name']} ({airport['icao']})",
                    'distance_nm': distance
                })
        
        # Process cities
        for city in region_data.get('cities', []):
            distance = self._haversine_distance(center_lat, center_lon, city['lat'], city['lon'])
            if distance <= range_nm:
                features.append({
                    'lat': city['lat'],
                    'lon': city['lon'],
                    'type': city['type'],  # 'city' or 'town'
                    'name': city['name'],
                    'distance_nm': distance
                })
        
        return features
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        R = 3440.065  # Earth's radius in nautical miles
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def parse_coastline_file(self, coastline_file: str, center_lat: float, center_lon: float, range_nm: float) -> List[Dict]:
        """Parse C15_COAST format coastline file and return coordinates within range"""
        coastline_points = []
        
        if not os.path.exists(coastline_file):
            print(f"Coastline file not found: {coastline_file}")
            return coastline_points
            
        try:
            with open(coastline_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if line.startswith(';') or line.startswith('$') or line.startswith('{') or not line:
                        continue
                    
                    # Parse coordinate lines (format: lat+-lon)
                    coord_match = re.match(r'^(-?\d+\.\d+)\+(-?\d+\.\d+)$', line)
                    if coord_match:
                        lat = float(coord_match.group(1))
                        lon = float(coord_match.group(2))
                        
                        # Check if within radar range
                        distance = self._haversine_distance(center_lat, center_lon, lat, lon)
                        if distance <= range_nm:
                            coastline_points.append({
                                'lat': lat,
                                'lon': lon,
                                'type': 'coastline',
                                'name': 'Coast',
                                'distance_nm': distance
                            })
                            
        except Exception as e:
            print(f"Error parsing coastline file: {e}")
            
        print(f"Loaded {len(coastline_points)} coastline points within {range_nm}nm of {center_lat:.4f}, {center_lon:.4f}")
        return coastline_points
    
    def get_available_regions(self) -> Dict[str, str]:
        """Get list of available regions"""
        region_info = {}
        for code, path in self.available_regions.items():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    region_info[code] = {
                        'name': data['region']['name'],
                        'country': data['region'].get('country', 'Unknown'),
                        'center': data['region']['center']
                    }
            except Exception as e:
                print(f"Error reading region {code}: {e}")
                continue
        return region_info

# Global instance
regional_manager = RegionalDataManager()
