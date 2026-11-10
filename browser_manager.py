import os
import time
import random
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import PROFILE_DIR, SCREENSHOTS_DIR, PAGE_TIMEOUT, CHROME_DEBUG_PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BrowserManager")

class BrowserManager:
    def __init__(self, headless: bool = False, use_existing_chrome: bool = False):
        self.headless = headless
        self.use_existing_chrome = use_existing_chrome
        self.driver = None

    def start_driver(self):
        options = Options()

        if self.use_existing_chrome:
            # Connect to existing Chrome instance running with --remote-debugging-port=9222
            logger.info(f"Connecting to existing Chrome instance on port {CHROME_DEBUG_PORT}...")
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")
        else:
            # Use dedicated persistent profile directory
            user_data_path = str(PROFILE_DIR)
            logger.info(f"Using persistent Chrome user profile at {user_data_path}")
            options.add_argument(f"--user-data-dir={user_data_path}")
            
            if self.headless:
                options.add_argument("--headless=new")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1600,1000")
            options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
            
            # Anti-detection flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(options=options)
            
            # Mask navigator.webdriver
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                }
            )
            self.driver.implicitly_wait(5)
            logger.info("Chrome driver initialized successfully.")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to start Chrome driver: {e}")
            raise e

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver stopped.")
            except Exception as e:
                logger.warning(f"Error while closing driver: {e}")
            self.driver = None

    def human_delay(self, min_s: float = 1.5, max_s: float = 3.5):
        time.sleep(random.uniform(min_s, max_s))

    def wait_for_element(self, by: By, value: str, timeout: int = PAGE_TIMEOUT):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))

    def wait_for_clickable(self, by: By, value: str, timeout: int = PAGE_TIMEOUT):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable((by, value)))

    def take_screenshot(self, name_prefix: str) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"Screenshot captured: {filepath}")
        return str(filepath)

    def scroll_smoothly(self, pixels: int = 500):
        try:
            self.driver.execute_script(f"window.scrollBy({{top: {pixels}, behavior: 'smooth'}});")
            self.human_delay(0.8, 1.5)
        except Exception:
            pass
