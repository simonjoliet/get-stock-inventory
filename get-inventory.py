import argparse
import glob
import html
import importlib.util
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

def load_stock_logins_module():
    module_path = Path(__file__).with_name("stock-logins.py")
    spec = importlib.util.spec_from_file_location("stock_logins_runtime", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

stock_logins = load_stock_logins_module()

def log(msg):
    print(msg, file=sys.stderr, flush=True)

def load_page(driver, url, app_config):
    scraping = app_config["scraping"]

    for attempt in range(1, scraping["max_retries"] + 1):
        try:
            driver.get(url)
            time.sleep(scraping["page_load_wait_seconds"])
            return driver.page_source
        except WebDriverException as e:
            log(f"  retry {attempt}/{scraping['max_retries']} failed: {e}")
            time.sleep(scraping["retry_delay_seconds"])

    raise Exception(f"Failed to load {url}")

def is_next_disabled(driver):
    try:
        btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="next page"]')
        if btn.get_attribute("disabled") is not None:
            return True

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
        print(f'Adobe,{filename},{asset_id},"{unquote(title)}"')

    return len(matches)

def extract_shutterstock(content):
    pattern = r'aria-label="select\ asset\ ([^"]+\.(?:jpg|JPG)).*?<img[^>]+src="[^"]*?-([0-9]{10})\.(?:jpg|JPG)[^"]*"[^>]+alt="([^"]+)"'
    matches = re.findall(pattern, content, re.DOTALL)

    for filename, asset_id, title in matches:
        print(f'Shutterstock,{filename},{asset_id},"{html.unescape(title)}"')

    return len(matches)

def run_scraper(driver, url_template, extractor, app_config, max_pages=None):
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            log("  └ Reached max page limit")
            break

        log(f"\nPage {page}")
        log("  ├ Downloading...")

        html_content = load_page(driver, url_template.format(page=page), app_config)

        log("  └ Extracting...")
        count = extractor(html_content)

        if count == 0:
            log("   x No items found: last page reached")
            break

        if is_next_disabled(driver):
            log("   x Next button disabled: last page reached")
            break

        page += 1
        time.sleep(app_config["scraping"]["page_delay_seconds"])

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

    parser.add_argument("--page", type=int, default=None, help="Max number of pages to fetch")
    parser.add_argument(
        "--file",
        nargs="+",
        default=None,
        help="HTML file(s) to parse instead of scraping",
    )

    args = parser.parse_args()

    print("platform,filename,asset_id,title")

    if args.file:
        run_from_files(args)
        log("\nDone (file mode)")
        return

    app_config = stock_logins.load_config()
    driver = stock_logins.create_driver(app_config)

    if args.shutterstock:
        stock_logins.login_shutterstock(driver, app_config, log)
        run_scraper(
            driver,
            app_config["shutterstock"]["portfolio_url"],
            extract_shutterstock,
            app_config,
            max_pages=args.page,
        )
    elif args.adobe:
        stock_logins.login_adobe(driver, app_config, log)
        run_scraper(
            driver,
            app_config["adobe"]["portfolio_url"],
            extract_adobe,
            app_config,
            max_pages=args.page,
        )

    driver.quit()
    log("\nDone.")

if __name__ == "__main__":
    main()