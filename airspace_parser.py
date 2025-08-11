#!/usr/bin/env python3
"""
UK Airspace Data Parser for Professional Radar Display
Parses UK airspace data files and provides airspace identification services
"""

import os
import re
import json
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

@dataclass
class AirspaceZone:
    """Represents a single airspace zone"""
    name: str
    type: str
    type_code: int
    coordinates: List[Tuple[float, float]]
    polygon: Polygon
    description: str = ""
    altitude_min: str = "SFC"
    altitude_max: str = "UNL"

class UKAirspaceParser:
    """Parser for UK airspace data files"""
    
    # Airspace type mappings based on $TYPE values from the readme
    TYPE_MAPPINGS = {
        5: "Final Approach",
        6: "Lower Airway CL", 
        7: "Upper Airway CL",
        8: "ATZ",
        9: "CTA/TMA", 
        10: "CTR",
        11: "Danger Area",
        12: "FIR",
        13: "TACAN Route",
        15: "VOR Roses",
        17: "LARS",
        18: "MATZ",
        19: "Lower Airway Boundary",
        20: "AARA",
        21: "AIAA", 
        22: "MTA",
        23: "ATA",
        24: "ATSDA"
    }
    
    def __init__(self, airspace_dir: str = "data/OUT_UK_Airspace"):
        self.airspace_dir = airspace_dir
        self.zones: List[AirspaceZone] = []
        self.zones_by_type: Dict[str, List[AirspaceZone]] = {}
        
    def parse_all_airspace(self) -> None:
        """Parse all airspace files in the directory"""
        if not os.path.exists(self.airspace_dir):
            print(f"Airspace directory not found: {self.airspace_dir}")
            return
            
        print(f"🗺️  Parsing UK airspace data from {self.airspace_dir}")
        
        # Priority order for parsing (most important first)
        priority_patterns = [
            "UK_CTR_*",      # Control Zones (highest priority)
            "UK_CTA_*",      # Control Areas  
            "UK_TMA_*",      # Terminal Control Areas
            "UK_DA_*",       # Danger/Prohibited/Restricted Areas
            "UK_ATZ*",       # Aerodrome Traffic Zones
            "UK_MIL_MATZ*",  # Military ATZ
            "UK_AWY_*",      # Airways
            "UK_FIR*",       # Flight Information Regions
            "UK_LARS_*",     # Lower Airspace Radar Service
            "UK_MIL_*",      # Military areas
        ]
        
        parsed_files = 0
        for pattern in priority_patterns:
            files = self._find_files(pattern)
            for file_path in files:
                try:
                    zones = self._parse_airspace_file(file_path)
                    self.zones.extend(zones)
                    parsed_files += 1
                except Exception as e:
                    print(f"❌ Error parsing {file_path}: {e}")
                    
        # Organize zones by type
        self._organize_zones_by_type()
        
        print(f"✅ Parsed {parsed_files} airspace files, loaded {len(self.zones)} zones")
        print(f"📊 Zone types: {', '.join([f'{k}({len(v)})' for k, v in self.zones_by_type.items()])}")
        
    def _find_files(self, pattern: str) -> List[str]:
        """Find files matching a pattern"""
        import glob
        pattern_path = os.path.join(self.airspace_dir, pattern.replace("*", "*.out"))
        return glob.glob(pattern_path)
        
    def _parse_airspace_file(self, file_path: str) -> List[AirspaceZone]:
        """Parse a single airspace file"""
        zones = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Extract zone name from filename and content
        filename = os.path.basename(file_path)
        zone_name = self._extract_zone_name(filename, content)
        
        # Extract type code
        type_match = re.search(r'\$TYPE=(\d+)', content)
        type_code = int(type_match.group(1)) if type_match else 0
        type_name = self.TYPE_MAPPINGS.get(type_code, f"Type_{type_code}")
        
        # Parse coordinate blocks
        coordinate_blocks = self._parse_coordinate_blocks(content)
        
        for i, coords in enumerate(coordinate_blocks):
            if len(coords) < 3:  # Need at least 3 points for a polygon
                continue
                
            try:
                # Create polygon from coordinates
                polygon = Polygon(coords)
                if not polygon.is_valid:
                    polygon = polygon.buffer(0)  # Fix invalid polygons
                    
                zone_id = f"{zone_name}_{i+1}" if len(coordinate_blocks) > 1 else zone_name
                
                zone = AirspaceZone(
                    name=zone_id,
                    type=type_name,
                    type_code=type_code,
                    coordinates=coords,
                    polygon=polygon,
                    description=self._get_zone_description(filename, type_name)
                )
                
                zones.append(zone)
                
            except Exception as e:
                print(f"⚠️  Skipping invalid polygon in {filename}: {e}")
                continue
                
        return zones
        
    def _extract_zone_name(self, filename: str, content: str) -> str:
        """Extract zone name from filename and content"""
        # Try to get name from content first
        name_match = re.search(r'\{([^}]+)\}', content)
        if name_match:
            return name_match.group(1)
            
        # Fall back to filename parsing
        name = filename.replace('.out', '').replace('UK_', '')
        
        # Clean up common patterns
        name = re.sub(r'_[A-Z]_', ' ', name)  # Replace _X_ with space
        name = name.replace('_', ' ')
        
        return name.title()
        
    def _parse_coordinate_blocks(self, content: str) -> List[List[Tuple[float, float]]]:
        """Parse coordinate blocks from file content"""
        blocks = []
        current_block = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith(';') or line.startswith('$') or line.startswith('{') or not line:
                continue
                
            # End of block marker
            if line == '-1':
                if current_block and len(current_block) >= 3:
                    blocks.append(current_block)
                current_block = []
                continue
                
            # Parse coordinate line
            coord_match = re.match(r'^(-?\d+\.\d+)\+(-?\d+\.\d+)$', line)
            if coord_match:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                current_block.append((lon, lat))  # Shapely uses (lon, lat) order
                
        # Add final block if exists
        if current_block and len(current_block) >= 3:
            blocks.append(current_block)
            
        return blocks
        
    def _get_zone_description(self, filename: str, type_name: str) -> str:
        """Generate description for a zone"""
        descriptions = {
            "CTR": "Control Zone - Controlled airspace around an airport",
            "CTA": "Control Area - Controlled airspace en-route",
            "TMA": "Terminal Control Area - Controlled airspace around major airports",
            "ATZ": "Aerodrome Traffic Zone - Airspace around smaller airports",
            "MATZ": "Military Aerodrome Traffic Zone",
            "Danger Area": "Danger Area - Hazardous activities",
            "AIAA": "Area of Intense Aerial Activity",
            "AARA": "Air-to-Air Refuelling Area",
            "MTA": "Military Training Area",
            "ATA": "Aerial Tactics Area",
            "LARS": "Lower Airspace Radar Service",
            "FIR": "Flight Information Region"
        }
        
        for key, desc in descriptions.items():
            if key.lower() in filename.lower() or key in type_name:
                return desc
                
        return f"{type_name} airspace"
        
    def _organize_zones_by_type(self) -> None:
        """Organize zones by type for efficient lookup"""
        self.zones_by_type = {}
        for zone in self.zones:
            if zone.type not in self.zones_by_type:
                self.zones_by_type[zone.type] = []
            self.zones_by_type[zone.type].append(zone)
            
    def find_airspace_for_position(self, lat: float, lon: float) -> List[AirspaceZone]:
        """Find all airspace zones containing a given position"""
        point = Point(lon, lat)  # Shapely uses (lon, lat) order
        containing_zones = []
        
        # Check priority zones first (CTR, CTA, TMA)
        priority_types = ["CTR", "CTA/TMA", "TMA"]
        
        for zone_type in priority_types:
            if zone_type in self.zones_by_type:
                for zone in self.zones_by_type[zone_type]:
                    try:
                        if zone.polygon.contains(point):
                            containing_zones.append(zone)
                    except Exception:
                        continue
                        
        # If no priority zones found, check other types
        if not containing_zones:
            for zone_type, zones in self.zones_by_type.items():
                if zone_type in priority_types:
                    continue
                for zone in zones:
                    try:
                        if zone.polygon.contains(point):
                            containing_zones.append(zone)
                    except Exception:
                        continue
                        
        return containing_zones
        
    def get_zones_in_area(self, center_lat: float, center_lon: float, radius_nm: float) -> List[AirspaceZone]:
        """Get all airspace zones within a given radius"""
        center_point = Point(center_lon, center_lat)
        
        # Convert nautical miles to degrees (approximate)
        radius_deg = radius_nm / 60.0
        
        nearby_zones = []
        for zone in self.zones:
            try:
                # Check if zone intersects with circular area
                if zone.polygon.distance(center_point) <= radius_deg:
                    nearby_zones.append(zone)
            except Exception:
                continue
                
        return nearby_zones
        
    def export_for_visualization(self, center_lat: float, center_lon: float, radius_nm: float) -> Dict:
        """Export airspace data for radar visualization"""
        zones = self.get_zones_in_area(center_lat, center_lon, radius_nm)
        
        export_data = {
            "center": {"lat": center_lat, "lon": center_lon},
            "radius_nm": radius_nm,
            "zones": [],
            "summary": {
                "total_zones": len(zones),
                "by_type": {}
            }
        }
        
        for zone in zones:
            # Convert coordinates back to lat/lon for visualization
            coords_latlon = [(lat, lon) for lon, lat in zone.coordinates]
            
            zone_data = {
                "name": zone.name,
                "type": zone.type,
                "type_code": zone.type_code,
                "coordinates": coords_latlon,
                "description": zone.description,
                "altitude_min": zone.altitude_min,
                "altitude_max": zone.altitude_max
            }
            
            export_data["zones"].append(zone_data)
            
            # Update summary
            if zone.type not in export_data["summary"]["by_type"]:
                export_data["summary"]["by_type"][zone.type] = 0
            export_data["summary"]["by_type"][zone.type] += 1
            
        return export_data
        
    def get_airspace_info_for_ai(self, lat: float, lon: float, altitude_ft: Optional[int] = None) -> str:
        """Get human-readable airspace information for AI assistant"""
        zones = self.find_airspace_for_position(lat, lon)
        
        if not zones:
            return f"Position {lat:.4f}°N, {lon:.4f}°W is in uncontrolled airspace"
            
        info_parts = [f"Position {lat:.4f}°N, {lon:.4f}°W is within:"]
        
        # Sort zones by priority (CTR highest, then CTA, etc.)
        priority_order = {"CTR": 1, "CTA/TMA": 2, "TMA": 3, "ATZ": 4, "MATZ": 5}
        zones.sort(key=lambda z: priority_order.get(z.type, 99))
        
        for zone in zones[:3]:  # Limit to top 3 most relevant zones
            info_parts.append(f"• {zone.name} ({zone.type}) - {zone.description}")
            
        if altitude_ft:
            info_parts.append(f"Aircraft altitude: {altitude_ft} feet")
            
        return "\n".join(info_parts)

def main():
    """Test the airspace parser"""
    parser = UKAirspaceParser()
    parser.parse_all_airspace()
    
    # Test with Prestwick coordinates
    prestwick_lat = 55.5094
    prestwick_lon = -4.5967
    
    print(f"\n🔍 Testing airspace lookup for Prestwick Airport:")
    zones = parser.find_airspace_for_position(prestwick_lat, prestwick_lon)
    for zone in zones:
        print(f"  • {zone.name} ({zone.type})")
        
    print(f"\n🗺️  Airspace zones within 50nm of Prestwick:")
    nearby = parser.get_zones_in_area(prestwick_lat, prestwick_lon, 50)
    print(f"  Found {len(nearby)} zones")
    
    # Export sample data
    export_data = parser.export_for_visualization(prestwick_lat, prestwick_lon, 25)
    print(f"\n📊 Export summary: {export_data['summary']}")

if __name__ == "__main__":
    main()
