import configparser
import sys
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


CONFIG_FILE = "config.ini"


def default_log(msg):
    print(msg, file=sys.stderr, flush=True)


def load_config():
    parser = configparser.ConfigParser()
    config_path = Path(__file__).resolve().parent / CONFIG_FILE

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Missing {CONFIG_FILE}. Copy default-config.ini to {CONFIG_FILE} and update it with your credentials."
        )

    parser.read(config_path)

    return {
        "selenium": {
            "timeout_seconds": parser.getint("selenium", "timeout_seconds"),
            "start_maximized": parser.getboolean("selenium", "start_maximized"),
            "disable_automation_controlled": parser.getboolean(
                "selenium", "disable_automation_controlled"
            ),
        },
        "scraping": {
            "max_retries": parser.getint("scraping", "max_retries"),
            "retry_delay_seconds": parser.getfloat(
                "scraping", "retry_delay_seconds"
            ),
            "page_delay_seconds": parser.getfloat("scraping", "page_delay_seconds"),
            "page_load_wait_seconds": parser.getfloat(
                "scraping", "page_load_wait_seconds"
            ),
        },
        "shutterstock": {
            "username": parser.get("shutterstock", "username"),
            "password": parser.get("shutterstock", "password"),
            "portfolio_url": parser.get("shutterstock", "portfolio_url"),
            "login_page_wait_seconds": parser.getfloat(
                "shutterstock", "login_page_wait_seconds"
            ),
            "post_login_wait_seconds": parser.getfloat(
                "shutterstock", "post_login_wait_seconds"
            ),
        },
        "adobe": {
            "username": parser.get("adobe", "username"),
            "portfolio_url": parser.get("adobe", "portfolio_url"),
            "login_page_wait_seconds": parser.getfloat(
                "adobe", "login_page_wait_seconds"
            ),
            "google_continue_timeout_seconds": parser.getfloat(
                "adobe", "google_continue_timeout_seconds"
            ),
            "manual_login_timeout_seconds": parser.getfloat(
                "adobe", "manual_login_timeout_seconds"
            ),
            "manual_login_poll_seconds": parser.getfloat(
                "adobe", "manual_login_poll_seconds"
            ),
        },
        "set_inventory": {
            "portfolio_url": parser.get("set_inventory", "portfolio_url"),
            "asset_search_wait_seconds": parser.getfloat(
                "set_inventory", "asset_search_wait_seconds"
            ),
            "reveal_edit_wait_seconds": parser.getfloat(
                "set_inventory", "reveal_edit_wait_seconds"
            ),
            "edit_input_wait_seconds": parser.getfloat(
                "set_inventory", "edit_input_wait_seconds"
            ),
            "between_assets_wait_seconds": parser.getfloat(
                "set_inventory", "between_assets_wait_seconds"
            ),
        },
    }


def create_driver(app_config):
    options = Options()
    if app_config["selenium"]["start_maximized"]:
        options.add_argument("--start-maximized")
    if app_config["selenium"]["disable_automation_controlled"]:
        options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)


def wait_for(driver, by, selector, timeout):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def wait_clickable(driver, by, selector, timeout):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )


def wait_for_adobe_manual_login(driver, settings):
    return WebDriverWait(
        driver,
        settings["manual_login_timeout_seconds"],
        poll_frequency=settings["manual_login_poll_seconds"],
    ).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//span[contains(@class, 'time-frame-select__label') "
                "and normalize-space()='Time Frame']",
            )
        )
    )


def login_shutterstock(driver, app_config, logger=None, start_url=None):
    logger = logger or default_log
    timeout = app_config["selenium"]["timeout_seconds"]
    settings = app_config["shutterstock"]

    driver.get(start_url or settings["portfolio_url"].format(page=1))
    time.sleep(settings["login_page_wait_seconds"])

    logger("  ├ Filling username...")
    wait_for(driver, By.CSS_SELECTOR, '[data-test-id="email-input"]', timeout).send_keys(
        settings["username"]
    )

    logger("  ├ Filling password...")
    wait_for(
        driver, By.CSS_SELECTOR, '[data-test-id="password-input"]', timeout
    ).send_keys(settings["password"])

    logger("  └ Submitting login...")
    wait_clickable(
        driver,
        By.CSS_SELECTOR,
        '[data-test-id="login-form-submit-button"]',
        timeout,
    ).click()

    time.sleep(settings["post_login_wait_seconds"])


def login_adobe(driver, app_config, logger=None, start_url=None):
    logger = logger or default_log
    timeout = app_config["selenium"]["timeout_seconds"]
    settings = app_config["adobe"]

    logger("Opening Adobe login page...")
    driver.get(start_url or settings["portfolio_url"].format(page=1))
    time.sleep(settings["login_page_wait_seconds"])

    logger("Clicking Google login...")
    wait_clickable(
        driver, By.CSS_SELECTOR, '[data-social-provider="Google"]', timeout
    ).click()

    email_input = wait_for(driver, By.ID, "identifierId", timeout)
    email_input.send_keys(settings["username"])
    email_input.send_keys("\n")

    try:
        continue_btn = WebDriverWait(
            driver, settings["google_continue_timeout_seconds"]
        ).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='Continue']")
            )
        )
        continue_btn.click()
    except TimeoutException:
        pass

    logger("Waiting for Adobe login to complete in the browser...")
    wait_for_adobe_manual_login(driver, settings)