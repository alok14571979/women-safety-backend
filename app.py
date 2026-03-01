import os
import requests
import mysql.connector
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION SECTION ---
# Aiven Database Details
db_config = {
    'host': 'mysql-2622950a-soaloksoni21703-f300.j.aivencloud.com', 
    'user': 'avnadmin',
    'password': 'AVNS_K2VFCeaK0KhtqVEKGN6', 
    'database': 'defaultdb',
    'port': 27756
}

# Google Form API Link (For Permanent Backup)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdHDJvYqxEG79WiGZfbcTEBOLNTwR9l2c76DcSCGZIlW02PcQ/formResponse"

# Sync Control: Har 10 minute mein ek baar Google Sheet update hogi
last_sheet_update = datetime.now() - timedelta(minutes=10)

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- DATABASE SETUP ROUTE ---
@app.route('/setup')
def setup_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Table Creation with all necessary columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_logs (
                id INT PRIMARY KEY,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                alert_level INT,
                battery_level INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        # Insert initial row if not exists
        cursor.execute("INSERT IGNORE INTO location_logs (id, latitude, longitude, alert_level, battery_level) VALUES (1, 0.0, 0.0, 0, 0)")
        conn.commit()
        cursor.close()
        conn.close()
        return """
        <div style='text-align:center; padding:50px; font-family:sans-serif;'>
            <h1 style='color:green;'>✅ Setup Successful!</h1>
            <p>Database is optimized for single-row live tracking.</p>
            <a href='/'>Go to Dashboard</a>
        </div>
        """, 200
    except Exception as e:
        return f"<h1 style='color:red;'>❌ Setup Error: {str(e)}</h1>", 500

# --- FULL FEATURED DASHBOARD UI ---
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🛡️ Women Safety Tracker - Satellite Live</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { background: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; overflow: hidden; }
            #header { background: #1a1a1a; padding: 15px; text-align: center; border-bottom: 2px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
            #map { height: calc(100vh - 140px); width: 100%; }
            .info-bar { display: flex; justify-content: space-around; padding: 15px; background: #1a1a1a; border-top: 2px solid #333; position: fixed; bottom: 0; width: 100%; z-index: 1000; }
            .stat-box { text-align: center; }
            .stat-label { font-size: 10px; color: #888; text-transform: uppercase; }
            .stat-value { font-size: 18px; font-weight: bold; color: #00ffcc; }
            .alert-high { color: #ff3333 !important; animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0.3; } }
        </style>
    </head>
    <body>
        <div id="header">
            <h2 style="margin:0; letter-spacing: 2px;">🛡️ WOMEN SAFETY LIVE SATELLITE TRACKER</h2>
        </div>
        
        <div id="map"></div>

        <div class="info-bar">
            <div class="stat-box">
                <div class="stat-label">Latitude</div>
                <div class="stat-value" id="lat">0.0000</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Longitude</div>
                <div class="stat-value" id="lng">0.0000</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Battery Status</div>
                <div class="stat-value" id="bat">--%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Last Sync (UTC)</div>
                <div class="stat-value" id="time">--:--:--</div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Layer setups
            var streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
            var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}');

            var map = L.map('map', {
                center: [20.5937, 78.9629],
                zoom: 5,
                layers: [satelliteLayer]
            });

            var baseLayers = { "Satellite View": satelliteLayer, "Street View": streetLayer };
            L.control.layers(baseLayers).addTo(map);

            var marker = L.marker([0, 0]).addTo(map);
            var firstLoad = true;

            async function updateUI() {
                try {
                    const response = await fetch('/get_location');
                    const data = await response.json();
                    
                    if(data.latitude !== 0) {
                        const pos = [data.latitude, data.longitude];
                        marker.setLatLng(pos);
                        
                        document.getElementById('lat').innerText = data.latitude.toFixed(6);
                        document.getElementById('lng').innerText = data.longitude.toFixed(6);
                        document.getElementById('bat').innerText = data.battery_level + "%";
                        document.getElementById('time').innerText = data.timestamp;

                        if(firstLoad) {
                            map.setView(pos, 17);
                            firstLoad = false;
                        } else {
                            map.panTo(pos);
                        }

                        // Alert Visual Logic
                        if(data.alert_level > 0) {
                            document.getElementById('header').style.background = "#450000";
                        } else {
                            document.getElementById('header').style.background = "#1a1a1a";
                        }
                    }
                } catch (err) { console.error("Syncing..."); }
            }

            setInterval(updateUI, 5000); // UI updates every 5 seconds
        </script>
    </body>
    </html>
    ''')

# --- DATA RECEIVER (POST) ---
@app.route('/update_location', methods=['POST'])
def update_location():
    global last_sheet_update
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Update Aiven (Live Row ID=1)
        update_query = """
            UPDATE location_logs 
            SET latitude=%s, longitude=%s, alert_level=%s, battery_level=%s, timestamp=NOW() 
            WHERE id=1
        """
        cursor.execute(update_query, (data['lat'], data['lng'], data['alert'], data['battery']))
        
        # 2. Google Form Sync (History Backup every 10 mins)
        now = datetime.now()
        if now - last_sheet_update >= timedelta(minutes=10):
            try:
                form_payload = {
                    "entry.362679473": data['lat'],
                    "entry.1387206127": data['lng'],
                    "entry.1495376179": data['alert'],
                    "entry.747084692": data['battery']
                }
                requests.get(FORM_URL, params=form_payload, timeout=5)
                last_sheet_update = now
                print(">>> Backup synced to Google Sheets ✅")
            except Exception as e:
                print(f">>> Sheet Sync Error: {e}")

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "sync": "active"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- DATA FETCH (GET) ---
@app.route('/get_location', methods=['GET'])
def get_location():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM location_logs WHERE id=1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return jsonify({
                "latitude": float(row['latitude']),
                "longitude": float(row['longitude']),
                "alert_level": int(row['alert_level']),
                "battery_level": int(row['battery_level']),
                "timestamp": row['timestamp'].strftime("%H:%M:%S")
            }), 200
        return jsonify({"latitude": 0, "longitude": 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
