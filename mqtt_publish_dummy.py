"""
Script untuk mengirim dummy data MQTT ke broker untuk testing.
Gunakan: python mqtt_publish_dummy.py [api_key] [ph] [tds] [suhu]
Contoh: python mqtt_publish_dummy.py 00000 6.5 1200 28.5
"""

import paho.mqtt.publish as publish
import json
import sys

def send_mqtt_data(api_key, ph, tds, suhu):
    """Kirim data sensor ke MQTT broker"""
    topic = f"hydroponik/tanamanku/datasensor/{api_key}"
    payload = {
        "ph": float(ph),
        "tds": float(tds),
        "suhu": float(suhu)
    }
    
    try:
        publish.single(
            topic,
            payload=json.dumps(payload),
            hostname="broker.emqx.io",
            port=1883,
            retain=False
        )
        print(f"[OK] Data terkirim ke {topic}")
        print(f"  pH: {ph}, TDS: {tds}, Suhu: {suhu} C")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Penggunaan: python mqtt_publish_dummy.py <api_key> <ph> <tds> <suhu>")
        print("\nContoh:")
        print("  python mqtt_publish_dummy.py 00000 6.5 1200 28.5")
        print("  python mqtt_publish_dummy.py 00000 7.0 1500 25.0")
        sys.exit(1)
    
    api_key = sys.argv[1]
    ph = sys.argv[2]
    tds = sys.argv[3]
    suhu = sys.argv[4]
    
    send_mqtt_data(api_key, ph, tds, suhu)
