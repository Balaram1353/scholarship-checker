from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client
from datetime import datetime
import calendar
import json
import time

# =========================================================
# 🔧 CONFIG (FILL THESE)
# =========================================================
URL = "https://tgepass.cgg.gov.in/HomeServicePostmatricKnowApplication"
APPLICATION_NUMBER = ""
YEAR_VALUE = "2021-22"

# Twilio Credentials
ACCOUNT_SID = ""
AUTH_TOKEN = ""

# WhatsApp numbers
FROM_WHATSAPP = "whatsapp:+14155238886"   # Twilio sandbox number
TO_WHATSAPP = "whatsapp:+91"    # Your number

STATUS_FILE = "status.json"

# =========================================================
#  WHATSAPP ALERT FUNCTION (TWILIO)
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
#  CHECK IF MONTH END
# =========================================================
def is_month_end():
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day

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
# SCRAPE WEBSITE
# =========================================================
def check_status():
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(URL)

    wait = WebDriverWait(driver, 15)

    try:
        # 1. Select Year
        Select(wait.until(
            EC.presence_of_element_located((By.ID, "ac_year"))
        )).select_by_value(YEAR_VALUE)

        # 2. Enter Application Number
        app_input = wait.until(
            EC.presence_of_element_located((By.ID, "applId"))
        )
        app_input.clear()
        app_input.send_keys(APPLICATION_NUMBER)

        # 3. Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # 4. Wait for result page
        wait.until(
            EC.presence_of_element_located(
                (By.ID, "datatable-totals-withoutfooter_A4_new")
            )
        )

        time.sleep(2)

        # 5. Extract Bank Remitted Date
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
    bank_date = check_status()

    if bank_date:
        # Found → send alert immediately
        message = f"Bank Remitted Date Generated: {bank_date}"
        send_whatsapp(message)
        update_status(True)

    else:
        print("No remitted date yet")
        update_status(False)

        # Month-end message
        if is_month_end():
            message = "⚠️ Checked this month: No Bank Remitted Date generated"
            send_whatsapp(message)

# =========================================================
# RUN SCRIPT
# =========================================================
if __name__ == "__main__":
    main()
