# 📡 SSR Code Integration System

## Overview

The SSR (Secondary Surveillance Radar) Code Integration System provides comprehensive aircraft context, automated alerts, and enhanced radar display based on transponder squawk codes. This system transforms raw SSR codes into meaningful operational intelligence for air traffic monitoring.

## 🌟 Key Features

### **📊 Comprehensive SSR Database**
- **4,245 SSR codes** from the official UK database
- **297 alert-worthy codes** for special operations
- **12 categories** including Emergency, SAR, Military, Police, NATO, etc.
- **Real-time lookups** and context information

### **🚨 Automated Alert System**
- **Critical alerts** for emergency codes (7700, 7600, 7500)
- **High-priority alerts** for SAR, Medical, Police operations
- **NATO/Military alerts** for special operations and QRA flights
- **Real-time notifications** in the communications log

### **🎨 Enhanced Visual Display**
- **Color-coded aircraft** based on SSR code priority
- **Priority-based rendering** (SSR alerts override altitude colors)
- **Enhanced contact list** with SSR descriptions
- **Alert indicators** for special operations

### **🔍 Interactive SSR Analysis**
- **Code lookup tool** with detailed information
- **Category browsing** for different operation types
- **Statistics dashboard** with code distribution
- **Live alert monitoring** for active aircraft

## 📋 SSR Code Categories

### **🚨 EMERGENCY (4 codes)**
- **7700**: General Emergency
- **7600**: Radio Failure
- **7500**: Unlawful Interference (Hijacking)
- **0020**: Air Ambulance Helicopter Emergency Medivac

### **🚁 SEARCH & RESCUE (5 codes)**
- **0023**: Aircraft engaged in actual SAR Operations
- **0020**: Air Ambulance Helicopter Emergency Medivac
- Various regional air ambulance codes (0014-0017)

### **🏥 MEDICAL (Multiple codes)**
- Air ambulance services
- Helicopter Emergency Medical Services (HEMS)
- Regional medical transport operations

### **👮 POLICE (19 codes)**
- **0032**: Aircraft engaged in police air support operations
- Regional Police Air Support Units (ASU)
- Metropolitan, Greater Manchester, Essex, Surrey Police, etc.

### **🛡️ NATO (123 codes)**
- **0100, 0200, 0300, etc.**: NATO CAOC 9 Exercises
- **3000-4000 series**: Aircraft receiving service from AEW aircraft
- **6000-6700 series**: NATO CAOC 9 Exercises

### **🎖️ MILITARY (466 codes)**
- RAF and RNAS operations
- Special tasks and royal flights
- Military radar services
- Training and operational flights

### **⭐ SPECIAL OPERATIONS (139 codes)**
- **7003**: Red Arrows Transit/Display
- **7004**: Conspicuity Aerobatics and Display
- **7005**: High-Energy Manoeuvres
- **0026**: Special Tasks (Mil) - activated under SFN
- **0033**: Aircraft Paradropping
- **0034**: Antenna trailing/target towing

## 🎯 Alert System

### **Priority Levels**

#### **CRITICAL Priority**
- **Emergency codes** (7700, 7600, 7500)
- **Air ambulance emergencies**
- **Immediate response required**
- **Color**: Red (#ff0000)

#### **HIGH Priority**
- **SAR operations** (0023)
- **Medical flights** (air ambulance)
- **Police operations** (0032)
- **NATO exercises** when active
- **Color**: Orange (#ff8800)

#### **MEDIUM Priority**
- **Military operations**
- **Special tasks**
- **Royal flights**
- **Color**: Yellow (#ffaa00)

#### **LOW Priority**
- **Normal operations**
- **Conspicuity codes**
- **Transit codes**
- **Color**: Default theme color

### **Alert Messages**

The system generates contextual alert messages:

- **🚨 EMERGENCY: EZY123 squawking 7700 (General Emergency)**
- **🚁 SAR OPERATION: RESCUE01 - Aircraft engaged in actual SAR Operations**
- **👮 POLICE: NPAS25 - Aircraft engaged in police air support operations**
- **🛡️ NATO: NATO01 - NATO CAOC 9 Exercises (activated by NOTAM)**
- **👑 ROYAL FLIGHT: KITTYHAWK - Royal Flights - Helicopters**
- **🔴 RED ARROWS: RED1 - Red Arrows Transit/Display**

## 🖥️ User Interface

### **SSR Tab Features**

#### **Code Lookup Tool**
- Enter any 4-digit SSR code
- Instant lookup with detailed information
- Description, categories, priority, and alert status
- Color-coded display matching radar presentation

#### **Category Browser**
- Browse codes by operational category
- Filter by Emergency, SAR, Medical, Police, NATO, Military, etc.
- Shows code count and examples for each category
- Quick access to relevant operational codes

#### **Statistics Dashboard**
- Total codes in database: **4,245**
- Alert-worthy codes: **297**
- Category breakdown with counts
- Real-time statistics updates

#### **Live Alert Monitor**
- Shows currently active SSR alerts
- Aircraft with special operation codes
- Priority-based sorting and coloring
- Click to center map on alert aircraft

### **Enhanced Radar Display**

#### **Color-Coded Aircraft**
- **Red**: Emergency operations (7700, 7600, 7500)
- **Orange**: SAR and medical operations
- **Blue**: Police operations
- **Magenta**: NATO and military operations
- **Yellow**: Special operations and displays
- **Green**: Normal operations (altitude-based)

#### **Contact List Enhancements**
- SSR codes color-matched to radar display
- Alert descriptions for special operations
- Priority indicators for high-importance flights
- Integrated with airspace information

## 📡 API Endpoints

### **Get SSR Code Information**
```http
GET /api/ssr-codes?code=7700

Response:
{
  "status": "success",
  "data": {
    "code_info": {
      "code": "7700",
      "description": "Special Purpose Code - Emergency",
      "categories": ["EMERGENCY"],
      "priority": "CRITICAL",
      "color": "#ff0000",
      "is_alert": true
    }
  }
}
```

### **Browse SSR Category**
```http
GET /api/ssr-codes?category=EMERGENCY

Response:
{
  "status": "success",
  "data": {
    "category": "EMERGENCY",
    "codes": { ... },
    "count": 4,
    "statistics": { ... }
  }
}
```

### **Get SSR Statistics**
```http
GET /api/ssr-codes

Response:
{
  "status": "success",
  "data": {
    "statistics": {
      "total_codes": 4245,
      "alert_codes": 297,
      "categories": { ... }
    },
    "emergency_codes": ["7700", "7600", "7500"]
  }
}
```

## 🛠️ Technical Implementation

### **SSR Code Parser (`ssr_code_parser.py`)**

#### **Features**
- Parses official UK SSR codes database
- Categorizes codes by operational type
- Identifies alert-worthy codes
- Provides color coding and priority levels
- Generates contextual alert messages

#### **Key Functions**
- `get_code_info(squawk_code)`: Get detailed information about an SSR code
- `check_for_alerts(aircraft_data)`: Check if aircraft requires alerts
- `get_statistics()`: Get database statistics
- `export_codes_json()`: Export codes for frontend use

### **Aircraft Data Enhancement**

#### **Server-Side Processing**
```python
# Add SSR information to aircraft data
ssr_info = ssr_parser.get_code_info(aircraft['squawk'])
if ssr_info:
    aircraft['ssr'] = {
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
        # Process alerts...
```

#### **Frontend Integration**
```javascript
// Color aircraft based on SSR code priority
if (aircraft.ssr && aircraft.ssr.is_alert && aircraft.ssr.color) {
    color = aircraft.ssr.color;
}

// Display SSR information in contact list
${ac.ssr && ac.ssr.is_alert ? `
    <div style="color: ${ac.ssr.color}; font-weight: bold;">
        ⚠️ ${ac.ssr.description}
    </div>
` : ''}
```

## 🎯 Use Cases

### **Emergency Response**
- **Immediate identification** of emergency aircraft (7700, 7600, 7500)
- **Visual and audible alerts** for critical situations
- **Automatic prioritization** in contact lists and displays
- **Context information** for appropriate response

### **Search and Rescue Coordination**
- **SAR aircraft identification** with code 0023
- **Air ambulance tracking** with regional codes
- **Medical emergency support** with HEMS identification
- **Coordination support** for rescue operations

### **Security and Law Enforcement**
- **Police aircraft identification** across all UK regions
- **Special operation awareness** for security activities
- **NATO exercise monitoring** when exercises are active
- **Military operation context** for airspace coordination

### **Aviation Training and Education**
- **SSR code education** with comprehensive database
- **Operational context learning** for air traffic controllers
- **Emergency procedure training** with real-world examples
- **Military/civilian coordination** understanding

### **Air Traffic Management**
- **Enhanced situational awareness** with operational context
- **Priority handling** for special operation aircraft
- **Airspace coordination** with military and civilian operations
- **Conflict resolution** with operational priority information

## 🚀 Quick Start Guide

### **1. Access SSR Features**
1. Open Airspace Visualizer
2. Click the **SSR** tab in the control panel
3. View live SSR statistics and alerts

### **2. Lookup SSR Codes**
1. Enter any 4-digit code in the lookup field
2. Press Enter or click 🔍
3. View detailed information and context

### **3. Browse by Category**
1. Select category from dropdown (Emergency, SAR, Police, etc.)
2. Click "Browse Category"
3. View all codes in that operational category

### **4. Monitor Live Alerts**
1. Active SSR alerts appear automatically
2. Aircraft with special codes are highlighted
3. Click alerts to center map on aircraft

### **5. Enhanced Radar Display**
- Aircraft automatically color-coded by SSR priority
- Emergency aircraft appear in red
- SAR/Medical aircraft in orange
- Police aircraft in blue
- Military/NATO in magenta

## 🔍 Example Scenarios

### **Emergency Declaration**
```
Aircraft: BAW123
SSR Code: 7700
Alert: 🚨 EMERGENCY: BAW123 squawking 7700 (General Emergency)
Display: Red aircraft symbol, priority in contact list
Action: Immediate attention, emergency response coordination
```

### **Search and Rescue Operation**
```
Aircraft: RESCUE01
SSR Code: 0023
Alert: 🚁 SAR OPERATION: RESCUE01 - Aircraft engaged in actual SAR Operations
Display: Orange aircraft symbol, SAR category identification
Action: Monitor for coordination, provide airspace priority
```

### **Police Operation**
```
Aircraft: NPAS25
SSR Code: 0032
Alert: 👮 POLICE: NPAS25 - Aircraft engaged in police air support operations
Display: Blue aircraft symbol, police category identification
Action: Airspace awareness, coordination with ATC
```

### **NATO Exercise**
```
Aircraft: NATO01
SSR Code: 0100
Alert: 🛡️ NATO: NATO01 - NATO CAOC 9 Exercises (activated by NOTAM)
Display: Magenta aircraft symbol, NATO category identification
Action: Exercise awareness, military coordination
```

## 📈 Benefits

### **Enhanced Situational Awareness**
- **Immediate operational context** for all aircraft
- **Priority-based visual display** for quick identification
- **Automated alert generation** for special operations
- **Comprehensive database** of operational codes

### **Improved Safety**
- **Emergency aircraft prioritization** with critical alerts
- **SAR operation visibility** for rescue coordination
- **Police operation awareness** for security activities
- **Military exercise context** for safe separation

### **Operational Efficiency**
- **Automated categorization** of aircraft operations
- **Real-time alert processing** without manual intervention
- **Integrated display system** with existing radar data
- **Comprehensive API** for system integration

### **Training and Education**
- **Complete SSR code database** for learning
- **Operational context examples** for training
- **Real-world application** of SSR code knowledge
- **Interactive exploration** of code categories

---

**The SSR Code Integration System transforms raw transponder codes into actionable intelligence, providing comprehensive operational context for professional air traffic monitoring and emergency response coordination.** 📡✈️🚨

