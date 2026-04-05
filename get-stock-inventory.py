import time
import sys
import re
import html
import argparse
import configparser
from urllib.parse import unquote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

ADOBE_URL = "https://contributor.stock.adobe.com/en/portfolio?limit=100&page={page}&sort_by=create_desc"
SHUTTER_URL = "https://submit.shutterstock.com/portfolio/published/photo?sortOrder=newest&page={page}"

MAX_RETRIES = 3
DELAY = 2

def log(msg):
    print(msg, file=sys.stderr, flush=True)

def load_credentials():
    config = configparser.ConfigParser()
    config.read("credentials.ini")

    return {
        "shutterstock": {
            "username": config.get("shutterstock", "username"),
            "password": config.get("shutterstock", "password"),
        },
        "adobe": {
            "username": config.get("adobe", "username")        }
    }

def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)

def load_page(driver, url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(url)
            time.sleep(3)
            return driver.page_source
        except WebDriverException as e:
            log(f"  retry {attempt}/{MAX_RETRIES} failed: {e}")
            time.sleep(2)
    raise Exception(f"Failed to load {url}")

def login_shutterstock(driver, creds):

    driver.get(SHUTTER_URL)
    time.sleep(3)

    log("  ├ Filling username...")
    driver.find_element(By.CSS_SELECTOR, '[data-test-id="email-input"]').send_keys(creds["username"])

    log("  ├ Filling password...")
    driver.find_element(By.CSS_SELECTOR, '[data-test-id="password-input"]').send_keys(creds["password"])

    log("  └ Submitting login...")
    driver.find_element(By.CSS_SELECTOR, '[data-test-id="login-form-submit-button"]').click()

    # Wait for redirect / dashboard load
    time.sleep(5)

def login_adobe(driver, creds):
    log("Opening Adobe login page...")
    driver.get(ADOBE_URL.format(page=1))
    time.sleep(3)

    log("  ├ Clicking 'Continue with Google'...")

    # Click the Google sign-in button
    driver.find_element(
        By.CSS_SELECTOR,
        '[data-social-provider="Google"]'
    ).click()

    time.sleep(3)

    log("  ├ Filling Google email...")

    # Switch to email input (Google login page)
    email_input = driver.find_element(By.ID, "identifierId")
    email_input.send_keys(creds["username"])

    log("  └ Submitting email...")

    email_input.send_keys("\n")  # press Enter

    # Wait for manual interaction (password / 2FA)
    log("\nComplete Google login (password, 2FA, etc.), then press ENTER...\n")
    input()

def extract_adobe(content):
    pattern = r'%22%2C%22original_name%22%3A%22(.*?)%22%2C%22.*?F220_F_(.*?)_.*?title%22%3A%22(.*?)%22%2C%22'
    matches = re.findall(pattern, content)

    for filename, asset_id, title in matches:
        print(f"Adobe Stock,{filename},{asset_id},\"{unquote(title)}\"")

    return len(matches)


def extract_shutterstock(content):
    img_pattern = r'<img[^>]+src="[^"]*?-([0-9]{10})\.(?:jpg|JPG)[^"]*"[^>]+alt="([^"]+)"'
    imgs = re.findall(img_pattern, content)

    file_pattern = r'([0-9]{10}\s-\s[^<"]+?\.(?:jpg|JPG))'
    filenames = re.findall(file_pattern, content)

    count = min(len(imgs), len(filenames))

    for i in range(count):
        asset_id, title = imgs[i]
        filename = filenames[i].strip()

        print(f"Shutterstock,{filename},{asset_id},\"{html.unescape(title)}\"")

    return count

def run_adobe(driver):
    page = 1

    while True:
        log(f"\nPage {page}")
        log("  ├ Downloading...")
        html_content = load_page(driver, ADOBE_URL.format(page=page))

        log("  └ Extracting...")
        count = extract_adobe(html_content)

        if count == 0:
            log("  └ No more items")
            break

        page += 1
        time.sleep(DELAY)

def run_shutterstock(driver):
    page = 1

    while True:
        log(f"\nPage {page}")
        log("  ├ Downloading...")
        html_content = load_page(driver, SHUTTER_URL.format(page=page))

        log("  └ Extracting...")
        count = extract_shutterstock(html_content)

        if "No items" in html_content or count == 0:
            log("  └ No more items")
            break

        page += 1
        time.sleep(DELAY)

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--adobe", action="store_true")
    group.add_argument("--shutterstock", action="store_true")

    args = parser.parse_args()

    creds = load_credentials()
    driver = create_driver()

    # CSV header
    print("platform,filename,asset_id,title")

    if args.shutterstock:
        login_shutterstock(driver, creds["shutterstock"])
        run_shutterstock(driver)

    elif args.adobe:
        login_adobe(driver, creds["adobe"])
        run_adobe(driver)

    driver.quit()
    log("\nDone.")


if __name__ == "__main__":
    main()