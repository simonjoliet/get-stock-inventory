import time
import sys
import re
import html
import argparse
import configparser
import glob
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
            "username": config.get("adobe", "username")
        }
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

    time.sleep(5)

def login_adobe(driver, creds):
    log("Opening Adobe login page...")
    driver.get(ADOBE_URL.format(page=1))
    time.sleep(3)

    driver.find_element(By.CSS_SELECTOR, '[data-social-provider="Google"]').click()
    time.sleep(3)

    email_input = driver.find_element(By.ID, "identifierId")
    email_input.send_keys(creds["username"])
    email_input.send_keys("\n")

    log("\nComplete Google login (password, 2FA, etc.), then press ENTER...\n")
    input()

def is_next_disabled(driver):
    try:
        btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="next page"]')

        # Direct disabled attribute
        if btn.get_attribute("disabled") is not None:
            return True

        # CSS class fallback (Material UI style)
        classes = btn.get_attribute("class") or ""
        if "Mui-disabled" in classes:
            return True

    except Exception:
        pass

    return False

def extract_adobe(content):
    pattern = r'%22%2C%22original_name%22%3A%22(.*?)%22%2C%22.*?F220_F_(.*?)_.*?title%22%3A%22(.*?)%22%2C%22'
    matches = re.findall(pattern, content)

    for filename, asset_id, title in matches:
        print(f"Adobe,{filename},{asset_id},\"{unquote(title)}\"")

    return len(matches)

def extract_shutterstock(content):
    pattern = r'aria-label="select\ asset\ ([^"]+\.(?:jpg|JPG)).*?<img[^>]+src="[^"]*?-([0-9]{10})\.(?:jpg|JPG)[^"]*"[^>]+alt="([^"]+)"'

    matches = re.findall(pattern, content, re.DOTALL)

    for filename, asset_id, title in matches:
        print(f'Shutterstock,{filename},{asset_id},"{html.unescape(title)}"')

    return len(matches)

def run_scraper(driver, url_template, extractor, max_pages=None):
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            log("  └ Reached max page limit")
            break

        log(f"\nPage {page}")
        log("  ├ Downloading...")

        html_content = load_page(driver, url_template.format(page=page))

        log("  └ Extracting...")
        count = extractor(html_content)

        # If no items found, stop
        if count == 0:
            log("   x No items found: last page reached")
            break

        if is_next_disabled(driver):
            log("   x Next button disabled: last page reached")
            break

        page += 1
        time.sleep(DELAY)

def parse_files(file_patterns, extractor):
    files = []
    for pattern in file_patterns:
        files.extend(glob.glob(pattern))

    if not files:
        raise Exception("No files matched input patterns")

    for file in sorted(files):
        log(f"Processing file: {file}")
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        extractor(content)

def run_from_files(args):
    if args.adobe:
        parse_files(args.file, extract_adobe)
    elif args.shutterstock:
        parse_files(args.file, extract_shutterstock)

def main():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--adobe", action="store_true")
    group.add_argument("--shutterstock", action="store_true")

    parser.add_argument("--page", type=int, default=None,
                        help="Max number of pages to fetch")

    parser.add_argument("--file", nargs="+", default=None,
                        help="HTML file(s) to parse instead of scraping")

    args = parser.parse_args()

    print("platform,filename,asset_id,title")

    if args.file:
        run_from_files(args)
        log("\nDone (file mode)")
        return

    creds = load_credentials()
    driver = create_driver()

    if args.shutterstock:
        login_shutterstock(driver, creds["shutterstock"])
        run_scraper(driver, SHUTTER_URL, extract_shutterstock, max_pages=args.page)

    elif args.adobe:
        login_adobe(driver, creds["adobe"])
        run_scraper(driver, ADOBE_URL, extract_adobe, max_pages=args.page)

    driver.quit()
    log("\nDone.")

if __name__ == "__main__":
    main()