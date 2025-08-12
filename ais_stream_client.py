#!/usr/bin/env python3
"""
AIS Stream Client for Maritime Vessel Tracking
Connects to AISStream.io WebSocket API for real-time ship data
"""

import asyncio
import websockets
import json
import threading
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class AISStreamClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.vessels = {}  # MMSI -> vessel data
        self.connection = None
        self.running = False
        self.thread = None
        
        # Default bounds for UK waters
        self.bounds = {
            'north': 60.0,   # Northern Scotland
            'south': 50.0,   # Southern England
            'east': 2.0,     # Eastern England
            'west': -10.0    # Western Ireland
        }
        
        # AIS message types to filter
        self.message_types = [
            "PositionReport",      # Types 1, 2, 3
            "BaseStationReport",   # Type 4
            "StaticAndVoyageData", # Type 5
            "StandardClassBPositionReport",  # Types 18, 19
            "AidToNavigationReport",         # Type 21
            "StaticDataReport"     # Type 24
        ]
        
        # Vessel type mappings
        self.vessel_types = {
            0: "Not specified",
            20: "Wing in ground",
            21: "Wing in ground (hazardous)",
            22: "Wing in ground (reserved)",
            30: "Fishing",
            31: "Towing",
            32: "Towing (large)",
            33: "Dredging",
            34: "Diving ops",
            35: "Military ops",
            36: "Sailing",
            37: "Pleasure craft",
            40: "High speed craft",
            41: "High speed craft (hazardous)",
            42: "High speed craft (reserved)",
            50: "Pilot vessel",
            51: "Search and rescue",
            52: "Tug",
            53: "Port tender",
            54: "Anti-pollution",
            55: "Law enforcement",
            56: "Spare - local vessel",
            57: "Spare - local vessel",
            58: "Medical transport",
            59: "Non-combatant ship",
            60: "Passenger",
            61: "Passenger (hazardous)",
            62: "Passenger (reserved)",
            63: "Passenger (reserved)",
            64: "Passenger (reserved)",
            65: "Passenger (reserved)",
            66: "Passenger (reserved)",
            67: "Passenger (reserved)",
            68: "Passenger (reserved)",
            69: "Passenger (no info)",
            70: "Cargo",
            71: "Cargo (hazardous)",
            72: "Cargo (reserved)",
            73: "Cargo (reserved)",
            74: "Cargo (reserved)",
            75: "Cargo (reserved)",
            76: "Cargo (reserved)",
            77: "Cargo (reserved)",
            78: "Cargo (reserved)",
            79: "Cargo (no info)",
            80: "Tanker",
            81: "Tanker (hazardous)",
            82: "Tanker (reserved)",
            83: "Tanker (reserved)",
            84: "Tanker (reserved)",
            85: "Tanker (reserved)",
            86: "Tanker (reserved)",
            87: "Tanker (reserved)",
            88: "Tanker (reserved)",
            89: "Tanker (no info)",
            90: "Other",
            91: "Other (hazardous)",
            92: "Other (reserved)",
            93: "Other (reserved)",
            94: "Other (reserved)",
            95: "Other (reserved)",
            96: "Other (reserved)",
            97: "Other (reserved)",
            98: "Other (reserved)",
            99: "Other (no info)"
        }
        
        # Navigation status mappings
        self.nav_status = {
            0: "Under way using engine",
            1: "At anchor",
            2: "Not under command",
            3: "Restricted maneuverability",
            4: "Constrained by draught",
            5: "Moored",
            6: "Aground",
            7: "Engaged in fishing",
            8: "Under way sailing",
            9: "Reserved for HSC",
            10: "Reserved for WIG",
            11: "Power-driven vessel towing astern",
            12: "Power-driven vessel pushing ahead",
            13: "Reserved",
            14: "AIS-SART",
            15: "Undefined"
        }

    def set_geographic_bounds(self, north: float, south: float, east: float, west: float):
        """Set geographic filtering bounds"""
        self.bounds = {
            'north': north,
            'south': south,
            'east': east,
            'west': west
        }
        print(f"🌍 AIS bounds set: {south}°N-{north}°N, {west}°W-{east}°E")

    def get_vessels_in_range(self, center_lat: float, center_lon: float, range_nm: float) -> List[Dict]:
        """Get all vessels within specified range of center point"""
        vessels_in_range = []
        current_time = datetime.now()
        
        for mmsi, vessel in self.vessels.items():
            try:
                # Skip stale data (older than 10 minutes)
                if vessel.get('last_update'):
                    last_update = datetime.fromisoformat(vessel['last_update'])
                    if (current_time - last_update).total_seconds() > 600:
                        continue
                
                # Calculate distance from center
                distance_nm = self._haversine_distance(
                    center_lat, center_lon,
                    vessel['lat'], vessel['lon']
                )
                
                if distance_nm <= range_nm:
                    vessel_copy = vessel.copy()
                    vessel_copy['distance_nm'] = round(distance_nm, 1)
                    vessel_copy['bearing'] = self._calculate_bearing(
                        center_lat, center_lon,
                        vessel['lat'], vessel['lon']
                    )
                    vessels_in_range.append(vessel_copy)
                    
            except (KeyError, ValueError, TypeError) as e:
                print(f"⚠️ Error processing vessel {mmsi}: {e}")
                continue
        
        # Sort by distance
        vessels_in_range.sort(key=lambda x: x.get('distance_nm', 999))
        return vessels_in_range

    def get_status(self) -> Dict:
        """Get connection status and statistics"""
        current_time = datetime.now()
        active_vessels = 0
        
        # Count active vessels (updated within last 10 minutes)
        for vessel in self.vessels.values():
            if vessel.get('last_update'):
                try:
                    last_update = datetime.fromisoformat(vessel['last_update'])
                    if (current_time - last_update).total_seconds() <= 600:
                        active_vessels += 1
                except ValueError:
                    continue
        
        # Count by vessel type
        type_counts = {}
        for vessel in self.vessels.values():
            vessel_type = vessel.get('vessel_type', 'Unknown')
            type_counts[vessel_type] = type_counts.get(vessel_type, 0) + 1
        
        return {
            'connected': self.running,
            'total_vessels': len(self.vessels),
            'active_vessels': active_vessels,
            'vessel_types': type_counts,
            'bounds': self.bounds,
            'last_update': current_time.isoformat()
        }

    def start_connection(self):
        """Start AIS WebSocket connection in background thread"""
        if self.running:
            print("🚢 AIS connection already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.thread.start()
        print("🚢 Starting AIS WebSocket connection...")

    def stop_connection(self):
        """Stop AIS WebSocket connection"""
        self.running = False
        if self.connection:
            asyncio.create_task(self.connection.close())
        print("🚢 AIS connection stopped")

    def _run_websocket(self):
        """Run WebSocket connection in asyncio event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_websocket())
        except Exception as e:
            print(f"❌ AIS WebSocket error: {e}")
        finally:
            loop.close()

    async def _connect_websocket(self):
        """Connect to AISStream.io WebSocket"""
        uri = "wss://stream.aisstream.io/v0/stream"
        
        # Subscription message with correct coordinate format
        subscribe_message = {
            "APIKey": self.api_key,
            "BoundingBoxes": [[
                [self.bounds['south'], self.bounds['west']],  # SW corner
                [self.bounds['north'], self.bounds['east']]   # NE corner
            ]],
            "FilterMessageTypes": self.message_types
        }
        
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                print(f"🔗 Connecting to AISStream.io... (attempt {retry_count + 1})")
                
                async with websockets.connect(uri) as websocket:
                    self.connection = websocket
                    
                    # Send subscription
                    await websocket.send(json.dumps(subscribe_message))
                    print("✅ AIS WebSocket connected and subscribed")
                    retry_count = 0  # Reset on successful connection
                    
                    # Listen for messages
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            self._process_ais_message(data)
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON decode error: {e}")
                        except Exception as e:
                            print(f"⚠️ Message processing error: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                print("🔌 AIS WebSocket connection closed")
            except Exception as e:
                print(f"❌ AIS WebSocket connection error: {e}")
                
            retry_count += 1
            if self.running and retry_count < max_retries:
                wait_time = min(2 ** retry_count, 60)  # Exponential backoff, max 60s
                print(f"🔄 Retrying in {wait_time} seconds... (rate limit protection)")
                await asyncio.sleep(wait_time)
        
        if retry_count >= max_retries:
            print("❌ AIS connection failed after maximum retries")
            self.running = False

    def _process_ais_message(self, data: Dict):
        """Process incoming AIS message"""
        try:
            message = data.get('Message', {})
            if not message:
                return
            
            # Extract common fields
            mmsi = message.get('UserID')
            if not mmsi:
                return
            
            # Get or create vessel record
            vessel = self.vessels.get(mmsi, {'mmsi': mmsi})
            
            # Update timestamp
            vessel['last_update'] = datetime.now().isoformat()
            
            # Process position data
            if 'Latitude' in message and 'Longitude' in message:
                vessel['lat'] = message['Latitude']
                vessel['lon'] = message['Longitude']
            
            # Process movement data
            if 'SpeedOverGround' in message:
                vessel['speed'] = round(message['SpeedOverGround'], 1)
            
            if 'CourseOverGround' in message:
                vessel['course'] = round(message['CourseOverGround'], 1)
            
            if 'TrueHeading' in message:
                vessel['heading'] = message['TrueHeading']
            
            # Process navigation status
            if 'NavigationalStatus' in message:
                status_code = message['NavigationalStatus']
                vessel['nav_status'] = self.nav_status.get(status_code, f"Unknown ({status_code})")
            
            # Process vessel type
            if 'ShipAndCargoType' in message:
                type_code = message['ShipAndCargoType']
                vessel['vessel_type'] = self.vessel_types.get(type_code, f"Unknown ({type_code})")
            
            # Process static data
            if 'VesselName' in message:
                vessel['name'] = message['VesselName'].strip()
            
            if 'CallSign' in message:
                vessel['callsign'] = message['CallSign'].strip()
            
            if 'Destination' in message:
                vessel['destination'] = message['Destination'].strip()
            
            # Process dimensions
            if 'DimToBow' in message and 'DimToStern' in message:
                vessel['length'] = message['DimToBow'] + message['DimToStern']
            
            if 'DimToPort' in message and 'DimToStarboard' in message:
                vessel['width'] = message['DimToPort'] + message['DimToStarboard']
            
            # Store vessel
            self.vessels[mmsi] = vessel
            
        except Exception as e:
            print(f"⚠️ Error processing AIS message: {e}")

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

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360

    def cleanup_stale_vessels(self, max_age_minutes: int = 10):
        """Remove vessels that haven't been updated recently"""
        current_time = datetime.now()
        stale_mmsis = []
        
        for mmsi, vessel in self.vessels.items():
            if vessel.get('last_update'):
                try:
                    last_update = datetime.fromisoformat(vessel['last_update'])
                    age_minutes = (current_time - last_update).total_seconds() / 60
                    if age_minutes > max_age_minutes:
                        stale_mmsis.append(mmsi)
                except ValueError:
                    stale_mmsis.append(mmsi)  # Invalid timestamp
        
        for mmsi in stale_mmsis:
            del self.vessels[mmsi]
        
        if stale_mmsis:
            print(f"🧹 Cleaned up {len(stale_mmsis)} stale vessels")

if __name__ == "__main__":
    # Test the client
    import os
    
    api_key = os.getenv("AISSTREAM_API_KEY", "test_key")
    client = AISStreamClient(api_key)
    
    print("🚢 AIS Stream Client Test")
    print(f"Status: {client.get_status()}")
    
    # Test with some mock data
    client.vessels = {
        123456789: {
            'mmsi': 123456789,
            'lat': 55.5,
            'lon': -4.6,
            'speed': 12.5,
            'course': 180,
            'name': 'Test Vessel',
            'vessel_type': 'Cargo',
            'nav_status': 'Under way using engine',
            'last_update': datetime.now().isoformat()
        }
    }
    
    vessels = client.get_vessels_in_range(55.5094, -4.5967, 50)
    print(f"Vessels in range: {len(vessels)}")
    for vessel in vessels:
        print(f"  {vessel['name']} ({vessel['mmsi']}) - {vessel['distance_nm']}nm")
