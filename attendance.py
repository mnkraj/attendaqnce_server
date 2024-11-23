from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import shutil
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from dotenv import load_dotenv

load_dotenv()

id = os.getenv("regn")
pwd = os.getenv("pwd")
url1 = os.getenv("login_url")
url2 = os.getenv("attendance_url")

app = Flask(__name__)
CORS(app)

CHROMEDRIVER_URL = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"

def download_driver():
    """
    Download and extract ChromeDriver to /tmp directory for temporary use.
    """
    driver_zip_path = "/tmp/chromedriver.zip"
    extracted_path = "/tmp/chromedriver"
    if not os.path.exists(extracted_path):
        print("Downloading ChromeDriver...")
        response = requests.get(CHROMEDRIVER_URL, stream=True)
        with open(driver_zip_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        shutil.unpack_archive(driver_zip_path, "/tmp/")
        os.chmod(extracted_path, 0o755)  # Make it executable
    return extracted_path

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
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.binary_location = "/usr/bin/google-chrome"  # Change if bundling Chrome manually

        driver_path = download_driver()
        service = Service(driver_path)  # Use the Service object to specify the path

        driver = webdriver.Chrome(service=service, options=chrome_options)  # Updated syntax

        attendance = att(driver, regn)
        driver.quit()

        return jsonify({'status': 'success', 'attendance': attendance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
