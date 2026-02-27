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
        <title>Women Safety Shield - LIVE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #f4f7f6; }
            .nav { background: #2c3e50; color: white; padding: 15px; text-align: center; font-weight: bold; }
            .container { padding: 15px; max-width: 1000px; margin: auto; }
            #map { height: 450px; width: 100%; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
            .stats { display: flex; justify-content: space-around; margin-top: 20px; background: white; padding: 15px; border-radius: 10px; }
            .stat-box { text-align: center; }
            #alert-msg { padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; display: none; }
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
                <div class="stat-box"><strong>Battery:</strong> <span id="bat">--%</span></div>
                <div class="stat-box"><strong>Mode:</strong> <span id="conn">--</span></div>
                <div class="stat-box"><strong>Time:</strong> <span id="time">--:--:--</span></div>
            </div>
        </div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            var marker = L.marker([0, 0]).addTo(map);

            async function refreshData() {
                try {
                    const res = await fetch('/get_location');
                    const data = await res.json();
                    if(data && data.latitude != 20.5937) {
                        var pos = [data.latitude, data.longitude];
                        marker.setLatLng(pos);
                        map.panTo(pos);
                        if(map.getZoom() < 10) map.setZoom(16);
                        document.getElementById('bat').innerText = data.battery_level + "%";
                        document.getElementById('conn').innerText = data.connection_type;
                        document.getElementById('time').innerText = data.timestamp;
                        if(data.alert_level > 0) document.getElementById('alert-msg').className = "emergency";
                        else document.getElementById('alert-msg').className = "";
                    }
                } catch (err) { console.log("Waiting for data..."); }
            }
            setInterval(refreshData, 3000);
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
