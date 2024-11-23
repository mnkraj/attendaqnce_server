from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import time
from flask_cors import CORS




load_dotenv()

id = os.getenv("regn")
pwd = os.getenv("pwd")
url1 = os.getenv("login_url")
url2 = os.getenv("attendacnce_url")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://nitjsr.vercel.app"}})

def wait_for_network_idle(driver, timeout=10):
    driver.execute_cdp_cmd("Network.enable", {})
    inflight_requests = set()

    driver.execute_cdp_cmd("Runtime.evaluate", {
        "expression": """
        (() => {
            window.requests = new Set();
            window.onRequestSent = (req) => window.requests.add(req);
            window.onRequestFinished = (req) => window.requests.delete(req);
        })()
        """
    })

def att(driver, regn):
    driver.get(url1)
    WebDriverWait(driver, 100).until(
        EC.element_to_be_clickable((By.ID, "txtuser_id"))
    ).send_keys(id)
    WebDriverWait(driver, 100).until(
        EC.element_to_be_clickable((By.ID, "txtpassword"))
    ).send_keys(pwd)
    WebDriverWait(driver, 100).until(
        EC.element_to_be_clickable((By.ID, "btnsubmit"))
    ).click()
    WebDriverWait(driver, 100).until(
        lambda driver: driver.current_url != url1
    )
    driver.execute_script(f"window.location.href = '{url2}';")
    WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlroll"))
    )
    select_element = driver.find_element(By.ID, "ContentPlaceHolder1_ddlroll")
    driver.execute_script("arguments[0].removeAttribute('disabled');", select_element)
    driver.execute_script(
        f"""
        const select = document.querySelector('#ContentPlaceHolder1_ddlroll');
        const optionToSelect = Array.from(select.options).find(option => option.value === '{regn}');
        if (optionToSelect) {{
            optionToSelect.selected = true;
            select.dispatchEvent(new Event('change'));
        }}
        """
    )
    wait_for_network_idle(driver, 100)
    time.sleep(2)
    attendance_table = driver.find_element(By.ID, 'ContentPlaceHolder1_gv')
    attendance = []
    rows = attendance_table.find_elements(By.TAG_NAME, 'tr')
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        if not cells:
            cells = row.find_elements(By.TAG_NAME, 'th')
        row_data = [cell.text for cell in cells]
        attendance.append(row_data)
    return attendance

@app.route('/get_attendance', methods=['POST'])
def get_attendance():
    try:
        data = request.json
        regn = data.get('regn')
        if not regn:
            return jsonify({'error': 'Registration number is required'}), 400
        chrome_options = Options()
        chrome_options.page_load_strategy = "none"
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,10080")  
        chrome_options.add_argument("--disable-gpu")
        service = Service()  
        driver = webdriver.Chrome(service=service, options=chrome_options)
        attendance = att(driver, regn)
        driver.quit()
        return jsonify({'status': 'success', 'attendance': attendance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
