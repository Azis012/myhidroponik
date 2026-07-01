# MQTT Setup & Testing Guide

## Deskripsi
Sistem ini menggunakan MQTT untuk menerima data sensor dari ESP32. Data sensor (pH, TDS, Suhu) dikirim oleh ESP32 dan disimpan ke database melalui MQTT broker.

## Broker MQTT
- **Host**: broker.emqx.io
- **Port**: 1883
- **Protocol**: MQTT (tidak terenkripsi)

## Topic Structure
```
hidroponik/data/{API_KEY}
```
Contoh: `hidroponik/data/00000`

## Payload Format
```json
{
  "ph": 6.5,
  "tds": 1200,
  "suhu": 28.5
}
```

## Cara Menjalankan MQTT Handler

### 1. Terminal 1: Jalankan MQTT Handler (Receiver)
```bash
cd c:\Users\ahmad\OneDrive\Documents\hidroponik_project
python mqtt_handler_new.py
```

Output yang diharapkan:
```
============================================================
MQTT Data Handler - Hidroponik Monitor
============================================================
Broker: broker.emqx.io:1883
Subscribe: hidroponik/data/+
============================================================
Menunggu data dari ESP32...

[HH:MM:SS] ✓ Terhubung ke MQTT Broker: broker.emqx.io
[HH:MM:SS] Subscribe ke topik: hidroponik/data/+
```

### 2. Terminal 2: Publish Dummy Data (Testing)
Gunakan script `mqtt_publish_dummy.py` untuk test:

```bash
python mqtt_publish_dummy.py {API_KEY} {pH} {TDS} {SUHU}
```

Contoh:
```bash
python mqtt_publish_dummy.py 00000 6.5 1200 28.5
python mqtt_publish_dummy.py 00000 7.2 1500 27.3
python mqtt_publish_dummy.py 00000 6.8 1300 28.0
```

### 3. Refresh Browser
Setelah mengirim data MQTT, refresh halaman di browser untuk melihat data sensor terbaru di kartu Rak.

---

## ESP32 Configuration

Untuk implementasi di ESP32, gunakan format berikut:

```cpp
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* mqtt_server = "broker.emqx.io";
const char* mqtt_topic = "hidroponik/data/00000"; // Ganti dengan API Key
const int mqtt_port = 1883;

void publishData(float ph, float tds, float suhu) {
  StaticJsonDocument<256> doc;
  doc["ph"] = ph;
  doc["tds"] = tds;
  doc["suhu"] = suhu;
  
  char buffer[256];
  serializeJson(doc, buffer);
  
  client.publish(mqtt_topic, buffer);
}
```

---

## Troubleshooting

### Koneksi MQTT Gagal
- Pastikan internet terhubung
- Cek apakah broker.emqx.io bisa diakses
- Gunakan command line untuk test: `telnet broker.emqx.io 1883`

### Data Tidak Muncul di Web
1. Pastikan `mqtt_handler_new.py` sedang berjalan
2. Pastikan MQTT handler menampilkan pesan "✓ Data masuk"
3. Refresh halaman di browser
4. Cek API Key di database harus cocok dengan topik yang dikirim

### Format JSON Error
- Pastikan payload menggunakan format JSON yang valid
- Harus ada 3 field: `ph`, `tds`, `suhu`
- Semua field harus bertipe angka (float)

---

## File-file yang Digunakan

| File | Fungsi |
|------|--------|
| `mqtt_handler_new.py` | Menerima data MQTT dan simpan ke DB |
| `mqtt_publish_dummy.py` | Mengirim dummy data untuk testing |
| `monitor/models.py` | Model DataSensor untuk menyimpan data |
| `monitor/views.py` | View untuk menampilkan data di halaman |
| `templates/rak_list.html` | Tampilan data sensor di kartu Rak |

---

## Live Testing Checklist

- [ ] MQTT Handler berjalan tanpa error
- [ ] Dummy data dapat dikirim
- [ ] Data muncul di terminal MQTT Handler
- [ ] Data muncul di database
- [ ] Data tampil di halaman web (setelah refresh)
