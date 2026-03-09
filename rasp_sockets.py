import serial
import asyncio
import websockets
import json
import os

# =====================================================
# SERIAL CONFIG (Raspberry Pi 5 SAFE CONFIG)
# =====================================================
PORT = "/dev/serial0"   # ✅ DO NOT use ttyAMA0 directly
BAUD = 9600

connected_clients = set()

# =====================================================
# 🔥 RFID → GOOGLE CLOUD KEY MAPPING
# 👉 EDIT ONLY THIS DICTIONARY
# =====================================================
RFID_TO_CLOUD_KEY = {
    "$0015228858": "2700E86B46E2",
    "$0015224478": "2700E84E9E1F",
    "$0015224067": "2700E84D0381",
    "$0004122303": "28003EE6BF4F",
    "$0004139435": "28003F29AB95",
    "$0004126444": "28003EF6EC0C",
    "$0015236617": "2700E87E09B8",
    "$0004136582": "2700E85FBA2A",
    "$0015231814": "28003F1E868F",
    "$0004123702": "28003EEC36CC",
    
}
# =====================================================


async def rfid_reader():
    # Verify serial port exists
    if not os.path.exists(PORT):
        print(f"⚠️ Serial port {PORT} not found")
        return

    print(f"🚀 Oki Hardware Bridge active on {PORT}...")

    try:
        # ✅ Proper PySerial configuration
        ser = serial.Serial(
            PORT,
            BAUD,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )

        await asyncio.sleep(1)  # allow UART to stabilize

        while True:
            try:
                if ser.in_waiting > 0:
                    raw_uid = ser.read_until(b'\n').decode(
                        "utf-8", errors="ignore"
                    ).strip()

                    if not raw_uid:
                        continue

                    print(f"📥 RFID scanned: {raw_uid}")

                    # 🔥 MAP RFID → CLOUD KEY
                    cloud_key = RFID_TO_CLOUD_KEY.get(raw_uid)

                    if cloud_key and connected_clients:
                        print(f"✅ Mapped → {cloud_key}")

                        message = json.dumps({
                            "type": "RFID_RAW",  # keep app compatibility
                            "uid": cloud_key
                        })

                        await asyncio.gather(
                            *[client.send(message) for client in connected_clients],
                            return_exceptions=True
                        )
                    else:
                        print("⛔ No mapping found OR no client connected")

                await asyncio.sleep(0.01)

            except serial.SerialException as e:
                print(f"❌ Serial read error: {e}")
                break

        ser.close()

    except Exception as e:
        print(f"❌ Serial Error: {e}")


async def ws_handler(websocket):
    connected_clients.add(websocket)
    print("🌐 Oki Web App connected.")

    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print("🌐 Oki Web App disconnected.")


async def main():
    print("🌐 Starting WebSocket server on port 8765...")
    async with websockets.serve(ws_handler, "0.0.0.0", 8765):
        await rfid_reader()
