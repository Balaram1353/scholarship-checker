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
import calendar

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
def update_status(found, bank_date=""):
    data = {
        "last_checked": str(datetime.now()),
        "found": found,
        "bank_date": bank_date
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
    wait = WebDriverWait(driver, 30)

    try:
        print(f"Opening URL: {URL}")
        driver.get(URL)

        # Select Year
        Select(wait.until(EC.presence_of_element_located((By.ID, "ac_year")))).select_by_value(YEAR_VALUE)

        # Enter Application Number
        app_input = wait.until(EC.presence_of_element_located((By.ID, "applId")))
        app_input.clear()
        app_input.send_keys(APPLICATION_NUMBER)

        # Submit
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Wait for results table
        wait.until(EC.presence_of_element_located((By.ID, "datatable-totals-withoutfooter_A4_new")))
        time.sleep(2)

        # Extract Bank Remitted Date
        bank_date = ""
        try:
            bank_date = driver.find_element(By.XPATH, "//td[contains(text(),'Bank Remitted Date')]/b").text.strip()
        except:
            # fallback
            tds = driver.find_elements(By.TAG_NAME, "td")
            for td in tds:
                if "Bank Remitted Date" in td.text:
                    b_tags = td.find_elements(By.TAG_NAME, "b")
                    if b_tags:
                        bank_date = b_tags[-1].text.strip()
                        break

        print("Bank Remitted Date:", bank_date if bank_date else "Not found")
        return bank_date

    except Exception as e:
        print("Scraper error:", e)
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

    # Check secrets
    if not all([ACCOUNT_SID, AUTH_TOKEN, TO_WHATSAPP, APPLICATION_NUMBER]):
        print("ERROR: One or more required secrets are missing.")
        raise SystemExit(1)

    bank_date = check_status()

    if bank_date:
        # Bank Remitted Date FOUND → send WhatsApp alert and stop retries
        message = (
            f"TGEPASS Scholarship Alert\n"
            f"Application: {APPLICATION_NUMBER}\n"
            f"Bank Remitted Date: {bank_date}\n"
            f"Checked at: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}"
        )
        send_whatsapp(message)
        update_status(True, bank_date)
        raise SystemExit(0)  # SUCCESS

    else:
        print("No Bank Remitted Date yet.")
        update_status(False)

        # Check if today is month-end
        today = datetime.now()
        last_day = calendar.monthrange(today.year, today.month)[1]
        if today.day == last_day:
            send_whatsapp("Checked this month: No Bank Remitted Date generated")

        raise SystemExit(1)  # triggers retry in GitHub Actions

if __name__ == "__main__":
    main()
