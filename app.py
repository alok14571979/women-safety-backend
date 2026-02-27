import os
from flask import Flask, request, jsonify, render_template_string
import mysql.connector
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- UPDATED DATABASE CONFIG (As per your Aiven screenshot) ---
db_config = {
    'host': 'mysql-2622950a-soaloksoni21703-f300.j.aivencloud.com', 
    'user': 'avnadmin',
    'password': 'AVNS_K2VFCeaK0KhtqVEKGN6', # Yahan reveal karke apna password dalein
    'database': 'defaultdb',
    'port': 27756
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- STEP 1: AUTO-SETUP ROUTE (Table banane ke liye) ---
@app.route('/setup')
def setup_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Table banane ki query
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                alert_level INT,
                battery_level INT,
                connection_type VARCHAR(20),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return "<h1>Success: Table 'location_logs' created!</h1>", 200
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>", 500

# --- STEP 2: DASHBOARD UI ---
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Women Safety Tracker - Live</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            #map { height: 600px; width: 100%; border-radius: 10px; }
            body { background: #121212; color: white; font-family: sans-serif; margin: 0; }
            .info-bar { display: flex; justify-content: space-around; padding: 15px; background: #1e1e1e; }
        </style>
    </head>
    <body>
        <div style="text-align:center; padding: 10px;"><h2>🛡️ LIVE SATELLITE TRACKER</h2></div>
        <div id="map"></div>
        <div class="info-bar">
            <div>📍 Lat: <span id="lat">0.0</span></div>
            <div>📍 Lng: <span id="lng">0.0</span></div>
            <div>🔋 Battery: <span id="bat">--</span></div>
            <div>🕒 Last Update: <span id="time">--</span></div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Layers: Leaflet Engine + Map Data
            var streetView = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
            var satelliteView = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}');

            var map = L.map('map', {
                center: [20.5937, 78.9629],
                zoom: 5,
                layers: [satelliteView] // Default Satellite rakha hai
            });

            // Switch karne ka option
            var baseMaps = {
                "Satellite": satelliteView,
                "Street (OpenStreetMap)": streetView
            };
            L.control.layers(baseMaps).addTo(map);

            var marker = L.marker([0, 0]).addTo(map);

            async function fetchData() {
                try {
                    const response = await fetch('/get_location');
                    const data = await response.json();
                    
                    if(data && data.latitude != 20.5937) {
                        var pos = [data.latitude, data.longitude];
                        marker.setLatLng(pos);
                        map.panTo(pos);
                        if(map.getZoom() < 10) map.setZoom(17);

                        document.getElementById('lat').innerText = data.latitude;
                        document.getElementById('lng').innerText = data.longitude;
                        document.getElementById('bat').innerText = data.battery_level + "%";
                        document.getElementById('time').innerText = data.timestamp;
                    }
                } catch (e) { console.log("Updating..."); }
            }

            // Har 5 second mein auto-fetch (No full page reload)
            setInterval(fetchData, 5000);
        </script>
    </body>
    </html>
    ''')
    
# --- STEP 3: API ROUTES ---
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO location_logs (user_id, latitude, longitude, alert_level, battery_level, connection_type) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (1, data['lat'], data['lng'], data['alert'], data['battery'], data['connection'])
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_location', methods=['GET'])
def get_location():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM location_logs ORDER BY timestamp DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return jsonify({
                "latitude": float(result['latitude']),
                "longitude": float(result['longitude']),
                "alert_level": int(result['alert_level']),
                "battery_level": int(result['battery_level']),
                "connection_type": str(result['connection_type']),
                "timestamp": result['timestamp'].strftime("%H:%M:%S")
            }), 200
        return jsonify({"latitude": 20.5937, "longitude": 78.9629}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

