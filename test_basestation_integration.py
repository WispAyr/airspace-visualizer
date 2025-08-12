#!/usr/bin/env python3
"""
Test script for BaseStation database integration
"""

import requests
import json
import time

def test_basestation_endpoints():
    """Test the new BaseStation database endpoints"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing BaseStation Database Integration...")
    print("=" * 50)
    
    # Test 1: Get BaseStation database statistics
    print("\n1️⃣ Testing BaseStation Stats...")
    try:
        response = requests.get(f"{base_url}/api/basestation/stats")
        if response.status_code == 200:
            data = response.json()
            stats = data.get('data', {})
            print(f"✅ Stats retrieved successfully!")
            print(f"   Total Aircraft: {stats.get('total_aircraft', 0):,}")
            print(f"   With Registration: {stats.get('with_registration', 0):,}")
            print(f"   With Type Code: {stats.get('with_type_code', 0):,}")
            
            # Show top manufacturers
            if 'top_manufacturers' in stats:
                print(f"   Top Manufacturers:")
                for i, mfg in enumerate(stats['top_manufacturers'][:5]):
                    print(f"     {i+1}. {mfg['Manufacturer']}: {mfg['count']}")
        else:
            print(f"❌ Stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")
    
    # Test 2: Look up a specific aircraft by ModeS
    print("\n2️⃣ Testing Aircraft Lookup...")
    try:
        # Test with a known ModeS code from our database
        test_mode_s = "408092"  # G-ZBLH from our sample
        response = requests.get(f"{base_url}/api/aircraft/lookup/{test_mode_s}")
        if response.status_code == 200:
            data = response.json()
            aircraft = data.get('data', {})
            print(f"✅ Aircraft lookup successful!")
            print(f"   ModeS: {aircraft.get('mode_s')}")
            print(f"   Registration: {aircraft.get('registration')}")
            print(f"   Type: {aircraft.get('type')}")
            print(f"   Manufacturer: {aircraft.get('manufacturer')}")
        elif response.status_code == 404:
            print(f"⚠️  Aircraft {test_mode_s} not found in database")
        else:
            print(f"❌ Lookup failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Lookup error: {e}")
    
    # Test 3: Search by registration
    print("\n3️⃣ Testing Registration Search...")
    try:
        response = requests.get(f"{base_url}/api/aircraft/search/registration/G-")
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {})
            print(f"✅ Registration search successful!")
            print(f"   Search term: {results.get('search_term')}")
            print(f"   Results found: {results.get('count')}")
            
            # Show first few results
            for i, aircraft in enumerate(results.get('results', [])[:3]):
                print(f"   {i+1}. {aircraft.get('registration')} - {aircraft.get('type')}")
        else:
            print(f"❌ Registration search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Registration search error: {e}")
    
    # Test 4: Search by aircraft type
    print("\n4️⃣ Testing Type Search...")
    try:
        response = requests.get(f"{base_url}/api/aircraft/search/type/B738")
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {})
            print(f"✅ Type search successful!")
            print(f"   Search term: {results.get('search_term')}")
            print(f"   Results found: {results.get('count')}")
            
            # Show first few results
            for i, aircraft in enumerate(results.get('results', [])[:3]):
                print(f"   {i+1}. {aircraft.get('registration')} - {aircraft.get('type')}")
        else:
            print(f"❌ Type search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Type search error: {e}")
    
    # Test 5: Enhanced aircraft data from proxy
    print("\n5️⃣ Testing Enhanced Aircraft Data...")
    try:
        response = requests.get(f"{base_url}/tmp/aircraft.json")
        if response.status_code == 200:
            data = response.json()
            aircraft_list = data.get('aircraft', [])
            print(f"✅ Enhanced aircraft data retrieved!")
            print(f"   Aircraft count: {len(aircraft_list)}")
            
            # Check for enhanced aircraft
            enhanced_count = sum(1 for ac in aircraft_list if ac.get('enhanced'))
            print(f"   Enhanced aircraft: {enhanced_count}")
            
            # Show details of first enhanced aircraft
            for aircraft in aircraft_list:
                if aircraft.get('enhanced'):
                    print(f"   Enhanced aircraft example:")
                    print(f"     Hex: {aircraft.get('hex')}")
                    print(f"     Registration: {aircraft.get('registration')}")
                    print(f"     Type: {aircraft.get('aircraft_type')}")
                    print(f"     Manufacturer: {aircraft.get('manufacturer')}")
                    break
        else:
            print(f"❌ Enhanced aircraft data failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Enhanced aircraft data error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ BaseStation integration test completed!")

if __name__ == "__main__":
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    test_basestation_endpoints()
