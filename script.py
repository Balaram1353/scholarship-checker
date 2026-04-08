from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client
from datetime import datetime
import json
import time
import os

# =========================================================
# CONFIG
# =========================================================
URL = "https://tgepass.cgg.gov.in/HomeServicePostmatricKnowApplication"

APPLICATION_NUMBER = os.getenv("APPLICATION_NUMBER")
YEAR_VALUE = "2021-22"

ACCOUNT_SID   = os.getenv("ACCOUNT_SID")
AUTH_TOKEN    = os.getenv("AUTH_TOKEN")
TO_WHATSAPP   = os.getenv("TO_WHATSAPP")
FROM_WHATSAPP = "whatsapp:+14155238886"

STATUS_FILE = "status.json"

# =========================================================
# WHATSAPP ALERT
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
# SAVE STATUS
# =========================================================
def update_status(found):
    data = {
        "last_checked": str(datetime.now()),
        "found": found
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)
    print("Status saved:", data)

# =========================================================
# SCRAPER
# =========================================================
def check_status():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = "/usr/bin/google-chrome"

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        print(f"Opening URL: {URL}")
        driver.get(URL)

        print(f"Selecting year: {YEAR_VALUE}")
        Select(wait.until(
            EC.presence_of_element_located((By.ID, "ac_year"))
        )).select_by_value(YEAR_VALUE)

        print(f"Entering application number: {APPLICATION_NUMBER}")
        app_input = wait.until(
            EC.presence_of_element_located((By.ID, "applId"))
        )
        app_input.clear()
        app_input.send_keys(APPLICATION_NUMBER)

        print("Clicking submit...")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        print("Waiting for results table...")
        wait.until(
            EC.presence_of_element_located(
                (By.ID, "datatable-totals-withoutfooter_A4_new")
            )
        )

        time.sleep(2)

        try:
            bank_date = driver.find_element(
                By.XPATH,
                "//td[contains(text(),'Bank Remitted Date')]/b"
            ).text.strip()
        except:
            bank_date = ""

        print("Bank Remitted Date:", bank_date if bank_date else "Not found")
        return bank_date

    except Exception as e:
        print(f"Scraper error: {e}")
        try:
            driver.save_screenshot("error_screenshot.png")
        except:
            pass
        return ""

    finally:
        driver.quit()

# =========================================================
# MAIN
# =========================================================
def main():
    print("=" * 50)
    print(f"Run started at: {datetime.now()}")
    print("=" * 50)

    if not all([ACCOUNT_SID, AUTH_TOKEN, TO_WHATSAPP, APPLICATION_NUMBER]):
        print("ERROR: One or more required secrets are missing.")
        print(f"  ACCOUNT_SID       : {'SET' if ACCOUNT_SID else 'MISSING'}")
        print(f"  AUTH_TOKEN        : {'SET' if AUTH_TOKEN else 'MISSING'}")
        print(f"  TO_WHATSAPP       : {'SET' if TO_WHATSAPP else 'MISSING'}")
        print(f"  APPLICATION_NUMBER: {'SET' if APPLICATION_NUMBER else 'MISSING'}")
        raise SystemExit(1)

    bank_date = check_status()      # <-- THIS LINE, do not hardcode anything here

    if bank_date and bank_date.strip():
        print("Bank Remitted Date found!")
        message = (
            f"TGEPASS Scholarship Alert\n"
            f"Application: {APPLICATION_NUMBER}\n"
            f"Bank Remitted Date: {bank_date}\n"
            f"Checked at: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}"
        )
        send_whatsapp(message)
        update_status(True)
        raise SystemExit(0)    # date found - workflow stops all retries
    else:
        print("No Bank Remitted Date yet.")
        update_status(False)
        raise SystemExit(1)    # no date - workflow retries after 1 hour

if __name__ == "__main__":
    main()
