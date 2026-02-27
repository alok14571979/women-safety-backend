import os
from flask import Flask, request, jsonify, render_template_string
import mysql.connector
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
# CORS setup taaki browser map data fetch kar sake bina kisi security error ke
CORS(app)

# --- DATABASE CONFIGURATION ---
db_config = {
    'host': 'mysql-2622950a-soaloksoni21703-f300.j.aivencloud.com',      # Aiven Host yahan dalein
    'user': 'avnadmin',
    'password': 'AVNS_K2VFCeaK0KhtqVEKGN6',   # Aiven Password yahan dalein
    'database': 'defaultdb',
    'port': 27756
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- FRONTEND: HTML + MAP DASHBOARD ---
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Women Safety Shield - LIVE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #f4f7f6; color: #333; }
            .nav { background: #2c3e50; color: white; padding: 15px; text-align: center; font-size: 1.2rem; font-weight: bold; }
            .container { padding: 15px; max-width: 1000px; margin: auto; }
            #map { height: 450px; width: 100%; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border: 4px solid white; }
            .stats { display: flex; justify-content: space-around; margin-top: 20px; background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            .stat-box { text-align: center; }
            .stat-box small { color: #888; display: block; text-transform: uppercase; font-size: 0.7rem; }
            .stat-box span { font-size: 1.1rem; font-weight: bold; color: #2c3e50; }
            #alert-msg { padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; display: none; transition: 0.3s; }
            .emergency { display: block !important; background: #e74c3c; color: white; animation: blink 1s infinite; }
            @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        </style>
    </head>
    <body>
        <div class="nav">🛡️ WOMEN SAFETY LIVE MONITOR</div>
        <div class="container">
            <div id="alert-msg">🚨 EMERGENCY DETECTED! 🚨</div>
            <div id="map"></div>
            <div class="stats">
                <div class="stat-box"><small>Battery</small><span id="bat">--%</span></div>
                <div class="stat-box"><small>Signal</small><span id="conn">--</span></div>
                <div class="stat-box"><small>Last Update</small><span id="time">--:--:--</span></div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Initial map view (India)
            var map = L.map('map').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            var marker = L.marker([0, 0]).addTo(map);

            async function refreshData() {
                try {
                    const res = await fetch('/get_location');
                    if (!res.ok) return;
                    const data = await res.json();
                    
                    if(data && data.latitude != 0) {
                        var lat = parseFloat(data.latitude);
                        var lng = parseFloat(data.longitude);
                        var newPos = [lat, lng];

                        // Smoothly move marker and map
                        marker.setLatLng(newPos);
                        map.panTo(newPos);
                        if(map.getZoom() < 10) map.setZoom(16); // Pehli baar mein zoom karein

                        // Update Stats UI
                        document.getElementById('bat').innerText = data.battery_level + "%";
                        document.getElementById('conn').innerText = data.connection_type;
                        document.getElementById('time').innerText = data.timestamp;

                        // Alert Logic
                        if(data.alert_level > 0) {
                            document.getElementById('alert-msg').className = "emergency";
                        } else {
                            document.getElementById('alert-msg').className = "";
                        }
                    }
                } catch (err) { console.log("Update check failed..."); }
            }
            setInterval(refreshData, 3000); // Har 3 seconds mein data check karein
        </script>
    </body>
    </html>
    ''')

# --- API: RECEIVE DATA FROM ESP32 ---
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """INSERT INTO location_logs 
                   (user_id, latitude, longitude, alert_level, battery_level, connection_type) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        values = (1, data['lat'], data['lng'], data['alert'], data['battery'], data['connection'])
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API: SEND LATEST DATA TO DASHBOARD ---
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
        else:
            # Agar DB khali hai toh default coordinates bhejein crash se bachne ke liye
            return jsonify({"latitude": 20.5937, "longitude": 78.9629, "alert_level": 0, "battery_level": 0, "connection_type": "No Data", "timestamp": "N/A"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
