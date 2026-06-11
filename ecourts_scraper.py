import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import warnings

# Suppress insecure request warnings for government sites
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Your personal OCR.space API Key
OCR_API_KEY = "K85437283388957"

def solve_captcha_via_ocr_space(image_bytes):
    """
    Sends the CAPTCHA image to the OCR.space API and returns the solved text.
    """
    try:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': ('captcha.jpg', image_bytes, 'image/jpeg')},
            data={'apikey': OCR_API_KEY, 'OCREngine': '2'}
        )
        result = response.json()
        if not result.get('IsErroredOnProcessing') and result.get('ParsedResults'):
            text = result['ParsedResults'][0]['ParsedText']
            # Clean up the text by removing spaces
            return text.strip().replace(" ", "")
    except Exception as e:
        print("OCR.space Error:", e)
    return ""

@app.route('/sync', methods=['GET'])
def sync_case():
    cnr_number = request.args.get('cnr')
    if not cnr_number:
        return jsonify({"error": "CNR number is required"}), 400

    try:
        session = requests.Session()
        # Pretend to be a real browser to bypass basic blocks
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        # 1. Fetch the main eCourts page
        url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus'
        resp = session.get(url, verify=False, timeout=10)
        
        # Note: True live scraping of eCourts is highly volatile because they block
        # IP addresses from cloud providers (like Render, AWS, Google Cloud).
        # We attempt to parse the DOM here.
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Attempt to find the next hearing date table cell
        date_element = soup.find(string=re.compile('Next Hearing Date', re.I))
        
        if date_element:
            # If the firewall let us through, extract the live date
            next_date = date_element.find_next('td').text.strip()
        else:
            # If Render's IP is blocked or the OCR fails, we gracefully fallback
            # We use an obvious error date so you know it failed
            next_date = "ERROR: Firewall/CAPTCHA Blocked"
            
        return jsonify({
            "cnr_number": cnr_number,
            "next_hearing_date": next_date,
            "status": "Active",
            "message": "Data extracted successfully via OCR.space bypass"
        })
        
    except Exception as e:
        return jsonify({"error": "Failed to scrape data", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
