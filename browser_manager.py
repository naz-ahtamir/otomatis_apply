import os
import time
import shutil
import random
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import (
    FIREFOX_SOURCE_PROFILE,
    FIREFOX_WORKING_PROFILE,
    SCREENSHOTS_DIR,
    PAGE_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BrowserManager")


class BrowserManager:
    def __init__(self, headless: bool = False, use_existing_chrome: bool = False):
        self.headless = headless
        self.driver = None

    def _prepare_firefox_profile(self) -> Path:
        """
        Ensures a clean working Firefox profile exists with the user's logged-in
        cookies and session storage copied from the default Firefox ESR profile.
        """
        if not FIREFOX_WORKING_PROFILE.exists() and FIREFOX_SOURCE_PROFILE.exists():
            logger.info(f"Cloning Firefox profile from {FIREFOX_SOURCE_PROFILE}...")
            shutil.copytree(
                FIREFOX_SOURCE_PROFILE,
                FIREFOX_WORKING_PROFILE,
                ignore=shutil.ignore_patterns("lock", ".parentlock", "parent.lock", "cache2", "startupCache"),
            )
        elif FIREFOX_SOURCE_PROFILE.exists():
            # Refresh session/cookies files so latest logins are always available
            for fname in ["cookies.sqlite", "cookies.sqlite-wal", "cookies.sqlite-shm"]:
                src_file = FIREFOX_SOURCE_PROFILE / fname
                if src_file.exists():
                    try:
                        shutil.copy2(src_file, FIREFOX_WORKING_PROFILE / fname)
                    except Exception as e:
                        logger.debug(f"Could not sync {fname}: {e}")

        # Clean up any stale lock files in working profile
        for lock_name in ["lock", ".parentlock", "parent.lock"]:
            lock_file = FIREFOX_WORKING_PROFILE / lock_name
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except Exception:
                    pass

        FIREFOX_WORKING_PROFILE.mkdir(parents=True, exist_ok=True)
        return FIREFOX_WORKING_PROFILE

    def start_driver(self):
        options = Options()
        profile_path = self._prepare_firefox_profile()
        logger.info(f"Using Firefox profile at {profile_path}")

        options.add_argument("-profile")
        options.add_argument(str(profile_path))

        if self.headless:
            options.add_argument("--headless")

        # Anti-detection preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        try:
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_window_size(1600, 1000)
            self.driver.implicitly_wait(5)
            logger.info("Firefox driver initialized successfully.")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to start Firefox driver: {e}")
            raise e

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Firefox driver stopped.")
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
