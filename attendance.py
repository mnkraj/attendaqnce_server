from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
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

GECKODRIVER_URL = "https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz"

def download_driver():
    """
    Download and extract geckodriver to /tmp directory for temporary use.
    """
    driver_tar_path = "/tmp/geckodriver.tar.gz"
    extracted_path = "/tmp/geckodriver"
    if not os.path.exists(extracted_path):
        print("Downloading geckodriver...")
        response = requests.get(GECKODRIVER_URL, stream=True)
        with open(driver_tar_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        shutil.unpack_archive(driver_tar_path, "/tmp/")
        os.chmod(extracted_path, 0o755)  # Make it executable
    return extracted_path

def wait_for_network_idle(driver, timeout=10):
    # Simplified for compatibility with Firefox
    time.sleep(timeout)

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

        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")

        driver_path = download_driver()
        service = Service(driver_path)  # Use the Service object to specify the path

        driver = webdriver.Firefox(service=service, options=firefox_options)  # Updated syntax

        attendance = att(driver, regn)
        driver.quit()

        return jsonify({'status': 'success', 'attendance': attendance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
