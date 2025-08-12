#!/usr/bin/env python3
"""
BaseStation Database Integration Module

This module provides access to the BaseStation.sqb database containing
detailed aircraft information including registrations, types, manufacturers,
and operator details.

The database contains over 529,000 aircraft records with ModeS codes,
making it an invaluable resource for aircraft identification and information.
"""

import sqlite3
import os
from typing import Dict, Optional, List, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseStationDB:
    """Interface to the BaseStation.sqb aircraft database."""
    
    def __init__(self, db_path: str = "data/BaseStation.sqb"):
        """Initialize the BaseStation database connection.
        
        Args:
            db_path: Path to the BaseStation.sqb file
        """
        self.db_path = db_path
        # Don't create connection here - create per thread
    
    def _get_connection(self):
        """Get a thread-local database connection."""
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                return conn
            else:
                logger.warning(f"⚠️ BaseStation database not found at: {self.db_path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error connecting to BaseStation database: {e}")
            return None
    
    def get_aircraft_info(self, mode_s: str) -> Optional[Dict]:
        """Get detailed aircraft information by ModeS code.
        
        Args:
            mode_s: 6-character ModeS code (hex)
            
        Returns:
            Dictionary containing aircraft information or None if not found
        """
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            
            # Clean the ModeS code and search with quotes (as stored in database)
            mode_s = mode_s.strip("'").upper()
            
            cursor.execute("""
                SELECT ModeS, Registration, ICAOTypeCode, OperatorFlagCode, 
                       Manufacturer, Type, RegisteredOwners
                FROM Aircraft 
                WHERE ModeS = ? OR ModeS = ?
            """, (mode_s, f"'{mode_s}'"))
            
            row = cursor.fetchone()
            if row:
                return {
                    'mode_s': row['ModeS'],
                    'registration': row['Registration'] if row['Registration'] else None,
                    'icao_type': row['ICAOTypeCode'] if row['ICAOTypeCode'] else None,
                    'operator': row['OperatorFlagCode'] if row['OperatorFlagCode'] else None,
                    'manufacturer': row['Manufacturer'] if row['Manufacturer'] else None,
                    'type': row['Type'] if row['Type'] else None,
                    'owner': row['RegisteredOwners'] if row['RegisteredOwners'] else None
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error querying aircraft info for {mode_s}: {e}")
            return None
        finally:
            conn.close()
    
    def search_by_registration(self, registration: str) -> List[Dict]:
        """Search for aircraft by registration number.
        
        Args:
            registration: Aircraft registration (e.g., 'G-EKIM')
            
        Returns:
            List of matching aircraft records
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            registration = registration.upper().strip()
            
            cursor.execute("""
                SELECT ModeS, Registration, ICAOTypeCode, OperatorFlagCode, 
                       Manufacturer, Type, RegisteredOwners
                FROM Aircraft 
                WHERE Registration LIKE ?
                ORDER BY Registration
                LIMIT 50
            """, (f"%{registration}%",))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'mode_s': row['ModeS'],
                    'registration': row['Registration'] if row['Registration'] else None,
                    'icao_type': row['ICAOTypeCode'] if row['ICAOTypeCode'] else None,
                    'operator': row['OperatorFlagCode'] if row['OperatorFlagCode'] else None,
                    'manufacturer': row['Manufacturer'] if row['Manufacturer'] else None,
                    'type': row['Type'] if row['Type'] else None,
                    'owner': row['RegisteredOwners'] if row['RegisteredOwners'] else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching by registration {registration}: {e}")
            return []
        finally:
            conn.close()
    
    def search_by_type(self, aircraft_type: str) -> List[Dict]:
        """Search for aircraft by type.
        
        Args:
            aircraft_type: Aircraft type (e.g., 'B738', 'A320')
            
        Returns:
            List of matching aircraft records
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            aircraft_type = aircraft_type.upper().strip()
            
            cursor.execute("""
                SELECT ModeS, Registration, ICAOTypeCode, OperatorFlagCode, 
                       Manufacturer, Type, RegisteredOwners
                FROM Aircraft 
                WHERE ICAOTypeCode LIKE ? OR Type LIKE ?
                ORDER BY Registration
                LIMIT 100
            """, (f"%{aircraft_type}%", f"%{aircraft_type}%"))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'mode_s': row['ModeS'],
                    'registration': row['Registration'] if row['Registration'] else None,
                    'icao_type': row['ICAOTypeCode'] if row['ICAOTypeCode'] else None,
                    'operator': row['OperatorFlagCode'] if row['OperatorFlagCode'] else None,
                    'manufacturer': row['Manufacturer'] if row['Manufacturer'] else None,
                    'type': row['Type'] if row['Type'] else None,
                    'owner': row['RegisteredOwners'] if row['RegisteredOwners'] else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching by type {aircraft_type}: {e}")
            return []
        finally:
            conn.close()
    
    def get_aircraft_stats(self) -> Dict:
        """Get database statistics and summary information.
        
        Returns:
            Dictionary containing database statistics
        """
        conn = self._get_connection()
        if not conn:
            return {}
            
        try:
            cursor = conn.cursor()
            stats = {}
            
            # Total aircraft count
            cursor.execute("SELECT COUNT(*) FROM Aircraft")
            stats['total_aircraft'] = cursor.fetchone()[0]
            
            # Aircraft with registrations
            cursor.execute("SELECT COUNT(*) FROM Aircraft WHERE Registration != ''")
            stats['with_registration'] = cursor.fetchone()[0]
            
            # Aircraft with type codes
            cursor.execute("SELECT COUNT(*) FROM Aircraft WHERE ICAOTypeCode != ''")
            stats['with_type_code'] = cursor.fetchone()[0]
            
            # Top manufacturers
            cursor.execute("""
                SELECT Manufacturer, COUNT(*) as count 
                FROM Aircraft 
                WHERE Manufacturer != '' 
                GROUP BY Manufacturer 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_manufacturers'] = [dict(row) for row in cursor.fetchall()]
            
            # Top aircraft types
            cursor.execute("""
                SELECT ICAOTypeCode, COUNT(*) as count 
                FROM Aircraft 
                WHERE ICAOTypeCode != '' 
                GROUP BY ICAOTypeCode 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_types'] = [dict(row) for row in cursor.fetchall()]
            
            # Registration country distribution
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN Registration LIKE 'G-%' THEN 'UK'
                        WHEN Registration LIKE 'N-%' THEN 'USA'
                        WHEN Registration LIKE 'C-%' THEN 'Canada'
                        WHEN Registration LIKE 'D-%' THEN 'Germany'
                        WHEN Registration LIKE 'F-%' THEN 'France'
                        WHEN Registration LIKE 'I-%' THEN 'Italy'
                        WHEN Registration LIKE 'EC-%' THEN 'Spain'
                        WHEN Registration LIKE 'PH-%' THEN 'Netherlands'
                        WHEN Registration LIKE 'SE-%' THEN 'Sweden'
                        WHEN Registration LIKE 'LN-%' THEN 'Norway'
                        ELSE 'Other'
                    END as country,
                        COUNT(*) as count
                FROM Aircraft 
                WHERE Registration != ''
                GROUP BY country
                ORDER BY count DESC
            """)
            stats['country_distribution'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}
        finally:
            conn.close()
    
    def enhance_aircraft_data(self, aircraft_list: List[Dict]) -> List[Dict]:
        """Enhance a list of aircraft data with BaseStation information.
        
        Args:
            aircraft_list: List of aircraft dictionaries with ModeS codes
            
        Returns:
            Enhanced aircraft list with additional information
        """
        enhanced_list = []
        
        for aircraft in aircraft_list:
            enhanced_aircraft = aircraft.copy()
            
            # Try to get additional info from BaseStation
            if 'hex' in aircraft:
                mode_s = aircraft['hex'].upper()
                basestation_info = self.get_aircraft_info(mode_s)
                
                if basestation_info:
                    enhanced_aircraft.update({
                        'registration': basestation_info.get('registration'),
                        'icao_type': basestation_info.get('icao_type'),
                        'manufacturer': basestation_info.get('manufacturer'),
                        'aircraft_type': basestation_info.get('type'),
                        'operator': basestation_info.get('operator'),
                        'owner': basestation_info.get('owner'),
                        'enhanced': True
                    })
                else:
                    enhanced_aircraft['enhanced'] = False
            
            enhanced_list.append(enhanced_aircraft)
        
        return enhanced_list
    
    def get_random_sample(self, count: int = 10) -> List[Dict]:
        """Get a random sample of aircraft from the database.
        
        Args:
            count: Number of aircraft to return
            
        Returns:
            List of random aircraft records
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ModeS, Registration, ICAOTypeCode, OperatorFlagCode, 
                       Manufacturer, Type, RegisteredOwners
                FROM Aircraft 
                WHERE Registration != '' AND ICAOTypeCode != ''
                ORDER BY RANDOM()
                LIMIT ?
            """, (count,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'mode_s': row['ModeS'],
                    'registration': row['Registration'] if row['Registration'] else None,
                    'icao_type': row['ICAOTypeCode'] if row['ICAOTypeCode'] else None,
                    'operator': row['OperatorFlagCode'] if row['OperatorFlagCode'] else None,
                    'manufacturer': row['Manufacturer'] if row['Manufacturer'] else None,
                    'type': row['Type'] if row['Type'] else None,
                    'owner': row['RegisteredOwners'] if row['RegisteredOwners'] else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting random sample: {e}")
            return []
        finally:
            conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass  # No connection to close


# Global instance for easy access
_basestation_db = None

def get_basestation_db() -> BaseStationDB:
    """Get the global BaseStation database instance."""
    global _basestation_db
    if _basestation_db is None:
        _basestation_db = BaseStationDB()
    return _basestation_db

def close_basestation_db():
    """Close the global BaseStation database instance."""
    global _basestation_db
    if _basestation_db:
        _basestation_db = None


if __name__ == "__main__":
    # Test the module
    with BaseStationDB() as db:
        print("🔍 Testing BaseStation database integration...")
        
        # Get database stats
        stats = db.get_aircraft_stats()
        print(f"📊 Database Statistics:")
        print(f"   Total Aircraft: {stats.get('total_aircraft', 0):,}")
        print(f"   With Registration: {stats.get('with_registration', 0):,}")
        print(f"   With Type Code: {stats.get('with_type_code', 0):,}")
        
        # Test aircraft lookup
        test_mode_s = "408092"  # G-ZBLH from our sample
        aircraft_info = db.get_aircraft_info(test_mode_s)
        if aircraft_info:
            print(f"\n✈️ Aircraft Lookup Test ({test_mode_s}):")
            for key, value in aircraft_info.items():
                print(f"   {key}: {value}")
        
        # Test registration search
        uk_results = db.search_by_registration("G-")
        print(f"\n🇬🇧 UK Aircraft Sample (showing first 5):")
        for i, aircraft in enumerate(uk_results[:5]):
            print(f"   {i+1}. {aircraft['registration']} - {aircraft['type']} ({aircraft['manufacturer']})")
        
        # Test type search
        boeing_results = db.search_by_type("B738")
        print(f"\n🛩️ Boeing 737-800 Sample (showing first 5):")
        for i, aircraft in enumerate(boeing_results[:5]):
            print(f"   {i+1}. {aircraft['registration']} - {aircraft['type']}")
        
        print("\n✅ BaseStation database integration test completed!")
