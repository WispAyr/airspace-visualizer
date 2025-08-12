#!/usr/bin/env python3
"""
SSR Code Parser and Context Provider
Parses SSR (Secondary Surveillance Radar) codes to provide aircraft context,
generate alerts for special operations, and enhance radar display.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class SSRCodeParser:
    def __init__(self, ssr_codes_file: str = 'data/SSR CODES.txt'):
        self.codes = {}
        self.categories = {
            'EMERGENCY': [],
            'MILITARY': [],
            'SAR': [],  # Search and Rescue
            'POLICE': [],
            'MEDICAL': [],
            'NATO': [],
            'QRA': [],  # Quick Reaction Alert
            'SPECIAL_OPS': [],
            'CONSPICUITY': [],
            'TRANSIT': [],
            'APPROACH': [],
            'MONITORING': [],
            'UNRELIABLE': []
        }
        self.alert_codes = set()
        self.load_ssr_codes(ssr_codes_file)
        self.categorize_codes()
    
    def load_ssr_codes(self, file_path: str):
        """Load and parse SSR codes from file"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or not line[0].isdigit():
                    continue
                
                # Parse line format: "0000. Description"
                match = re.match(r'^(\d{4})([-.]?\d*)\.?\s+(.+)$', line)
                if match:
                    code_start = match.group(1)
                    code_range = match.group(2)
                    description = match.group(3)
                    
                    if code_range and '-' in code_range:
                        # Handle range (e.g., "0001-0005")
                        end_code = code_range.replace('-', '')
                        start_num = int(code_start)
                        end_num = int(end_code)
                        
                        for code_num in range(start_num, end_num + 1):
                            code = f"{code_num:04d}"
                            self.codes[code] = {
                                'code': code,
                                'description': description,
                                'type': 'RANGE',
                                'original_line': line
                            }
                    else:
                        # Single code
                        self.codes[code_start] = {
                            'code': code_start,
                            'description': description,
                            'type': 'SINGLE',
                            'original_line': line
                        }
            
            print(f"✅ Loaded {len(self.codes)} SSR codes")
            
        except FileNotFoundError:
            print(f"❌ SSR codes file not found: {file_path}")
        except Exception as e:
            print(f"❌ Error loading SSR codes: {e}")
    
    def categorize_codes(self):
        """Categorize SSR codes by type and priority"""
        for code, data in self.codes.items():
            description = data['description'].upper()
            
            # Emergency codes (highest priority)
            if any(keyword in description for keyword in [
                'EMERGENCY', 'HI-JACKING', 'RADIO FAILURE', 'MAYDAY', 'PAN-PAN'
            ]):
                self.categories['EMERGENCY'].append(code)
                self.alert_codes.add(code)
            
            # Search and Rescue
            elif any(keyword in description for keyword in [
                'SAR', 'SEARCH AND RESCUE', 'AIR AMBULANCE', 'HELICOPTER EMERGENCY MEDIVAC',
                'HEMS', 'MEDIVAC'
            ]):
                self.categories['SAR'].append(code)
                self.alert_codes.add(code)
            
            # Medical/Air Ambulance
            elif any(keyword in description for keyword in [
                'AMBULANCE', 'MEDIVAC', 'MEDICAL', 'HEMS'
            ]):
                self.categories['MEDICAL'].append(code)
                self.alert_codes.add(code)
            
            # Police operations
            elif any(keyword in description for keyword in [
                'POLICE', 'ASU', 'AIR SUPPORT'
            ]):
                self.categories['POLICE'].append(code)
                self.alert_codes.add(code)
            
            # NATO and Military operations
            elif any(keyword in description for keyword in [
                'NATO', 'CAOC', 'EXERCISES', 'AEW AIRCRAFT', 'QUICK REACTION'
            ]):
                self.categories['NATO'].append(code)
                self.alert_codes.add(code)
            
            # Military operations
            elif any(keyword in description for keyword in [
                'RAF', 'RNAS', 'MILITARY', 'MOD', 'SPECIAL TASKS', 'ROYAL FLIGHTS'
            ]):
                self.categories['MILITARY'].append(code)
                if 'SPECIAL TASKS' in description or 'ROYAL FLIGHTS' in description:
                    self.alert_codes.add(code)
            
            # Special operations
            elif any(keyword in description for keyword in [
                'SPECIAL', 'PARADROPPING', 'ANTENNA TRAILING', 'TARGET TOWING',
                'HIGH-ENERGY MANOEUVRES', 'RED ARROWS', 'AEROBATICS', 'DISPLAY'
            ]):
                self.categories['SPECIAL_OPS'].append(code)
                self.alert_codes.add(code)
            
            # Conspicuity codes
            elif 'CONSPICUITY' in description:
                self.categories['CONSPICUITY'].append(code)
            
            # Transit codes
            elif 'TRANSIT' in description or 'ORCAM' in description:
                self.categories['TRANSIT'].append(code)
            
            # Approach codes
            elif 'APPROACH' in description:
                self.categories['APPROACH'].append(code)
            
            # Monitoring codes
            elif 'MONITORING' in description:
                self.categories['MONITORING'].append(code)
            
            # Unreliable data
            elif 'UNRELIABLE' in description:
                self.categories['UNRELIABLE'].append(code)
        
        # Print categorization summary
        print("📊 SSR Code Categories:")
        for category, codes in self.categories.items():
            if codes:
                print(f"   {category}: {len(codes)} codes")
        print(f"🚨 Alert-worthy codes: {len(self.alert_codes)}")
    
    def get_code_info(self, squawk_code: str) -> Optional[Dict]:
        """Get information about a specific SSR code"""
        if not squawk_code:
            return None
        
        # Normalize code (remove spaces, ensure 4 digits)
        code = squawk_code.replace(' ', '').zfill(4)
        
        if code in self.codes:
            info = self.codes[code].copy()
            
            # Add category information
            info['categories'] = []
            for category, codes in self.categories.items():
                if code in codes:
                    info['categories'].append(category)
            
            # Add priority and alert status
            info['is_alert'] = code in self.alert_codes
            info['priority'] = self._get_priority(info['categories'])
            info['color'] = self._get_color(info['categories'])
            
            return info
        
        return None
    
    def _get_priority(self, categories: List[str]) -> str:
        """Determine priority level based on categories"""
        if 'EMERGENCY' in categories:
            return 'CRITICAL'
        elif any(cat in categories for cat in ['SAR', 'MEDICAL', 'POLICE', 'NATO']):
            return 'HIGH'
        elif any(cat in categories for cat in ['MILITARY', 'SPECIAL_OPS']):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_color(self, categories: List[str]) -> str:
        """Get display color based on categories"""
        if 'EMERGENCY' in categories:
            return '#ff0000'  # Red
        elif 'SAR' in categories or 'MEDICAL' in categories:
            return '#ff8800'  # Orange
        elif 'POLICE' in categories:
            return '#0088ff'  # Blue
        elif 'NATO' in categories or 'MILITARY' in categories:
            return '#ff00ff'  # Magenta
        elif 'SPECIAL_OPS' in categories:
            return '#ffff00'  # Yellow
        else:
            return '#00ff00'  # Green
    
    def check_for_alerts(self, aircraft_data: Dict) -> List[Dict]:
        """Check aircraft data for alert-worthy SSR codes"""
        alerts = []
        
        squawk = aircraft_data.get('squawk')
        if not squawk:
            return alerts
        
        code_info = self.get_code_info(squawk)
        if not code_info or not code_info.get('is_alert'):
            return alerts
        
        # Create alert
        alert = {
            'type': 'SSR_CODE_ALERT',
            'priority': code_info['priority'],
            'aircraft': {
                'hex': aircraft_data.get('hex'),
                'flight': aircraft_data.get('flight', 'Unknown'),
                'squawk': squawk,
                'lat': aircraft_data.get('lat'),
                'lon': aircraft_data.get('lon'),
                'altitude': aircraft_data.get('alt_baro')
            },
            'ssr_info': code_info,
            'message': self._generate_alert_message(code_info, aircraft_data),
            'timestamp': datetime.now().isoformat(),
            'color': code_info['color']
        }
        
        alerts.append(alert)
        return alerts
    
    def _generate_alert_message(self, code_info: Dict, aircraft_data: Dict) -> str:
        """Generate human-readable alert message"""
        flight = aircraft_data.get('flight', 'Unknown aircraft')
        squawk = code_info['code']
        description = code_info['description']
        
        if 'EMERGENCY' in code_info['categories']:
            if squawk == '7700':
                return f"🚨 EMERGENCY: {flight} squawking 7700 (General Emergency)"
            elif squawk == '7600':
                return f"📻 RADIO FAILURE: {flight} squawking 7600 (Communication Failure)"
            elif squawk == '7500':
                return f"🚨 HIJACK: {flight} squawking 7500 (Unlawful Interference)"
        
        elif 'SAR' in code_info['categories']:
            return f"🚁 SAR OPERATION: {flight} - {description}"
        
        elif 'MEDICAL' in code_info['categories']:
            return f"🏥 MEDICAL: {flight} - {description}"
        
        elif 'POLICE' in code_info['categories']:
            return f"👮 POLICE: {flight} - {description}"
        
        elif 'NATO' in code_info['categories']:
            return f"🛡️ NATO: {flight} - {description}"
        
        elif 'MILITARY' in code_info['categories']:
            if 'SPECIAL TASKS' in description:
                return f"⚡ SPECIAL MILITARY: {flight} - {description}"
            elif 'ROYAL FLIGHTS' in description:
                return f"👑 ROYAL FLIGHT: {flight} - {description}"
            else:
                return f"🎖️ MILITARY: {flight} - {description}"
        
        elif 'SPECIAL_OPS' in code_info['categories']:
            if 'RED ARROWS' in description:
                return f"🔴 RED ARROWS: {flight} - {description}"
            elif 'AEROBATICS' in description or 'DISPLAY' in description:
                return f"🎪 AEROBATIC DISPLAY: {flight} - {description}"
            else:
                return f"⭐ SPECIAL OPS: {flight} - {description}"
        
        return f"📡 SPECIAL CODE: {flight} squawking {squawk} - {description}"
    
    def get_statistics(self) -> Dict:
        """Get SSR code statistics"""
        return {
            'total_codes': len(self.codes),
            'alert_codes': len(self.alert_codes),
            'categories': {cat: len(codes) for cat, codes in self.categories.items() if codes},
            'emergency_codes': ['7700', '7600', '7500'],
            'last_updated': datetime.now().isoformat()
        }
    
    def export_codes_json(self, output_file: str = 'ssr_codes.json'):
        """Export SSR codes to JSON for frontend use"""
        export_data = {
            'codes': self.codes,
            'categories': self.categories,
            'alert_codes': list(self.alert_codes),
            'statistics': self.get_statistics(),
            'generated': datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📄 Exported SSR codes to {output_file}")

def main():
    """Test the SSR code parser"""
    parser = SSRCodeParser()
    
    # Test some codes
    test_codes = ['7700', '7600', '7500', '0023', '0020', '0032', '0100', '7001']
    
    print("\n🧪 Testing SSR codes:")
    for code in test_codes:
        info = parser.get_code_info(code)
        if info:
            print(f"   {code}: {info['description']} [{', '.join(info['categories'])}] - {info['priority']}")
        else:
            print(f"   {code}: Unknown code")
    
    # Export for frontend
    parser.export_codes_json()
    
    # Print statistics
    stats = parser.get_statistics()
    print(f"\n📊 Statistics: {stats}")

if __name__ == '__main__':
    main()

