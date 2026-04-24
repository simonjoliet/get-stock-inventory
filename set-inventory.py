import argparse
import csv
import importlib.util
import sys
import time
from pathlib import Path
from urllib.parse import quote

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def load_stock_logins_module():
    module_path = Path(__file__).with_name("stock-logins.py")
    spec = importlib.util.spec_from_file_location("stock_logins_runtime", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

stock_logins = load_stock_logins_module()

def log(msg):
    print(msg, file=sys.stderr, flush=True)

def wait_for_visible_css(driver, selector, timeout):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )

def wait_for_all_visible_css(driver, selector, timeout):
    return WebDriverWait(driver, timeout).until(
        lambda d: [el for el in d.find_elements(By.CSS_SELECTOR, selector) if el.is_displayed()]
    )

def set_input_value(driver, element, value):
    driver.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];
        let descriptor = null;
        if (element instanceof window.HTMLInputElement) {
            descriptor = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype,
                "value"
            );
        } else if (element instanceof window.HTMLTextAreaElement) {
            descriptor = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                "value"
            );
        }
        if (descriptor && descriptor.set) {
            descriptor.set.call(element, value);
        } else {
            element.value = value;
        }
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
        """,
        element,
        str(value),
    )


def get_input_value(driver, element):
    return driver.execute_script("return arguments[0].value;", element)


def set_input_value_with_verification(driver, element, value, attempts=3):
    expected = str(value)

    for _ in range(attempts):
        set_input_value(driver, element, expected)
        element.send_keys(Keys.SPACE, Keys.BACKSPACE)
        if get_input_value(driver, element) == expected:
            return True

    return False


def adobe_title_already_matches(driver, expected_title):
    expected = str(expected_title)
    cells = driver.find_elements(By.CLASS_NAME, "container-table-cell")

    for cell in cells:
        if not cell.is_displayed():
            continue

        cell_text = driver.execute_script(
            "return arguments[0].textContent;", cell
        )
        if cell_text == expected:
            return True

    return False


def get_adobe_title_cell(driver):
    visible_cells = [
        cell
        for cell in driver.find_elements(By.CLASS_NAME, "container-table-cell")
        if cell.is_displayed()
    ]

    if len(visible_cells) < 3:
        raise Exception("Could not find the third visible Adobe title cell")

    return visible_cells[2]


def click_adobe_title_edit_without_hover(driver, timeout):
    title_cell = get_adobe_title_cell(driver)
    pencil_selector = (
        'button.button.button--floating.editable__pencil.margin-left-small'
        '[data-t="portfolio-detail-panel-title-edit"]'
    )
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                title_cell,
            )
            clicked = driver.execute_script(
                """
                const selector = arguments[0];
                const cell = arguments[1];
                const pencil = document.querySelector(selector);
                if (pencil) {
                    pencil.click();
                    return true;
                }

                cell.click();
                return false;
                """,
                pencil_selector,
                title_cell,
            )
            if clicked:
                return
        except Exception as exc:
            last_error = exc

        time.sleep(0.3)

    if last_error is not None:
        raise last_error
    raise TimeoutException("Adobe title edit control was not clickable without hover")

def parse_csv(file_path):
    items = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            asset_id = row[0].strip()
            value = row[1].strip()
            if not asset_id or not value:
                continue
            if asset_id.lower() in {"asset_id", "id"} and value.lower() in {
                "title",
                "value",
                "inventory",
            }:
                continue
            items.append((asset_id, value))
    return items

def update_adobe_asset(driver, asset_id, title, app_config):
    log(f"\nProcessing asset {asset_id}")
    timeout = app_config["selenium"]["timeout_seconds"]
    settings = app_config["set_inventory"]
    wait = WebDriverWait(driver, timeout)

    try:
        log("  ├ Searching asset...")
        search = stock_logins.wait_clickable(driver, By.CLASS_NAME, "search-input", timeout)
        search.clear()
        search.send_keys(asset_id)
        search.send_keys(Keys.ENTER)

        time.sleep(settings["asset_search_wait_seconds"])

        log("  ├ Opening asset...")
        thumb = stock_logins.wait_clickable(
            driver, By.CLASS_NAME, "content-thumbnail", timeout
        )
        thumb.click()

        log("  ├ Checking current title...")
        time.sleep(settings["reveal_edit_wait_seconds"])
        if adobe_title_already_matches(driver, title):
            log("  └ Skipping: title already matches")
            return None

        log("  ├ Opening title editor...")
        click_adobe_title_edit_without_hover(driver, timeout)

        log("  ├ Updating title...")
        time.sleep(settings["edit_input_wait_seconds"])
        input_field = stock_logins.wait_clickable(driver, By.CLASS_NAME, "input--full", timeout)
        if not set_input_value_with_verification(driver, input_field, title):
            raise Exception("Failed to set Adobe title input reliably")
        input_field.send_keys(Keys.SPACE, Keys.BACKSPACE)

        log("  ├ Saving...")
        save_btn = stock_logins.wait_clickable(
            driver, By.CLASS_NAME, "button--action", timeout
        )
        save_btn.click()

        log("  ├ Confirming...")
        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm')]"))
        )
        confirm_btn.click()

        log("  └ Done")

    except Exception as e:
        log(f"  ✖ Failed: {e}")
        return False

    return True

def update_shutterstock_asset(driver, asset_id, value, app_config):
    log(f"\nProcessing asset {asset_id}")
    timeout = app_config["selenium"]["timeout_seconds"]
    settings = app_config["set_inventory"]
    wait = WebDriverWait(driver, timeout)

    try:
        log("  ├ Opening asset page...")
        driver.get("https://submit.shutterstock.com/portfolio/published/photo?q={asset_id}&filterType=id".format(asset_id=quote(str(asset_id))))

        time.sleep(settings["asset_search_wait_seconds"])

        log("  ├ Opening first result...")
        result_tiles = wait_for_all_visible_css(driver, ".MuiBox-root.css-whh5e5", timeout)
        result_tiles[0].click()

        log("  ├ Updating title...")
        input_element = wait_for_visible_css(driver, "textarea[name='description']", timeout)

        set_input_value(driver, input_element, value)
        time.sleep(settings["edit_input_wait_seconds"])
        input_element.send_keys(Keys.SPACE, Keys.BACKSPACE)
        time.sleep(0.5)

        log("  ├ Saving...")
        wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='edit-dialog-save-button']"))
        ).click()

        log("  ├ Waiting for save confirmation...")
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        f"//*[contains(normalize-space(.), \"Your edit has been updated successfully.\")]",
                    )
                )
            )
        except TimeoutException:
            log("  ✖ Timed out waiting for save confirmation; assuming rename failed")
            return False

        log("  └ Done")

    except TimeoutException as e:
        log(f"  ✖ Timed out: {e}")
        return False
    except Exception as e:
        log(f"  ✖ Failed: {e}")
        return False

    return True

def main():
    parser = argparse.ArgumentParser()
    platform_group = parser.add_mutually_exclusive_group(required=True)
    platform_group.add_argument("--adobe", action="store_true")
    platform_group.add_argument("--shutterstock", action="store_true")

    parser.add_argument("--asset", type=str, help="Single asset ID")
    parser.add_argument("--title", type=str, help="Title/value for single asset")
    parser.add_argument("--value", type=str, help="Generic value for single asset")
    parser.add_argument("--file", type=str, help="CSV input file")

    args = parser.parse_args()

    single_value = args.value if args.value is not None else args.title

    if args.asset and single_value is None:
        raise Exception("--value or --title is required with --asset")

    if not args.asset and not args.file:
        raise Exception("Provide either --asset or --file")

    app_config = stock_logins.load_config()
    driver = stock_logins.create_driver(app_config)

    try:
        if args.adobe:
            stock_logins.login_adobe(
                driver,
                app_config,
                log,
                start_url=app_config["set_inventory"]["portfolio_url"],
            )
        else:
            stock_logins.login_shutterstock(
                driver,
                app_config,
                log,
                start_url="https://submit.shutterstock.com/portfolio/published/photo",
            )

        if args.asset:
            tasks = [(args.asset, single_value)]
        else:
            tasks = parse_csv(args.file)

        log(f"\nLoaded {len(tasks)} tasks")

        success = 0
        skipped = 0
        for asset_id, value in tasks:
            if args.adobe:
                updated = update_adobe_asset(driver, asset_id, value, app_config)
            else:
                updated = update_shutterstock_asset(driver, asset_id, value, app_config)

            if updated is None:
                skipped += 1
            elif updated:
                success += 1

            time.sleep(app_config["set_inventory"]["between_assets_wait_seconds"])

        log(f"\nFinished: {success}/{len(tasks)} successful, {skipped} skipped")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
