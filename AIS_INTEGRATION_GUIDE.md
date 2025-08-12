# 🚢 AIS Maritime Tracking Integration

## Overview

The AIS (Automatic Identification System) Maritime Tracking Integration connects your airspace visualizer to live ship data from AISStream.io, creating a comprehensive air and sea traffic monitoring system. This integration provides real-time vessel tracking, maritime situational awareness, and combined aircraft-ship display capabilities.

## 🌟 Key Features

### **📡 Real-Time AIS Data Stream**
- **WebSocket connection** to AISStream.io for live ship data
- **Geographic filtering** for UK waters (50°N-60°N, 10°W-2°E)
- **Message type filtering** for relevant AIS data (positions, static data, voyage data)
- **Automatic reconnection** and connection management

### **🚢 Comprehensive Ship Information**
- **Vessel identification**: Name, callsign, MMSI, IMO numbers
- **Position and movement**: Lat/lon, speed, course, heading
- **Vessel specifications**: Type, dimensions, destination
- **Navigation status**: Under way, at anchor, moored, aground, etc.
- **Real-time updates** with position history

### **🎯 Flexible Display Modes**
- **Both**: Aircraft and ships together (default)
- **Aircraft Only**: Traditional aviation radar view
- **Ships Only**: Pure maritime radar display
- **Dynamic switching** between modes

### **🔍 Advanced Ship Filtering**
- **Vessel Type**: Cargo, Tanker, Passenger, Fishing, Military, SAR, etc.
- **Navigation Status**: Under way, anchored, restricted maneuverability, etc.
- **Real-time filtering** with instant radar updates

### **🎨 Professional Maritime Display**
- **Color-coded ships** by vessel type and status
- **Directional symbols** showing ship orientation
- **Speed vectors** for moving vessels
- **Ship labels** with names and speeds
- **Distance-based detail levels**

## 🚢 Ship Categories and Color Coding

### **Vessel Types**
- **🟢 Cargo Ships** (#00ff88): Container ships, bulk carriers, general cargo
- **🟠 Tankers** (#ff8800): Oil tankers, chemical tankers, gas carriers
- **🟡 Passenger Vessels** (#ffaa00): Ferries, cruise ships, passenger boats
- **🟢 Fishing Vessels** (#88ff00): Commercial fishing boats, trawlers
- **🟣 Military Vessels** (#ff00ff): Naval ships, coast guard vessels
- **🟡 Pilot Vessels** (#ffff00): Harbor pilots, pilot boats
- **🔴 Search & Rescue** (#ff0000): SAR vessels, emergency response
- **🔵 Tugs** (#00ffff): Tugboats, harbor assistance vessels
- **🔵 Default Ships** (#00aaff): Other vessel types

### **Navigation Status Colors**
- **⚪ At Anchor** (#888888): Vessels at anchor
- **🔴 Aground** (#ff4444): Vessels that have run aground
- **🟠 Not Under Command** (#ff8844): Vessels unable to maneuver
- **Default**: Moving vessels use vessel type colors

## 📊 AIS Data Processing

### **Message Types Processed**
- **Type 1, 2, 3**: Position reports with navigation status
- **Type 4**: Base station reports (shore stations)
- **Type 5**: Static and voyage-related data
- **Type 18, 19**: Standard Class B position reports
- **Type 21**: Aid-to-navigation reports
- **Type 24**: Static data reports (Class B)

### **Geographic Bounds**
```
North: 60.0°N  (Northern Scotland)
South: 50.0°N  (Southern England)
East:   2.0°E  (Eastern England)
West: -10.0°W  (Western Ireland)
```

### **Data Refresh**
- **Ship positions**: Updated every 10 seconds
- **Connection monitoring**: Continuous WebSocket connection
- **Stale data removal**: Vessels older than 10 minutes removed
- **Distance filtering**: Only ships within radar range displayed

## 🖥️ User Interface

### **Display Mode Controls**
Located in the Radar tab:
- **Both**: Show aircraft and ships together
- **Aircraft**: Show only aircraft (traditional ATC view)
- **Ships**: Show only ships (maritime radar view)
- **Instant switching** without data loss

### **Ships Tab Features**

#### **Connection Management**
- **🔗 Connect AIS**: Establish WebSocket connection to AISStream.io
- **🔌 Disconnect**: Close AIS connection and clear ship data
- **Status indicator**: Real-time connection status display

#### **AIS Statistics**
- **Total ships** in current radar range
- **Vessel type breakdown** with counts
- **Connection status** and data freshness

#### **Filtering Controls**
- **Ship Type Filter**: Filter by vessel category
- **Navigation Status Filter**: Filter by operational status
- **🔍 Apply Filters**: Update display with new filter settings

#### **Active Ships List**
- **Real-time ship list** with key information
- **Distance sorting** (closest ships first)
- **Vessel details**: Name, type, status, speed, course
- **Click to center** map on selected ship (planned feature)

## 🔧 Technical Implementation

### **AIS Stream Client (`ais_stream_client.py`)**

#### **WebSocket Connection**
```python
async def connect_websocket(self):
    uri = "wss://stream.aisstream.io/v0/stream"
    subscribe_message = {
        "APIKey": self.api_key,
        "BoundingBoxes": [[
            [self.bounds['north'], self.bounds['west']],
            [self.bounds['south'], self.bounds['east']]
        ]],
        "FilterMessageTypes": self.message_types
    }
```

#### **Data Processing**
- **Message parsing**: Extract vessel information from AIS messages
- **Geographic filtering**: Only process ships within UK waters
- **Data enhancement**: Add calculated fields (distance, bearing)
- **Vessel tracking**: Maintain persistent vessel records by MMSI

#### **Vessel Information Structure**
```python
vessel = {
    'mmsi': mmsi,
    'lat': lat, 'lon': lon,
    'speed': speed_over_ground,
    'course': course_over_ground,
    'heading': true_heading,
    'nav_status': navigation_status_text,
    'vessel_type': ship_and_cargo_type_text,
    'name': vessel_name,
    'callsign': call_sign,
    'destination': destination,
    'length': bow_to_stern,
    'width': port_to_starboard
}
```

### **Frontend Integration**

#### **Ship Display Functions**
```javascript
function drawShips(centerX, centerY, maxRadius) {
    ships.forEach(ship => {
        // Calculate position on radar
        const distance = calculateDistance(radarCenterLat, radarCenterLon, ship.lat, ship.lon);
        const bearing = calculateBearing(radarCenterLat, radarCenterLon, ship.lat, ship.lon);
        
        // Draw ship symbol and label
        drawShipSymbol(x, y, ship);
        drawShipLabel(x, y, ship);
    });
}
```

#### **Ship Symbol Rendering**
- **Triangle symbols** pointing in direction of travel
- **Size scaling** based on zoom level
- **Color coding** by vessel type and status
- **Speed vectors** for moving vessels

## 📡 API Endpoints

### **Get Vessels in Range**
```http
GET /api/ais/vessels?lat=55.5094&lon=-4.5967&range=100

Response:
{
  "status": "success",
  "data": {
    "vessels": [...],
    "count": 25,
    "center": {"lat": 55.5094, "lon": -4.5967},
    "range_nm": 100,
    "timestamp": "2025-08-12T02:15:00.000Z"
  }
}
```

### **AIS Connection Status**
```http
GET /api/ais/status

Response:
{
  "status": "success",
  "data": {
    "connected": true,
    "total_vessels": 150,
    "active_vessels": 25,
    "bounds": {...},
    "api_key_set": true,
    "last_update": "2025-08-12T02:15:00.000Z"
  }
}
```

### **Connect to AIS Stream**
```http
POST /api/ais/connect

Response:
{
  "status": "success",
  "message": "AIS connection started"
}
```

### **Disconnect from AIS Stream**
```http
POST /api/ais/disconnect

Response:
{
  "status": "success", 
  "message": "AIS connection stopped"
}
```

## 🎯 Use Cases

### **Maritime Traffic Control**
- **Port approach monitoring** with combined air/sea traffic
- **Harbor traffic management** with vessel identification
- **Search and rescue coordination** with both aircraft and ships
- **Maritime security** with military and patrol vessel tracking

### **Aviation-Maritime Coordination**
- **Helicopter offshore operations** with ship landing platforms
- **Search and rescue missions** coordinating aircraft and vessels
- **Maritime patrol aircraft** with surface vessel correlation
- **Coast guard operations** with integrated air/sea picture

### **Training and Education**
- **Multi-domain awareness** training for controllers
- **Maritime traffic patterns** understanding
- **Vessel type identification** and characteristics
- **Navigation status interpretation** for maritime operations

### **Research and Analysis**
- **Traffic density studies** for air and sea routes
- **Vessel movement patterns** in relation to air traffic
- **Port efficiency analysis** with approach patterns
- **Environmental monitoring** with research vessel tracking

## 🚀 Quick Start Guide

### **1. Enable AIS Tracking**
1. Open the Airspace Visualizer
2. Click the **SHIPS** tab in the control panel
3. Click **🔗 Connect AIS** to start receiving ship data
4. Wait for connection confirmation

### **2. Configure Display Mode**
1. Go to the **RADAR** tab
2. Select your preferred display mode:
   - **Both**: See aircraft and ships together
   - **Aircraft**: Traditional aviation radar
   - **Ships**: Maritime radar only

### **3. Filter Ship Display**
1. In the **SHIPS** tab, choose filters:
   - **Ship Type**: Focus on specific vessel types
   - **Navigation Status**: Show only moving/anchored vessels
2. Click **🔍 Apply Filters** to update display

### **4. Monitor Maritime Traffic**
- Ships appear as colored triangles on the radar
- Colors indicate vessel type and status
- Speed vectors show direction and velocity
- Ship list shows detailed information

## 🔍 Example Scenarios

### **Port Approach Monitoring**
```
Display Mode: Both
Ship Filter: All vessel types
Range: 25nm around major port
Result: Combined view of arriving aircraft and ships
```

### **Search and Rescue Operation**
```
Display Mode: Both
Ship Filter: Search & Rescue vessels
Aircraft: Emergency squawk codes (7700)
Result: Coordinated SAR assets visualization
```

### **Maritime Security Patrol**
```
Display Mode: Both
Ship Filter: Military vessels
Aircraft Filter: Military/Police operations
Result: Security patrol coordination display
```

### **Offshore Operations**
```
Display Mode: Both
Ship Filter: Offshore supply vessels, platforms
Range: 100nm offshore
Result: Helicopter and supply vessel coordination
```

## 📈 Benefits

### **Enhanced Situational Awareness**
- **Complete operational picture** with air and sea traffic
- **Multi-domain coordination** for complex operations
- **Real-time updates** for dynamic situations
- **Professional display quality** for operational use

### **Operational Efficiency**
- **Single display system** for multiple traffic types
- **Flexible filtering** for mission-specific views
- **Real-time data integration** without manual correlation
- **Scalable from harbor to oceanic ranges**

### **Safety Improvements**
- **Collision avoidance** with combined traffic awareness
- **Search and rescue coordination** with all available assets
- **Emergency response** with comprehensive asset visibility
- **Training enhancement** with realistic multi-domain scenarios

### **Cost Effectiveness**
- **Single system** for multiple operational domains
- **Real-time data** without expensive proprietary systems
- **Open integration** with existing aviation infrastructure
- **Scalable deployment** from small ports to major facilities

## ⚙️ Configuration

### **API Key Setup**
Your AISStream.io API key is pre-configured:
```
API Key: 0f980557569314a04bba4d7b69d26c83b243200b
```

### **Geographic Bounds**
UK waters coverage (can be modified in `ais_stream_client.py`):
```python
self.bounds = {
    'north': 60.0,   # Northern Scotland
    'south': 50.0,   # Southern England  
    'east': 2.0,     # Eastern England
    'west': -10.0    # Western Ireland
}
```

### **Update Intervals**
- **Ship data**: 10 seconds (slower than aircraft due to ship movement patterns)
- **Connection monitoring**: Continuous
- **UI updates**: Real-time with data reception

## 🔧 Troubleshooting

### **No Ships Appearing**
1. Check AIS connection status in Ships tab
2. Verify internet connectivity for WebSocket
3. Ensure radar range includes shipping lanes
4. Check ship filters aren't too restrictive

### **Connection Issues**
1. Click **🔌 Disconnect** then **🔗 Connect AIS**
2. Check browser console for WebSocket errors
3. Verify API key is valid and has remaining quota
4. Check firewall settings for WebSocket connections

### **Performance Issues**
1. Reduce radar range to decrease ship count
2. Use ship filters to limit displayed vessels
3. Switch to "Aircraft Only" mode if needed
4. Check browser performance with large datasets

---

**The AIS Maritime Integration transforms your airspace visualizer into a comprehensive air-sea traffic monitoring system, providing professional-grade situational awareness for modern multi-domain operations.** 🚢✈️📡🌊

