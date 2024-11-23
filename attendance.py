from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

id = os.getenv("regn")
pwd = os.getenv("pwd")
url1 = os.getenv("login_url")
url2 = os.getenv("attendacnce_url")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://nitjsr.vercel.app"}})

def att(regn):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Use headless Chromium
        context = browser.new_context()
        page = context.new_page()
        page.goto(url1)

        # Login
        page.fill('#txtuser_id', id)
        page.fill('#txtpassword', pwd)
        page.click('#btnsubmit')
        page.wait_for_url(lambda url: url != url1)

        # Navigate to attendance page
        page.goto(url2)
        page.wait_for_selector('#ContentPlaceHolder1_ddlroll')

        # Enable and select registration number
        page.evaluate("""
            const select = document.querySelector('#ContentPlaceHolder1_ddlroll');
            const optionToSelect = Array.from(select.options).find(option => option.value === arguments[0]);
            if (optionToSelect) {
                select.disabled = false;
                optionToSelect.selected = true;
                select.dispatchEvent(new Event('change'));
            }
        """, regn)

        page.wait_for_timeout(2000)  # Allow data to load

        # Scrape attendance table
        attendance_table = page.query_selector('#ContentPlaceHolder1_gv')
        attendance = []

        if attendance_table:
            rows = attendance_table.query_selector_all('tr')
            for row in rows:
                cells = row.query_selector_all('td') or row.query_selector_all('th')
                row_data = [cell.inner_text() for cell in cells]
                attendance.append(row_data)

        browser.close()
        return attendance

@app.route('/get_attendance', methods=['POST'])
def get_attendance():
    try:
        data = request.json
        regn = data.get('regn')
        if not regn:
            return jsonify({'error': 'Registration number is required'}), 400
        attendance = att(regn)
        return jsonify({'status': 'success', 'attendance': attendance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
