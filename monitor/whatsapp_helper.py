import requests
import re
from django.conf import settings

def send_wa_notification(nomor_wa, message):
    """
    Sends WhatsApp notification using the local Baileys Node.js gateway.
    URL endpoint is fetched from Django settings.WA_GATEWAY_URL.
    """
    # Fallback to local gateway if not specified
    gateway_url = getattr(settings, 'WA_GATEWAY_URL', 'http://127.0.0.1:3000/send')

    if not nomor_wa:
        print("[WA HELPER] No recipient WhatsApp number provided.")
        return False

    # Clean the number (remove non-digits)
    clean_number = re.sub(r'\D', '', nomor_wa)
    if not clean_number:
        print(f"[WA HELPER] Recipient number '{nomor_wa}' is invalid after cleaning.")
        return False

    # Normalize local Indonesian numbers starting with '0' to '62'
    if clean_number.startswith('0'):
        clean_number = '62' + clean_number[1:]

    payload = {
        'number': clean_number,
        'message': message
    }

    print(f"[WA HELPER] Sending POST to {gateway_url} for {clean_number}...")

    try:
        response = requests.post(gateway_url, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result.get('status') is True:
            print(f"[WA HELPER] Message successfully sent to {clean_number}!")
            return True
        else:
            print(f"[WA HELPER] Gateway returned error: {result.get('message', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[WA HELPER] Connection to WA Gateway failed: {e}")
        print("[WA HELPER] Tip: Make sure the Node.js app in 'whatsapp_gateway' is running!")
        return False
    except Exception as e:
        print(f"[WA HELPER] Unexpected error: {e}")
        return False
