import paho.mqtt.client as mqtt
import json, os, django, time
from datetime import datetime, timedelta

# Django Connection setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.utils import timezone
from monitor.models import Rak, DataSensor
from monitor.whatsapp_helper import send_wa_notification

BROKER_ADDRESS = "broker.emqx.io"
BROKER_PORT = 1883
SUBSCRIBE_TOPIC = "hydroponik/tanamanku/datasensor/+"

def on_connect(client, userdata, flags, rc):
    """Called when the client receives a CONNECT response from the server."""
    if rc == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Connected to MQTT Broker: {BROKER_ADDRESS}")
        client.subscribe(SUBSCRIBE_TOPIC)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Subscribed to topic: {SUBSCRIBE_TOPIC}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Connection failed with code: {rc}")

def on_disconnect(client, userdata, rc):
    """Called when the client disconnects from the broker."""
    if rc != 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARNING] Disconnected unexpectedly. Code: {rc}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Disconnected from broker")

def on_subscribe(client, userdata, mid, granted_qos):
    """Called when SUBACK is received from the server."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Subscription successful (QoS: {granted_qos})")

def on_log(client, userdata, level, buf):
    """Log handler for debugging"""
    if level > 16:  # Skip info level logs
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [LOG] {buf}")

def on_message(client, userdata, msg):
    """Called when a PUBLISH message is received from the server."""
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        # Ambil API Key dari topik: hydroponik/tanamanku/datasensor/ABC-123
        api_key = msg.topic.split('/')[-1]
        payload = json.loads(msg.payload.decode())
        
        # Validasi field yang diperlukan
        required_fields = ['ph', 'tds', 'suhu']
        if not all(field in payload for field in required_fields):
            raise ValueError(f"Required fields: {', '.join(required_fields)}")
        
        # Cari rak berdasarkan API Key
        raks = Rak.objects.filter(api_key__api_key=api_key)
        if not raks.exists():
            raise Rak.DoesNotExist()
        
        for rak in raks:
            ph_val = float(payload['ph'])
            tds_val = float(payload['tds'])
            suhu_val = float(payload['suhu'])

            # Simpan data ke database
            DataSensor.objects.create(
                rak=rak,
                ph=ph_val,
                tds=tds_val,
                suhu=suhu_val
            )
            
            print(f"[{timestamp}] [OK] Data entry stored for '{rak.nama_rak}'")
            print(f"           pH: {ph_val} | TDS: {tds_val} | Suhu: {suhu_val} C")

            # Early Warning System (EWS) Alert Logic
            is_emergency = False
            reasons = []
            
            if ph_val < rak.min_ph:
                is_emergency = True
                reasons.append(f"pH air ({ph_val:.1f}) di bawah batas minimum ideal ({rak.min_ph:.1f})")
            elif ph_val > rak.max_ph:
                is_emergency = True
                reasons.append(f"pH air ({ph_val:.1f}) melebihi batas maksimum ideal ({rak.max_ph:.1f})")
                
            if is_emergency:
                now = timezone.now()
                cooldown_minutes = 30
                cooldown_time = now - timedelta(minutes=cooldown_minutes)
                
                # Check if cooldown has elapsed
                if rak.last_notification_sent is None or rak.last_notification_sent < cooldown_time:
                    # Construct WhatsApp message
                    message = (
                        f"🚨 *PERINGATAN DARURAT HIDROPONIK* 🚨\n\n"
                        f"Sistem Early Warning mendeteksi kondisi tidak ideal pada:\n"
                        f"📍 *Rak:* {rak.nama_rak}\n"
                        f"🌱 *Tanaman:* {rak.tanaman.nama if rak.tanaman else '-'}\n\n"
                        f"⚠️ *Keterangan:* {', '.join(reasons)}\n"
                        f"📊 *Detail Sensor Saat Ini:*\n"
                        f"  - pH: {ph_val:.1f} (Batas Ideal: {rak.min_ph} - {rak.max_ph})\n"
                        f"  - TDS: {tds_val:.0f} PPM\n"
                        f"  - Suhu: {suhu_val:.1f}°C\n\n"
                        f"Silakan lakukan pengecekan pada larutan nutrisi segera.\n"
                        f"Waktu: {now.strftime('%d-%m-%Y %H:%M:%S')}"
                    )
                    
                    # Try sending the message
                    sent = send_wa_notification(rak.nomor_wa, message)
                    if sent:
                        rak.last_notification_sent = now
                        rak.save(update_fields=['last_notification_sent'])
                        print(f"[{timestamp}] [ALERT] Emergency WhatsApp sent to {rak.nomor_wa} for '{rak.nama_rak}'")
                    else:
                        print(f"[{timestamp}] [ALERT] Failed to send emergency WhatsApp to {rak.nomor_wa}")

        
    except Rak.DoesNotExist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] API Key not found: {api_key}")
    except json.JSONDecodeError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Invalid JSON payload: {msg.payload}")
    except ValueError as ve:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {ve}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {e}")

def main():
    print("=" * 60)
    print("MQTT Data Handler - Hidroponik Monitor")
    print("=" * 60)
    print(f"Broker: {BROKER_ADDRESS}:{BROKER_PORT}")
    print(f"Subscribe: {SUBSCRIBE_TOPIC}")
    print("=" * 60)
    print("Waiting for data from ESP32...\n")
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_log = on_log
    
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n[Keyboard Interrupt] Stopping MQTT handler...")
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Attempting to reconnect in 5 seconds...")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
