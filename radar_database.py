#!/usr/bin/env python3
"""
Radar Database System for Historical Contact Storage
Stores ADS-B, radar, and AIS data with full historical context
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RadarDatabase:
    def __init__(self, db_path: str = "radar_history.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Aircraft contacts table - stores all ADS-B data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aircraft_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hex TEXT NOT NULL,
                    flight TEXT,
                    timestamp REAL NOT NULL,
                    lat REAL,
                    lon REAL,
                    alt_baro INTEGER,
                    alt_geom INTEGER,
                    gs REAL,
                    track REAL,
                    baro_rate INTEGER,
                    squawk TEXT,
                    category TEXT,
                    seen REAL,
                    rssi REAL,
                    messages INTEGER,
                    airspace_type TEXT,
                    airspace_name TEXT,
                    flight_phase TEXT,
                    atc_center TEXT,
                    intention TEXT,
                    raw_data TEXT
                )
            ''')
            
            # Aircraft summary table - tracks aircraft lifecycle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aircraft_summary (
                    hex TEXT PRIMARY KEY,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    total_contacts INTEGER DEFAULT 1,
                    callsigns TEXT, -- JSON array of all callsigns seen
                    airports_visited TEXT, -- JSON array of airports
                    max_altitude INTEGER,
                    min_altitude INTEGER,
                    total_distance REAL DEFAULT 0,
                    flight_phases TEXT, -- JSON array of phases seen
                    squawk_codes TEXT, -- JSON array of squawk codes used
                    airspace_history TEXT -- JSON array of airspaces visited
                )
            ''')
            
            # Ship contacts table - stores AIS data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ship_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mmsi TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    lat REAL,
                    lon REAL,
                    speed REAL,
                    course REAL,
                    heading INTEGER,
                    nav_status INTEGER,
                    vessel_type INTEGER,
                    name TEXT,
                    callsign TEXT,
                    destination TEXT,
                    length INTEGER,
                    width INTEGER,
                    raw_data TEXT
                )
            ''')
            
            # Ship summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ship_summary (
                    mmsi TEXT PRIMARY KEY,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    total_contacts INTEGER DEFAULT 1,
                    vessel_names TEXT, -- JSON array of names seen
                    destinations TEXT, -- JSON array of destinations
                    ports_visited TEXT, -- JSON array of estimated ports
                    max_speed REAL,
                    total_distance REAL DEFAULT 0,
                    vessel_types TEXT -- JSON array of types seen
                )
            ''')
            
            # Flight events table - tracks significant events
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hex TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL, -- TAKEOFF, LANDING, EMERGENCY, LOST_CONTACT, etc.
                    location_lat REAL,
                    location_lon REAL,
                    altitude INTEGER,
                    airport_code TEXT,
                    squawk_code TEXT,
                    details TEXT, -- JSON with additional event details
                    confidence REAL DEFAULT 1.0
                )
            ''')
            
            # Performance analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    total_aircraft INTEGER,
                    total_ships INTEGER,
                    active_aircraft INTEGER,
                    active_ships INTEGER,
                    db_size_mb REAL,
                    oldest_record REAL,
                    newest_record REAL
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_aircraft_hex_time ON aircraft_contacts(hex, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_aircraft_time ON aircraft_contacts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_aircraft_flight ON aircraft_contacts(flight)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ship_mmsi_time ON ship_contacts(mmsi, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ship_time ON ship_contacts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_hex ON flight_events(hex)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON flight_events(event_type)')
            
            conn.commit()
            logger.info("📊 Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Thread-safe database connection"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def store_aircraft_contact(self, aircraft_data: Dict) -> bool:
        """Store aircraft contact data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Extract data with defaults
                hex_code = aircraft_data.get('hex', '')
                if not hex_code:
                    return False
                
                timestamp = time.time()
                flight = aircraft_data.get('flight', '').strip()
                lat = aircraft_data.get('lat')
                lon = aircraft_data.get('lon')
                
                # Store contact
                cursor.execute('''
                    INSERT INTO aircraft_contacts (
                        hex, flight, timestamp, lat, lon, alt_baro, alt_geom, gs, track,
                        baro_rate, squawk, category, seen, rssi, messages,
                        airspace_type, airspace_name, flight_phase, atc_center, intention, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    hex_code, flight, timestamp, lat, lon,
                    aircraft_data.get('alt_baro'), aircraft_data.get('alt_geom'),
                    aircraft_data.get('gs'), aircraft_data.get('track'),
                    aircraft_data.get('baro_rate'), aircraft_data.get('squawk'),
                    aircraft_data.get('category'), aircraft_data.get('seen'),
                    aircraft_data.get('rssi'), aircraft_data.get('messages'),
                    aircraft_data.get('airspace', {}).get('type'),
                    aircraft_data.get('airspace', {}).get('name'),
                    aircraft_data.get('status', {}).get('phase'),
                    aircraft_data.get('status', {}).get('atc'),
                    aircraft_data.get('status', {}).get('intention'),
                    json.dumps(aircraft_data)
                ))
                
                # Update or create summary
                self._update_aircraft_summary(cursor, hex_code, aircraft_data, timestamp)
                
                # Check for significant events
                self._detect_flight_events(cursor, hex_code, aircraft_data, timestamp)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing aircraft contact: {e}")
            return False
    
    def store_ship_contact(self, ship_data: Dict) -> bool:
        """Store ship contact data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                mmsi = str(ship_data.get('mmsi', ''))
                if not mmsi:
                    return False
                
                timestamp = time.time()
                
                cursor.execute('''
                    INSERT INTO ship_contacts (
                        mmsi, timestamp, lat, lon, speed, course, heading,
                        nav_status, vessel_type, name, callsign, destination,
                        length, width, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    mmsi, timestamp,
                    ship_data.get('lat'), ship_data.get('lon'),
                    ship_data.get('speed'), ship_data.get('course'),
                    ship_data.get('heading'), ship_data.get('nav_status'),
                    ship_data.get('vessel_type'), ship_data.get('name'),
                    ship_data.get('callsign'), ship_data.get('destination'),
                    ship_data.get('length'), ship_data.get('width'),
                    json.dumps(ship_data)
                ))
                
                self._update_ship_summary(cursor, mmsi, ship_data, timestamp)
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing ship contact: {e}")
            return False
    
    def _update_aircraft_summary(self, cursor, hex_code: str, data: Dict, timestamp: float):
        """Update aircraft summary record"""
        # Get existing summary
        cursor.execute('SELECT * FROM aircraft_summary WHERE hex = ?', (hex_code,))
        existing = cursor.fetchone()
        
        flight = data.get('flight', '').strip()
        altitude = data.get('alt_baro', 0) or 0
        
        if existing:
            # Update existing
            callsigns = json.loads(existing['callsigns'] or '[]')
            if flight and flight not in callsigns:
                callsigns.append(flight)
            
            flight_phases = json.loads(existing['flight_phases'] or '[]')
            phase = data.get('status', {}).get('phase')
            if phase and phase not in flight_phases:
                flight_phases.append(phase)
            
            squawk_codes = json.loads(existing['squawk_codes'] or '[]')
            squawk = data.get('squawk')
            if squawk and squawk not in squawk_codes:
                squawk_codes.append(squawk)
            
            cursor.execute('''
                UPDATE aircraft_summary SET
                    last_seen = ?, total_contacts = total_contacts + 1,
                    callsigns = ?, flight_phases = ?, squawk_codes = ?,
                    max_altitude = MAX(max_altitude, ?),
                    min_altitude = MIN(min_altitude, ?)
                WHERE hex = ?
            ''', (
                timestamp, json.dumps(callsigns), json.dumps(flight_phases),
                json.dumps(squawk_codes), altitude, altitude, hex_code
            ))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO aircraft_summary (
                    hex, first_seen, last_seen, callsigns, max_altitude, min_altitude,
                    flight_phases, squawk_codes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                hex_code, timestamp, timestamp,
                json.dumps([flight] if flight else []),
                altitude, altitude,
                json.dumps([data.get('status', {}).get('phase')] if data.get('status', {}).get('phase') else []),
                json.dumps([data.get('squawk')] if data.get('squawk') else [])
            ))
    
    def _update_ship_summary(self, cursor, mmsi: str, data: Dict, timestamp: float):
        """Update ship summary record"""
        cursor.execute('SELECT * FROM ship_summary WHERE mmsi = ?', (mmsi,))
        existing = cursor.fetchone()
        
        name = data.get('name', '').strip()
        speed = data.get('speed', 0) or 0
        
        if existing:
            names = json.loads(existing['vessel_names'] or '[]')
            if name and name not in names:
                names.append(name)
            
            cursor.execute('''
                UPDATE ship_summary SET
                    last_seen = ?, total_contacts = total_contacts + 1,
                    vessel_names = ?, max_speed = MAX(max_speed, ?)
                WHERE mmsi = ?
            ''', (timestamp, json.dumps(names), speed, mmsi))
        else:
            cursor.execute('''
                INSERT INTO ship_summary (
                    mmsi, first_seen, last_seen, vessel_names, max_speed
                ) VALUES (?, ?, ?, ?, ?)
            ''', (mmsi, timestamp, timestamp, json.dumps([name] if name else []), speed))
    
    def _detect_flight_events(self, cursor, hex_code: str, data: Dict, timestamp: float):
        """Detect and store significant flight events"""
        altitude = data.get('alt_baro', 0) or 0
        squawk = data.get('squawk', '0000')
        phase = data.get('status', {}).get('phase', '')
        
        # Get recent history for this aircraft
        cursor.execute('''
            SELECT alt_baro, flight_phase, squawk FROM aircraft_contacts 
            WHERE hex = ? AND timestamp > ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (hex_code, timestamp - 300))  # Last 5 minutes
        
        recent = cursor.fetchall()
        
        # Emergency squawk detection
        if squawk in ['7500', '7600', '7700']:
            cursor.execute('''
                INSERT INTO flight_events (hex, timestamp, event_type, altitude, squawk_code, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (hex_code, timestamp, 'EMERGENCY_SQUAWK', altitude, squawk, 
                  json.dumps({'squawk_type': {'7500': 'HIJACK', '7600': 'RADIO_FAILURE', '7700': 'EMERGENCY'}[squawk]})))
        
        # Takeoff detection (altitude rapidly increasing from low level)
        if len(recent) >= 3 and altitude > 1000:
            recent_alts = [r['alt_baro'] for r in recent if r['alt_baro']]
            if recent_alts and min(recent_alts) < 500 and altitude - min(recent_alts) > 800:
                cursor.execute('''
                    INSERT INTO flight_events (hex, timestamp, event_type, altitude, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (hex_code, timestamp, 'TAKEOFF', altitude, json.dumps({'climb_rate': 'rapid'})))
        
        # Landing detection (altitude decreasing to low level)
        if len(recent) >= 3 and altitude < 500:
            recent_alts = [r['alt_baro'] for r in recent if r['alt_baro']]
            if recent_alts and max(recent_alts) > 2000:
                cursor.execute('''
                    INSERT INTO flight_events (hex, timestamp, event_type, altitude, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (hex_code, timestamp, 'LANDING', altitude, json.dumps({'descent_from': max(recent_alts)})))
    
    def get_aircraft_history(self, hex_code: str, hours: int = 24) -> List[Dict]:
        """Get historical data for specific aircraft"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since = time.time() - (hours * 3600)
            
            cursor.execute('''
                SELECT * FROM aircraft_contacts 
                WHERE hex = ? AND timestamp > ?
                ORDER BY timestamp ASC
            ''', (hex_code, since))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_aircraft_summary(self, hex_code: str) -> Optional[Dict]:
        """Get summary information for aircraft"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM aircraft_summary WHERE hex = ?', (hex_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_flight_events(self, hex_code: str = None, event_type: str = None, hours: int = 24) -> List[Dict]:
        """Get flight events"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since = time.time() - (hours * 3600)
            
            query = 'SELECT * FROM flight_events WHERE timestamp > ?'
            params = [since]
            
            if hex_code:
                query += ' AND hex = ?'
                params.append(hex_code)
            
            if event_type:
                query += ' AND event_type = ?'
                params.append(event_type)
            
            query += ' ORDER BY timestamp DESC'
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_aircraft(self, minutes: int = 5) -> List[Dict]:
        """Get aircraft seen in last N minutes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since = time.time() - (minutes * 60)
            
            cursor.execute('''
                SELECT hex, MAX(timestamp) as last_seen, flight, lat, lon, alt_baro
                FROM aircraft_contacts 
                WHERE timestamp > ? 
                GROUP BY hex
                ORDER BY last_seen DESC
            ''', (since,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count records
            cursor.execute('SELECT COUNT(*) FROM aircraft_contacts')
            stats['total_aircraft_contacts'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM ship_contacts')
            stats['total_ship_contacts'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM aircraft_summary')
            stats['unique_aircraft'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM flight_events')
            stats['total_events'] = cursor.fetchone()[0]
            
            # Time ranges
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM aircraft_contacts')
            row = cursor.fetchone()
            if row[0]:
                stats['oldest_aircraft_contact'] = datetime.fromtimestamp(row[0]).isoformat()
                stats['newest_aircraft_contact'] = datetime.fromtimestamp(row[1]).isoformat()
            
            # Database size
            import os
            if os.path.exists(self.db_path):
                stats['database_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            return stats
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Remove data older than specified days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = time.time() - (days * 24 * 3600)
            
            # Remove old contacts
            cursor.execute('DELETE FROM aircraft_contacts WHERE timestamp < ?', (cutoff,))
            aircraft_deleted = cursor.rowcount
            
            cursor.execute('DELETE FROM ship_contacts WHERE timestamp < ?', (cutoff,))
            ship_deleted = cursor.rowcount
            
            # Update summaries for aircraft that still have recent data
            cursor.execute('''
                UPDATE aircraft_summary 
                SET first_seen = (
                    SELECT MIN(timestamp) FROM aircraft_contacts 
                    WHERE aircraft_contacts.hex = aircraft_summary.hex
                )
                WHERE hex IN (SELECT DISTINCT hex FROM aircraft_contacts)
            ''')
            
            # Remove summaries for aircraft with no remaining data
            cursor.execute('''
                DELETE FROM aircraft_summary 
                WHERE hex NOT IN (SELECT DISTINCT hex FROM aircraft_contacts)
            ''')
            
            conn.commit()
            logger.info(f"🧹 Cleaned up {aircraft_deleted + ship_deleted} old records")
            return aircraft_deleted + ship_deleted

# Global database instance
radar_db = RadarDatabase()

if __name__ == "__main__":
    # Test the database
    print("🧪 Testing Radar Database...")
    
    # Test aircraft storage
    test_aircraft = {
        'hex': 'ABC123',
        'flight': 'BAW123',
        'lat': 55.5,
        'lon': -4.5,
        'alt_baro': 35000,
        'gs': 450,
        'squawk': '2000',
        'status': {'phase': 'CRUISE', 'atc': 'Scottish Control', 'intention': 'En route EGLL'}
    }
    
    radar_db.store_aircraft_contact(test_aircraft)
    
    # Get stats
    stats = radar_db.get_database_stats()
    print(f"📊 Database Stats: {json.dumps(stats, indent=2)}")
    
    print("✅ Database test completed!")
