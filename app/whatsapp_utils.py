import requests
import json
from flask import current_app

def send_whatsapp_message(to, message):
    """
    Sends a WhatsApp message using the Meta Business API.
    'to' should be a phone number in international format (e.g., 573101234567).
    'message' is the text content to be sent.
    """
    try:
        token = current_app.config['WHATSAPP_ACCESS_TOKEN']
        phone_number_id = current_app.config['WHATSAPP_PHONE_NUMBER_ID']
        
        url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            current_app.logger.info(f"WhatsApp message sent to {to}. Response: {response.json()}")
            return True, response.json()
        else:
            current_app.logger.error(f"Failed to send WhatsApp message to {to}. Status: {response.status_code}, Response: {response.text}")
            return False, response.json()
            
    except Exception as e:
        current_app.logger.error(f"An exception occurred while sending WhatsApp message: {e}")
        return False, {"error": str(e)}
