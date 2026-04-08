from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client
from datetime import datetime
import calendar
import json
import time
import os

# =========================================================
# CONFIG
# =========================================================
URL = "https://tgepass.cgg.gov.in/HomeServicePostmatricKnowApplication"

# Secrets from GitHub
APPLICATION_NUMBER = os.getenv("APPLICATION_NUMBER")
YEAR_VALUE = "2021-22"

# Twilio Secrets
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TO_WHATSAPP = os.getenv("TO_WHATSAPP")
FROM_WHATSAPP = "whatsapp:+14155238886"

STATUS_FILE = "status.json"

# =========================================================
# WHATSAPP ALERT FUNCTION
# =========================================================
def send_whatsapp(message):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    print("Sending WhatsApp Alert:", message)
    client.messages.create(
        from_=FROM_WHATSAPP,
        body=message,
        to=TO_WHATSAPP
    )

# =========================================================
# CHECK MONTH END
# =========================================================
def is_month_end():
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return True

# =========================================================
# SAVE STATUS
# =========================================================
def update_status(found):
    data = {
        "last_checked": str(datetime.now()),
        "found": found
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)

# =========================================================
# SCRAPER (HEADLESS SELENIUM)
# =========================================================
def check_status():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use GitHub Actions Chromium
    options.binary_location = "/usr/bin/chromium-browser"

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(URL)

        # Select Year
        Select(wait.until(
            EC.presence_of_element_located((By.ID, "ac_year"))
        )).select_by_value(YEAR_VALUE)

        # Enter Application Number
        app_input = wait.until(
            EC.presence_of_element_located((By.ID, "applId"))
        )
        app_input.clear()
        app_input.send_keys(APPLICATION_NUMBER)

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # Wait for results table
        wait.until(
            EC.presence_of_element_located(
                (By.ID, "datatable-totals-withoutfooter_A4_new")
            )
        )

        time.sleep(2)

        # Extract Bank Remitted Date
        try:
            bank_date = driver.find_element(
                By.XPATH,
                "//td[contains(text(),'Bank Remitted Date')]/b"
            ).text.strip()
        except:
            bank_date = ""

        print("Bank Remitted Date:", bank_date)
        return bank_date

    except Exception as e:
        print("Error:", e)
        return ""

    finally:
        driver.quit()

# =========================================================
# MAIN LOGIC
# =========================================================
def main():
    if not ACCOUNT_SID or not AUTH_TOKEN or not TO_WHATSAPP or not APPLICATION_NUMBER:
        print("Missing required secrets")
        return

    bank_date = check_status()

    if bank_date and bank_date.strip():
        message = f"Bank Remitted Date Generated: {bank_date}"
        send_whatsapp(message)
        update_status(True)
    else:
        print("No remitted date yet")
        update_status(False)
        if is_month_end():
            message = "Checked this month: No Bank Remitted Date generated"
            send_whatsapp(message)

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    main()
