
 
import serial
import requests
import threading
from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")

# --- CONFIG ---
PORT = "COM6"
BAUD = 9600

SUPABASE_KEY =  os.getenv("SUPABASE_KEY")

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def serial_listener():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                # Query for an active session with this UID
                query_url = f"{SUPABASE_URL}/visitors?rfid_uid=eq.{line}&check_out=is.null"
                resp = requests.get(query_url, headers=headers)
                socketio.emit('rfid_scan', {'uid': line, 'active_visitor': resp.json()})
    except Exception as e:
        print(f"Serial Error: {e}")

@socketio.on('register_user')
def handle_registration(data):
    profile = "KID_U8" if int(data['age']) < 8 else ("TEEN_U18" if int(data['age']) < 18 else "ADULT_18_PLUS")
    payload = {"rfid_uid": data['uid'], "name": data['name'], "age": int(data['age']), "profile_type": profile}
    res = requests.post(f"{SUPABASE_URL}/visitors", json=payload, headers=headers)
    if res.status_code in [200, 201]:
        emit('action_complete', {'message': f"Registered {data['name']}"})

@socketio.on('checkout_user')
def handle_checkout(data):
    res = requests.patch(f"{SUPABASE_URL}/visitors?id=eq.{data['id']}", json={"check_out": "now()"}, headers=headers)
    if res.status_code in [200, 201]:
        emit('action_complete', {'message': "Checkout Successful"})

# --- NEW: STATS ENGINE ---
@socketio.on('get_stats')
def handle_get_stats(data):
    # Get stats for a specific date (YYYY-MM-DD)
    target_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Supabase filter: check_in >= start of day AND check_in < start of next day
    query_url = f"{SUPABASE_URL}/visitors?check_in=gte.{target_date}T00:00:00&check_in=lt.{target_date}T23:59:59&order=check_in.desc"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code == 200:
        emit('stats_data', resp.json())

if __name__ == '__main__':
    threading.Thread(target=serial_listener, daemon=True).start()
    socketio.run(app, port=5000)    