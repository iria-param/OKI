import serial
import requests
import json
import time

# --- CONFIG ---
PORT = "COM6"
BAUD = 9600
SUPABASE_URL = "ENTER_SUPABASE_URL"
SUPABASE_KEY = "ENTER_SUPABASE_KEY"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

print("🛡️ Oki Admin Dashboard Active. Scan a tag to register a visitor.")

ser = serial.Serial(PORT, BAUD, timeout=0.1)

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if line:
        print(f"\n🔍 Tag Detected: {line}")
        
        # 1. Check if this tag is CURRENTLY in use (not checked out)
        query_url = f"{SUPABASE_URL}/visitors?rfid_uid=eq.{line}&check_out=is.null"
        resp = requests.get(query_url, headers=headers)
        active_visitors = resp.json()

        if isinstance(active_visitors, list) and len(active_visitors) > 0:
            visitor = active_visitors[0]
            print(f"👤 Tag is ACTIVE with: {visitor['name']}")
            action = input("Press 'X' to Check-out (free the tag) or 'Enter' to skip: ")
            if action.lower() == 'x':
                requests.patch(f"{SUPABASE_URL}/visitors?id=eq.{visitor['id']}", 
                               json={"check_out": "now()"}, headers=headers)
                print(f"✅ {visitor['name']} checked out.")
        else:
            # 2. Tag is free! Register new person
            print("🆕 NEW REGISTRATION")
            name = input("Name: ")
            age = int(input("Age: "))
            profile = "KID_U8" if age < 8 else ("TEEN_U18" if age < 18 else "ADULT_18_PLUS")
            
            data = {"rfid_uid": line, "name": name, "age": age, "profile_type": profile}
            res = requests.post(f"{SUPABASE_URL}/visitors", json=data, headers=headers)
            if res.status_code in [200, 201]:
                print(f"✅ Success! {name} registered as {profile}.")
            else:
                print(f"❌ Error: {res.text}")
    time.sleep(0.1)