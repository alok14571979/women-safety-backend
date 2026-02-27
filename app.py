from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# --- DATABASE CONNECTION DETAILS ---
# Ye details aapko Aiven Dashboard par milengi
db_config = {
    'host': 'mysql-2622950a-soaloksoni21703-f300.j.aivencloud.com',
    'user': 'avnadmin',
    'password': 'AVNS_K2VFCeaK0KhtqVEKGN6',
    'database': 'defaultdb', # Aiven mein defaultdb hota hai
    'port': '27756'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def home():
    return "Women Safety Server is Running!"

# --- API TO RECEIVE DATA FROM ESP32 ---
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    
    # ESP32 se aane wala data: lat, lng, alert, battery, connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """INSERT INTO location_logs 
                   (user_id, latitude, longitude, alert_level, battery_level, connection_type) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        
        # Maan lete hain user_id = 1 hai (Aap baad mein ise badal sakte hain)
        values = (1, data['lat'], data['lng'], data['alert'], data['battery'], data['connection'])
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Location updated"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)