from flask_cors import CORS
import os
import json
import time
import faiss
import numpy as np
import threading
from flask import Flask, request, jsonify
from ollama import embeddings, chat

ADS_B_FILE = "/tmp/aircraft.json"  # Fallback file
ADS_B_API_URL = "http://localhost:8080/tmp/aircraft.json"  # Enhanced endpoint
VDL2_FILE = "/tmp/vdl2.json"
NOTAM_API_URL = "http://localhost:8080/api/notams"
INDEX_FILE = "radar_index.faiss"
META_FILE = "radar_metadata.json"
EMBED_DIM = 768

app = Flask(__name__)
CORS(app)

# Use Inner Product index for cosine similarity
index = faiss.IndexFlatIP(EMBED_DIM)
metadata = []

def get_embedding(text):
    """Get normalized embedding for cosine similarity"""
    emb = embeddings(model="nomic-embed-text", prompt=text)["embedding"]
    # Convert to numpy array and normalize for cosine similarity
    emb = np.array(emb, dtype="float32")
    emb = emb.reshape(1, -1)
    faiss.normalize_L2(emb)
    return emb.flatten()

def extract_semantic_messages():
    summaries = []

    # ADS-B with airspace information (enhanced with BaseStation data)
    try:
        import requests
        # Try to get enhanced data from API first
        try:
            response = requests.get(ADS_B_API_URL, timeout=5)
            if response.status_code == 200:
                adsb = response.json().get("aircraft", [])
                print(f"📡 Fetched {len(adsb)} aircraft from enhanced API")
            else:
                # Fallback to local file
                with open(ADS_B_FILE) as f:
                    adsb = json.load(f).get("aircraft", [])
                print(f"📁 Using fallback file with {len(adsb)} aircraft")
        except Exception as api_error:
            print(f"⚠️ API fetch failed: {api_error}, using fallback file")
            with open(ADS_B_FILE) as f:
                adsb = json.load(f).get("aircraft", [])
        
        for a in adsb:
                flight = a.get("flight", "unknown").strip()
                hexcode = a.get("hex", "")
                alt = a.get("alt_baro", "unknown")
                speed = a.get("gs", "unknown")
                lat = a.get("lat", "?")
                lon = a.get("lon", "?")
                
                # Include airspace information if available
                airspace_info = ""
                if a.get("airspace"):
                    airspace = a["airspace"]
                    airspace_info = f", in {airspace['name']} ({airspace['type']}) - {airspace['description']}"
                
                # Add flight status analysis
                status_info = ""
                try:
                    # Analyze flight status using the same logic as frontend
                    altitude = a.get('alt_baro', 0)
                    speed_gs = a.get('gs', 0)
                    vertical_rate = a.get('baro_rate', 0)
                    squawk = a.get('squawk', '0000')
                    airspace_data = a.get('airspace')
                    
                    # Determine flight phase and intentions
                    phase = analyze_flight_phase(altitude, speed_gs, vertical_rate, airspace_data)
                    atc_center = analyze_atc_from_squawk(str(squawk))
                    intention = analyze_aircraft_intention(a, phase, airspace_data)
                    
                    status_info = f", Status: {phase}, ATC: {atc_center}, Intention: {intention}"
                except Exception as e:
                    print(f"Error analyzing flight status for {hexcode}: {e}")
                
                # Add BaseStation enhanced information if available
                basestation_info = ""
                if a.get("enhanced"):
                    registration = a.get("registration", "")
                    aircraft_type = a.get("aircraft_type", "")
                    icao_type = a.get("icao_type", "")
                    manufacturer = a.get("manufacturer", "")
                    operator = a.get("operator", "")
                    owner = a.get("owner", "")
                    
                    if registration and registration != "``":
                        basestation_info += f", Registration: {registration}"
                    if aircraft_type and aircraft_type != "``":
                        basestation_info += f", Type: {aircraft_type}"
                    elif icao_type:
                        basestation_info += f", ICAO Type: {icao_type}"
                    if manufacturer and manufacturer != "``":
                        basestation_info += f", Manufacturer: {manufacturer}"
                    if operator and operator != "``":
                        basestation_info += f", Operator: {operator}"
                    if owner and owner != "``":
                        basestation_info += f", Owner: {owner}"
                
                summaries.append(f"ADS-B: {flight} ({hexcode}) at {alt} ft, speed {speed} knots, position {lat}, {lon}{airspace_info}{status_info}{basestation_info}")
    except Exception as e:
        print(f"[ADS-B load error] {e}")

    # VDL2/ACARS
    try:
        with open(VDL2_FILE) as f:
            raw = f.read().strip()

        if not raw:
            raise ValueError("Empty VDL2 file")

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                vdl2_data = [parsed]  # wrap single object as list
            elif isinstance(parsed, list):
                vdl2_data = parsed
            else:
                raise ValueError("Unrecognized VDL2 format")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error: {e}")

        for entry in vdl2_data:
            v = entry.get("vdl2", entry)  # support wrapper key or flat
            acars = v.get("acars", {})
            flight = acars.get("flight", "unknown").strip()
            msg_text = acars.get("msg_text", "no message")
            summaries.append(f"ACARS message from flight {flight}: {msg_text}")
    except Exception as e:
        print(f"[VDL2 parse error] {e}")

    # NOTAM data
    try:
        import requests
        response = requests.get(NOTAM_API_URL, timeout=5)
        if response.status_code == 200:
            notam_data = response.json()
            if notam_data.get("status") == "success" and notam_data.get("data", {}).get("notams"):
                notams = notam_data["data"]["notams"]
                for notam in notams[:10]:  # Limit to top 10 NOTAMs for AI processing
                    notam_id = notam.get("id", "Unknown")
                    priority = notam.get("priority", "NORMAL")
                    description = notam.get("description", "No description")
                    location = notam.get("location", "Unknown location")
                    distance = notam.get("distance_nm", "Unknown distance")
                    
                    # Truncate description if too long
                    if len(description) > 200:
                        description = description[:200] + "..."
                    
                    summaries.append(f"NOTAM {notam_id} ({priority} priority): {description} at {location} ({distance}nm from center)")
    except Exception as e:
        print(f"[NOTAM fetch error] {e}")

    # METAR data for key airports
    try:
        import requests
        key_airports = ["EGPK", "EGLL", "EGCC", "EGBB", "EGPH"]  # Prestwick, Heathrow, Manchester, Birmingham, Edinburgh
        for icao in key_airports:
            try:
                metar_response = requests.get(f"http://localhost:8080/api/metar/{icao}", timeout=5)
                if metar_response.status_code == 200:
                    metar_data = metar_response.json()
                    if metar_data.get("status") == "success" and metar_data.get("data"):
                        data = metar_data["data"]
                        temperature = data.get("temperature", "Unknown")
                        wind_data = data.get("wind", {})
                        wind_speed = wind_data.get("speed", "Unknown") if wind_data else "Unknown"
                        wind_direction = wind_data.get("direction", "Unknown") if wind_data else "Unknown"
                        visibility = data.get("visibility", "Unknown")
                        clouds = data.get("clouds", {})
                        ceiling = clouds.get("height", "Unknown") if clouds else "Unknown"
                        conditions = data.get("weather", "Clear") if data.get("weather") else "Clear"
                        
                        # Format wind information properly
                        wind_info = f"{wind_direction}° at {wind_speed}kt" if wind_direction != "Unknown" and wind_speed != "Unknown" else "Unknown"
                        
                        summaries.append(f"METAR {icao}: Temp {temperature}°C, Wind {wind_info}, Visibility {visibility}m, Ceiling {ceiling}ft, Conditions {conditions}")
            except Exception as e:
                print(f"[METAR fetch error for {icao}]: {e}")
                continue
    except Exception as e:
        print(f"[METAR fetch error] {e}")

    return summaries

def rebuild_index():
    global index, metadata
    print("\n🔄 Rebuilding semantic index...")
    summaries = extract_semantic_messages()

    if not summaries:
        print("⚠️ No messages to index")
        return

    # Reset index and metadata
    index = faiss.IndexFlatIP(EMBED_DIM)
    metadata = []
    embeddings_list = []

    # Generate embeddings for all summaries
    for msg in summaries:
        try:
            emb = get_embedding(msg)
            embeddings_list.append(emb)
        except Exception as e:
            print(f"[Embedding error for '{msg[:50]}...']: {e}")
            continue

    if embeddings_list:
        # Create embedding matrix and normalize for cosine similarity
        emb_matrix = np.array(embeddings_list).astype("float32")
        faiss.normalize_L2(emb_matrix)
        
        # Add to index
        index.add(emb_matrix)
        metadata.extend(summaries[:len(embeddings_list)])

        # Save index and metadata
        try:
            faiss.write_index(index, INDEX_FILE)
            with open(META_FILE, "w") as f:
                json.dump(metadata, f)
        except Exception as e:
            print(f"[Index save error]: {e}")

    print(f"✅ Indexed {len(metadata)} messages")

def validate_aircraft_data(aircraft_data):
    """Validate aircraft data for consistency"""
    if not aircraft_data:
        return aircraft_data
    
    validated_data = []
    for aircraft in aircraft_data:
        # Check for contradictory information
        speed = aircraft.get('speed', 0)
        altitude = aircraft.get('altitude', 0)
        status = aircraft.get('status', '').lower()
        
        # Validate status consistency
        if speed > 10 and 'parked' in status:
            # Aircraft with speed cannot be parked
            aircraft['status'] = 'CRUISE' if altitude > 1000 else 'TAXI'
        elif speed < 5 and altitude < 100 and 'cruise' in status:
            # Aircraft on ground cannot be cruising
            aircraft['status'] = 'PARKED' if speed == 0 else 'TAXI'
        
        validated_data.append(aircraft)
    
    return validated_data

def fetch_historical_data(query):
    """Fetch historical data from the database based on the query"""
    try:
        import requests
        
        # Database statistics
        if any(word in query.lower() for word in ['stats', 'statistics', 'database', 'summary']):
            response = requests.get('http://localhost:8080/api/database/stats', timeout=5)
            if response.status_code == 200:
                return response.json().get('stats', {})
        
        # Active aircraft
        if any(word in query.lower() for word in ['active', 'recent', 'current']):
            response = requests.get('http://localhost:8080/api/aircraft/active?minutes=60', timeout=5)
            if response.status_code == 200:
                data = response.json().get('active_aircraft', [])
                return validate_aircraft_data(data)
        
        # Flight events
        if any(word in query.lower() for word in ['events', 'activity', 'movements']):
            response = requests.get('http://localhost:8080/api/events?hours=24', timeout=5)
            if response.status_code == 200:
                return response.json().get('events', [])
        
        return None
    except Exception as e:
        print(f"[Historical data fetch error] {e}")
        return None

def generate_chat_response(query, context_messages, chat_model="gemma:2b", historical_data=None):
    """Generate conversational response using retrieved context"""
    
    # Check if this is a general greeting or simple question
    simple_queries = ['hello', 'hi', 'hey', 'how are you', 'what can you do', 'help']
    is_simple_query = any(simple in query.lower() for simple in simple_queries)
    
    # Check if this is an aircraft-specific question
    aircraft_keywords = ['aircraft', 'plane', 'flight', 'flying', 'how many', 'count', 'traffic']
    is_aircraft_query = any(keyword in query.lower() for keyword in aircraft_keywords)
    
    # Check if this is a weather-specific question
    weather_keywords = ['weather', 'metar', 'temperature', 'wind', 'visibility', 'conditions', 'forecast']
    is_weather_query = any(keyword in query.lower() for keyword in weather_keywords)
    
    # Check if this is a historical data question
    historical_keywords = ['history', 'historical', 'past', 'yesterday', 'last week', 'database', 'stats', 'summary']
    is_historical_query = any(keyword in query.lower() for keyword in historical_keywords)
    
    # For simple queries, give a general response without overwhelming with data
    if is_simple_query:
        system_prompt = """You are an aviation radar assistant with live aircraft data and historical database access. Keep responses brief and focused.

You can help with:
- Aircraft tracking (live data)
- Historical data and trends
- Weather and METAR
- NOTAMs and airspace
- Aviation questions

Keep it short and to the point."""
    elif is_weather_query and context_messages:
        # For weather questions, prioritize METAR data over NOTAMs
        weather_data = [msg for msg in context_messages if 'METAR' in msg or 'weather' in msg.lower()]
        metar_data = [msg for msg in context_messages if 'METAR' in msg]
        
        # Only include NOTAMs if they're specifically about weather conditions
        weather_notams = [msg for msg in context_messages if 'NOTAM' in msg and any(w in msg.lower() for w in ['weather', 'visibility', 'wind', 'ceiling'])]
        
        # Prioritize METAR data, then weather data, limit NOTAMs to 1 if relevant
        if metar_data:
            context_text = "\n".join(metar_data + weather_notams[:1])
        elif weather_data:
            context_text = "\n".join(weather_data + weather_notams[:1])
        else:
            context_text = "\n".join(context_messages[:2])  # Fallback to general context
        
        system_prompt = f"""You are an aviation radar assistant. Answer weather questions with METAR data first.

CURRENT WEATHER DATA:
{context_text}

WEATHER GUIDELINES:
- Lead with METAR information when asked about weather
- Include temperature, wind, visibility, ceiling if available
- Mention NOTAMs only if they directly affect weather conditions
- Be brief and accurate
- Focus on current weather conditions
- If no METAR data available, say so clearly
- Keep responses under 80 words"""
    elif is_aircraft_query and context_messages:
        # For aircraft questions, prioritize aircraft data over NOTAMs
        aircraft_data = [msg for msg in context_messages if 'ADS-B' in msg or 'aircraft' in msg.lower()]
        
        # Only include NOTAMs if they're specifically about aircraft restrictions
        relevant_notams = [msg for msg in context_messages if 'NOTAM' in msg and ('aircraft' in msg.lower() or 'flight' in msg.lower())]
        
        # Prioritize aircraft data, limit NOTAMs to 1 if relevant
        if aircraft_data:
            context_text = "\n".join(aircraft_data + relevant_notams[:1])
        else:
            context_text = "\n".join(context_messages[:2])  # Fallback to general context
        
        system_prompt = f"""You are an aviation radar assistant. Answer aircraft questions with aircraft data first.

CURRENT AIRCRAFT DATA:
{context_text}

AIRCRAFT STATUS GUIDELINES:
- CRUISE: Aircraft flying at altitude with speed > 100 knots
- TAXI: Aircraft moving on ground with speed < 50 knots
- PARKED: Aircraft stationary on ground with speed = 0
- CLIMB/DESCENT: Aircraft changing altitude significantly

GUIDELINES:
- Lead with aircraft information when asked about aircraft
- Mention NOTAMs only if they directly affect the aircraft
- Be brief and accurate
- Focus on aircraft count, position, altitude, speed
- IMPORTANT: Validate data consistency - speed and status must match
- If data seems contradictory, use the most logical interpretation
- Keep responses under 80 words"""
    elif is_historical_query and historical_data:
        # For historical questions, use the historical data
        system_prompt = f"""You are an aviation radar assistant with access to historical database data.

HISTORICAL DATA:
{historical_data}

GUIDELINES:
- Use the historical data to answer questions about past activity
- Be specific about timeframes and trends
- Focus on what was asked
- Be brief and accurate
- Keep responses under 100 words"""
    elif context_messages:
        # For other questions, use the context but be smart about it
        context_text = "\n".join([f"- {msg}" for msg in context_messages])
        system_prompt = f"""You are an aviation radar assistant with live data. Be concise and accurate.

CURRENT DATA:
{context_text}

GUIDELINES:
- Use the live data to answer questions directly
- Be brief and to the point
- Focus on what was asked
- If no relevant data, say "No data available"
- Use aviation terms correctly
- Keep responses under 100 words unless more detail is requested"""
    else:
        system_prompt = """You are an aviation radar assistant. I don't have any current aviation data available right now, but I can help with general aviation questions and guidance."""

    try:
        response = chat(
            model=chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 200
            }
        )
        return response['message']['content']
    except Exception as e:
        return f"Chat model error: {str(e)}"

def periodic_rebuild():
    """Periodically rebuild the index with fresh data"""
    while True:
        rebuild_index()
        time.sleep(15)

@app.route("/chat")
def chat_endpoint():
    """Conversational interface with RAG context"""
    query = request.args.get("q", "")
    threshold = float(request.args.get("threshold", "0.3"))  # Lower default for chat
    max_context = int(request.args.get("max_context", "3"))  # Limit context for chat
    chat_model = request.args.get("model", "gemma:2b")
    
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"})

    try:
        # Get relevant context using semantic search
        context_messages = []
        if metadata:  # Only search if we have indexed data
            query_emb = get_embedding(query)
            query_emb = query_emb.reshape(1, -1)
            
            # Check if this is an aircraft question
            aircraft_keywords = ['aircraft', 'plane', 'flight', 'flying', 'how many', 'count', 'traffic']
            is_aircraft_query = any(keyword in query.lower() for keyword in aircraft_keywords)
            
            # Check if this is a weather question
            weather_keywords = ['weather', 'metar', 'temperature', 'wind', 'visibility', 'conditions', 'forecast']
            is_weather_query = any(keyword in query.lower() for keyword in weather_keywords)
            
            if is_aircraft_query:
                # For aircraft questions, prioritize ADS-B data
                search_k = min(max_context * 3, len(metadata))  # Search more broadly
                scores, idxs = index.search(query_emb, search_k)
                
                # First, get all ADS-B messages
                adsb_messages = []
                other_messages = []
                
                for score, idx in zip(scores[0], idxs[0]):
                    if idx < len(metadata) and score >= threshold:
                        msg = metadata[idx]
                        if 'ADS-B' in msg:
                            adsb_messages.append(msg)
                        else:
                            other_messages.append(msg)
                
                # Prioritize ADS-B data, then add other relevant data
                context_messages = adsb_messages + other_messages[:max_context - len(adsb_messages)]
                context_messages = context_messages[:max_context]
            elif is_weather_query:
                # For weather questions, prioritize METAR and weather data
                search_k = min(max_context * 3, len(metadata))  # Search more broadly
                scores, idxs = index.search(query_emb, search_k)
                
                # First, get all METAR and weather messages
                metar_messages = []
                weather_messages = []
                other_messages = []
                
                for score, idx in zip(scores[0], idxs[0]):
                    if idx < len(metadata) and score >= threshold:
                        msg = metadata[idx]
                        if 'METAR' in msg:
                            metar_messages.append(msg)
                        elif 'weather' in msg.lower():
                            weather_messages.append(msg)
                        else:
                            other_messages.append(msg)
                
                # Prioritize METAR data, then weather data, then other relevant data
                context_messages = metar_messages + weather_messages + other_messages[:max_context - len(metar_messages) - len(weather_messages)]
                context_messages = context_messages[:max_context]
            else:
                # For other questions, use normal search
                scores, idxs = index.search(query_emb, min(max_context * 2, len(metadata)))
                
                # Get relevant messages above threshold
                for score, idx in zip(scores[0], idxs[0]):
                    if idx < len(metadata) and score >= threshold:
                        context_messages.append(metadata[idx])
                
                context_messages = context_messages[:max_context]
        
        # Check if we need historical data
        historical_data = None
        if any(word in query.lower() for word in ['history', 'historical', 'past', 'yesterday', 'last week', 'database', 'stats', 'summary']):
            historical_data = fetch_historical_data(query)
        
        # Generate conversational response
        chat_response = generate_chat_response(query, context_messages, chat_model, historical_data)
        
        return jsonify({
            "query": query,
            "response": chat_response,
            "context_used": len(context_messages),
            "historical_data": historical_data is not None,
            "context_messages": context_messages if request.args.get("show_context") == "true" else None,
            "model": chat_model,
            "threshold_used": threshold
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Chat error: {str(e)}",
            "query": query
        })

@app.route("/ask")
def ask_question():
    query = request.args.get("q", "")
    threshold = float(request.args.get("threshold", "0.3"))  # Lower default threshold
    max_results = int(request.args.get("max_results", "5"))
    format_type = request.args.get("format", "simple")  # "simple" or "detailed"
    debug_mode = request.args.get("debug", "false").lower() == "true"
    
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"})

    if not metadata:
        return jsonify({
            "error": "No indexed data available. Please wait for initial indexing to complete."
        })

    try:
        # Get query embedding
        query_emb = get_embedding(query)
        query_emb = query_emb.reshape(1, -1)
        
        # Search for similar messages
        search_k = min(max_results * 3, len(metadata))  # Search more than needed
        scores, idxs = index.search(query_emb, search_k)
        
        debug_info = {}
        if debug_mode:
            debug_info = {
                "query_embedding_shape": query_emb.shape,
                "search_k": search_k,
                "raw_scores": scores[0][:5].tolist(),
                "raw_indices": idxs[0][:5].tolist(),
                "threshold": threshold,
                "metadata_count": len(metadata)
            }
        
        # Filter results by confidence threshold
        filtered_results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < len(metadata) and score >= threshold:  # Higher cosine similarity = better match
                filtered_results.append({
                    "text": metadata[idx],
                    "confidence": float(score),
                    "score": float(score)
                })
        
        # If no results with threshold, show best matches anyway in debug mode
        if not filtered_results and debug_mode:
            debug_info["best_matches_regardless_of_threshold"] = []
            for score, idx in zip(scores[0][:3], idxs[0][:3]):
                if idx < len(metadata):
                    debug_info["best_matches_regardless_of_threshold"].append({
                        "text": metadata[idx][:100] + "...",  # Truncated for debug
                        "score": float(score)
                    })
        
        # Limit to max_results
        filtered_results = filtered_results[:max_results]
        
        # Format results based on requested format
        if format_type == "detailed":
            # Return detailed format with confidence scores
            response = {
                "query": query,
                "threshold_used": threshold,
                "total_indexed": len(metadata),
                "results_found": len(filtered_results),
                "results": filtered_results if filtered_results else ["No relevant messages found above confidence threshold."],
                "best_match_confidence": filtered_results[0]["confidence"] if filtered_results else 0.0
            }
            if debug_mode:
                response["debug"] = debug_info
        else:
            # Return simple format (backward compatible)
            if filtered_results:
                # Just return the text strings with optional confidence info
                simple_results = []
                for result in filtered_results:
                    confidence_str = f" (confidence: {result['confidence']:.2f})" if request.args.get("show_confidence") == "true" else ""
                    simple_results.append(result["text"] + confidence_str)
                response = {
                    "query": query,
                    "results": simple_results
                }
            else:
                response = {
                    "query": query, 
                    "results": [f"No relevant messages found above confidence threshold {threshold}. Try lowering threshold with &threshold=0.3"]
                }
            
            if debug_mode:
                response["debug"] = debug_info
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Search error: {str(e)}",
            "query": query
        })

@app.route("/rebuild")
def manual_rebuild():
    """Manually trigger index rebuild"""
    try:
        rebuild_index()
        return jsonify({
            "status": "success",
            "message": "Index rebuilt successfully",
            "metadata_count": len(metadata),
            "index_size": index.ntotal if hasattr(index, 'ntotal') else 'unknown'
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Rebuild failed: {str(e)}"
        })

@app.route("/debug")
def debug_info():
    """Debug endpoint to check index status and test embeddings"""
    debug_data = {
        "index_status": {
            "total_vectors": index.ntotal if index else 0,
            "metadata_count": len(metadata),
            "index_dimension": EMBED_DIM,
            "index_type": str(type(index)) if index else "None"
        },
        "sample_metadata": metadata[:3] if metadata else [],
        "files_exist": {
            "adsb_file": os.path.exists(ADS_B_FILE),
            "vdl2_file": os.path.exists(VDL2_FILE),
            "index_file": os.path.exists(INDEX_FILE),
            "meta_file": os.path.exists(META_FILE)
        }
    }
    
    # Test embedding generation
    try:
        test_emb = get_embedding("test aircraft message")
        debug_data["embedding_test"] = {
            "success": True,
            "embedding_shape": len(test_emb),
            "sample_values": test_emb[:5].tolist() if len(test_emb) >= 5 else test_emb.tolist()
        }
    except Exception as e:
        debug_data["embedding_test"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test a simple search
    try:
        if metadata and index.ntotal > 0:
            query_emb = get_embedding("aircraft")
            query_emb = query_emb.reshape(1, -1)
            scores, idxs = index.search(query_emb, min(3, len(metadata)))
            debug_data["search_test"] = {
                "success": True,
                "scores": scores[0].tolist(),
                "indices": idxs[0].tolist(),
                "best_score": float(scores[0][0]) if len(scores[0]) > 0 else "no results"
            }
        else:
            debug_data["search_test"] = {"success": False, "reason": "no_data_indexed"}
    except Exception as e:
        debug_data["search_test"] = {
            "success": False,
            "error": str(e)
        }
    
    return jsonify(debug_data)
    """Health check and index status endpoint"""
    return jsonify({
        "status": "running",
        "indexed_messages": len(metadata),
        "index_dimension": EMBED_DIM,
        "model": "nomic-embed-text",
        "similarity_method": "cosine",
        "files_monitored": [ADS_B_FILE, VDL2_FILE]
    })

@app.route("/")
def home():
    return """
    <h1>Radar AI Assistant (Semantic RAG + Chat)</h1>
    <p>Endpoints:</p>
    <ul>
        <li><code>/ask?q=your_query&threshold=0.7&max_results=5</code> - Search messages</li>
        <li><code>/chat?q=your_question&threshold=0.6&model=gemma3:4b</code> - Conversational interface</li>
        <li><code>/status</code> - Check system status</li>
        <li><code>/debug</code> - Debug index and embedding status</li>
    </ul>
    <p><strong>Troubleshooting:</strong></p>
    <ul>
        <li>No results? Try: <code>/ask?q=aircraft&threshold=0.1&debug=true</code></li>
        <li>Check system: <code>/debug</code></li>
        <li>Lower threshold: <code>&threshold=0.3</code> or <code>&threshold=0.1</code></li>
    </ul>
    <p>Using cosine similarity with confidence thresholding + Gemma3 4B chat.</p>
    """

if __name__ == "__main__":
    print("\n🚀 Launching Radar AI Assistant (Semantic RAG + Chat)")
    print("📊 Using cosine similarity with confidence thresholding")
    print("🤖 Chat powered by Gemma3 4B")
    print(f"📁 Monitoring: {ADS_B_FILE}, {VDL2_FILE}")
    print(f"🧠 Embedding Model: nomic-embed-text ({EMBED_DIM}D)")
    
    # Load existing index if available
    try:
        if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
            print("📂 Loading existing index...")
            index = faiss.read_index(INDEX_FILE)
            with open(META_FILE, "r") as f:
                metadata = json.load(f)
            print(f"✅ Loaded {len(metadata)} existing messages")
    except Exception as e:
        print(f"⚠️ Could not load existing index: {e}")
        print("🔄 Will rebuild on startup...")
    
def analyze_flight_phase(altitude, speed, vertical_rate, airspace):
    """Analyze flight phase using same logic as frontend"""
    # Ground operations
    if altitude < 100 and speed < 50:
        if speed < 5: return 'PARKED'
        if speed < 25: return 'TAXIING'
        return 'GROUND OPS'
    
    # Airspace-aware analysis
    airspace_type = airspace.get('type', 'Class G') if airspace else 'Class G'
    airspace_name = airspace.get('name', 'Uncontrolled') if airspace else 'Uncontrolled'
    
    # Airport operations (CTR indicates airport control zone)
    if airspace_type == 'CTR' or 'CTR' in airspace_name:
        if altitude < 3000:
            if vertical_rate > 800: return 'DEPARTURE'
            if vertical_rate < -800: return 'FINAL APPROACH'
            if speed < 200: return 'AIRPORT PATTERN'
            return 'TERMINAL AREA'
    
    # Terminal area operations (TMA/CTA)
    if airspace_type in ['TMA', 'CTA/TMA', 'CTA']:
        if vertical_rate > 1000: return 'TERMINAL CLIMB'
        if vertical_rate < -1000: return 'TERMINAL DESCENT'
        if altitude < 10000: return 'TERMINAL AREA'
    
    # General flight phases
    if altitude < 3000:
        if vertical_rate > 500: return 'TAKEOFF'
        if vertical_rate < -500: return 'APPROACH'
        if speed < 200: return 'PATTERN'
        return 'LOW LEVEL'
    
    # Climb/Descent phases
    if abs(vertical_rate) > 300:
        if vertical_rate > 1500: return 'RAPID CLIMB'
        if vertical_rate > 800: return 'CLIMBING'
        if vertical_rate > 300: return 'SLOW CLIMB'
        if vertical_rate < -1500: return 'RAPID DESCENT'
        if vertical_rate < -800: return 'DESCENDING'
        if vertical_rate < -300: return 'SLOW DESCENT'
    
    # High altitude operations
    if altitude > 35000: return 'HIGH CRUISE'
    if altitude > 20000: return 'CRUISE'
    if altitude > 10000: return 'MEDIUM LEVEL'
    
    # Default based on altitude and speed
    if speed > 400: return 'HIGH SPEED'
    if speed > 250: return 'ENROUTE'
    if speed > 150: return 'APPROACH SPEED'
    
    return 'IN FLIGHT'

def analyze_atc_from_squawk(squawk):
    """Analyze ATC center from squawk code"""
    if not squawk or squawk == '0000': return 'NO SQUAWK'
    
    code = str(squawk).zfill(4)
    
    # Emergency codes
    if code == '7700': return 'EMERGENCY'
    if code == '7600': return 'RADIO FAILURE'
    if code == '7500': return 'HIJACK'
    
    # VFR codes
    if code == '7000': return 'VFR'
    if code == '7004': return 'AEROBATIC'
    if code == '7010': return 'VFR ABOVE FL100'
    
    # Special codes
    if code == '0001': return 'HEIGHT MONITOR'
    if code == '0002': return 'GROUND TEST'
    if code.startswith('00'): return 'SPECIAL USE'
    
    # UK ATC Centers (based on squawk ranges)
    if '0100' <= code <= '0777': return 'LONDON CONTROL'
    if '1000' <= code <= '1777': return 'SCOTTISH CONTROL'
    if '2000' <= code <= '2777': return 'MANCHESTER CONTROL'
    if '3000' <= code <= '3777': return 'LONDON TC'
    if '4000' <= code <= '4777': return 'APPROACH CONTROL'
    if '5000' <= code <= '5777': return 'AREA CONTROL'
    if '6000' <= code <= '6777': return 'TERMINAL CONTROL'
    
    # Default for assigned codes
    if '0100' <= code <= '7777': return 'ATC ASSIGNED'
    
    return 'UNKNOWN'

def analyze_aircraft_intention(aircraft, phase, airspace):
    """Analyze aircraft intentions from airspace and flight data"""
    altitude = aircraft.get('alt_baro', 0)
    speed = aircraft.get('gs', 0)
    vertical_rate = aircraft.get('baro_rate', 0)
    airspace_type = airspace.get('type', 'Class G') if airspace else 'Class G'
    airspace_name = airspace.get('name', 'Uncontrolled') if airspace else 'Uncontrolled'
    
    # Airport mapping for major UK airports
    airport_map = {
        'heathrow': 'EGLL', 'gatwick': 'EGKK', 'stansted': 'EGSS',
        'luton': 'EGGW', 'manchester': 'EGCC', 'birmingham': 'EGBB',
        'glasgow': 'EGPF', 'edinburgh': 'EGPH', 'bristol': 'EGGD',
        'prestwick': 'EGPK', 'newcastle': 'EGNT', 'leeds': 'EGNM'
    }
    
    # Extract airport code
    airport_code = None
    for name, code in airport_map.items():
        if name in airspace_name.lower():
            airport_code = code
            break
    
    # Airport-specific intentions
    if airspace_type == 'CTR':
        if phase in ['DEPARTURE', 'TAKEOFF']:
            return f'DEPARTING {airport_code or airspace_name.split()[0]}'
        if phase in ['FINAL APPROACH', 'APPROACH']:
            return f'LANDING {airport_code or airspace_name.split()[0]}'
        if phase == 'AIRPORT PATTERN':
            return f'PATTERN {airport_code or airspace_name.split()[0]}'
        if phase in ['TAXIING', 'GROUND OPS']:
            return f'GROUND {airport_code or airspace_name.split()[0]}'
    
    # Terminal area intentions
    if airspace_type in ['TMA', 'CTA/TMA']:
        if vertical_rate > 1000:
            return f'CLIMBING IN {airspace_name}'
        if vertical_rate < -1000:
            return f'DESCENDING TO {airport_code or airspace_name.split()[0]}'
        return f'TRANSITING {airspace_name}'
    
    # Controlled airspace intentions
    if airspace_type == 'CTA':
        if vertical_rate > 500:
            return 'CLIMBING TO CRUISE'
        if vertical_rate < -500:
            return 'DESCENDING FOR APPROACH'
        return f'ENROUTE IN {airspace_name}'
    
    # VFR intentions
    if aircraft.get('squawk') == '7000' or aircraft.get('squawk') == 7000:
        if altitude < 5000:
            return 'VFR LOCAL FLIGHT'
        return 'VFR CROSS COUNTRY'
    
    # General intentions based on phase
    if phase in ['HIGH CRUISE', 'CRUISE']:
        return 'ENROUTE CRUISE'
    if 'CLIMB' in phase:
        return 'CLIMBING TO CRUISE'
    if 'DESCENT' in phase:
        return 'DESCENDING FOR LANDING'
    if phase == 'APPROACH':
        return 'INBOUND FOR LANDING'
    if phase == 'PATTERN':
        return 'TRAFFIC PATTERN'
    
    return 'GENERAL FLIGHT'

if __name__ == "__main__":
    # Start periodic rebuild thread
    threading.Thread(target=periodic_rebuild, daemon=True).start()
    
    print("🤖 AI Server starting with enhanced flight status intelligence")
    print("🔍 Semantic search endpoint: /ask?q=your_question")
    print("💬 Chat endpoint: /chat?q=your_question")
    print("✈️ Flight status analysis: ENABLED")
    
    # Run Flask app
    app.run(host="0.0.0.0", port=11435, debug=False)
