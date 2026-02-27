import os
from flask import Flask, request, jsonify, render_template_string
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- DATABASE CONFIGURATION ---
# In details ko apne Aiven Dashboard se check karke sahi bhariye
db_config = {
    'host': 'mysql-2622950a-soaloksoni21703-f300.j.aivencloud.com',      
    'user': 'avnadmin',
    'password': 'AVNS_K2VFCeaK0KhtqVEKGN6',   
    'database': 'defaultdb',
    'port': 27756  # Aiven ka default port aksar yahi hota hai
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- 1. FRONTEND DASHBOARD (Isi file ke andar) ---
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Women Safety Live Tracker</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 10px; background: #f0f2f5; }
            .container { max-width: 900px; margin: auto; background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            #map { height: 450px; width: 100%; border-radius: 8px; margin-top: 15px; }
            .status-panel { display: flex; justify-content: space-around; margin-top: 15px; font-weight: bold; }
            #alert-banner { padding: 15px; border-radius: 8px; text-align: center; display: none; margin-bottom: 10px; }
            .danger { background: #ff4d4d; color: white; display: block !important; animation: blink 1s infinite; }
            @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="text-align:center;">🔴 Live Safety Dashboard</h2>
            <div id="alert-banner">🚨 EMERGENCY ALERT DETECTED! 🚨</div>
            <div id="map"></div>
            <div class="status-panel">
                <div>Status: <span id="st-text" style="color:green;">Normal</span></div>
                <div>Last Seen: <span id="st-time">-</span></div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            var marker = L.marker([0, 0]).addTo(map);

            async function updateDashboard() {
                try {
                    const response = await fetch('/get_location');
                    const data = await response.json();
                    if(data && data.latitude) {
                        const pos = [data.latitude, data.longitude];
                        marker.setLatLng(pos);
                        map.setView(pos, 16);
                        document.getElementById('st-time').innerText = data.timestamp;
                        
                        if(data.alert_level > 0) {
                            document.getElementById('alert-banner').className = "danger";
                            document.getElementById('st-text').innerText = "EMERGENCY";
                            document.getElementById('st-text').style.color = "red";
                        } else {
                            document.getElementById('alert-banner').className = "";
                            document.getElementById('st-text').innerText = "Normal";
                            document.getElementById('st-text').style.color = "green";
                        }
                    }
                } catch (e) { console.error("Update error"); }
            }
            setInterval(updateDashboard, 3000); // Har 3 second mein refresh
        </script>
    </body>
    </html>
    ''')

# --- 2. API: RECEIVE FROM ESP32 ---
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

# --- 3. API: SEND TO DASHBOARD ---
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
            # Timestamp ko string mein badalna zaroori hai JSON ke liye
            result['timestamp'] = result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Port Render ke liye dynamic hona chahiye
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
