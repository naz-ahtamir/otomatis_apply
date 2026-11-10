import os
import time
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_manager import BrowserManager
from config import REVOU_JOB_MATCHING_URL, REVOU_APPLICATION_URL

logger = logging.getLogger("RevoUCompanion")

class RevoUCompanion:
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.driver = browser.driver

    def ensure_logged_in(self) -> bool:
        """Checks if logged into RevoU. If at /login, prompts user to login."""
        self.driver.get(REVOU_JOB_MATCHING_URL)
        self.browser.human_delay(2, 4)

        current_url = self.driver.current_url
        if "login" in current_url:
            logger.warning("RevoU requires authentication! Please log in on the opened browser window.")
            print("\n" + "="*60)
            print("👉 SILAKAN LOGIN KE REVOU CAREER COMPANION DI BROWSER.")
            print("Setelah login dan dashboard terbuka, tekan ENTER di terminal ini...")
            print("="*60 + "\n")
            input("Tekan ENTER jika sudah selesai login di RevoU...")
            self.browser.human_delay(2, 3)
            return True
        return True

    def run_job_matching(self, job_title: str, job_description: str, job_url: str, cv_name: str = "Nasaruddin,ST2") -> dict:
        """
        Runs job matching on RevoU Career Companion.
        Selects CV 'Nasaruddin,ST2', inputs job details, and captures match results.
        """
        logger.info(f"Navigating to RevoU Job Matching for '{job_title}' with CV '{cv_name}'...")
        self.driver.get(REVOU_JOB_MATCHING_URL)
        self.browser.human_delay(2, 4)

        result = {
            "cv_profile": cv_name,
            "job_title": job_title,
            "job_url": job_url,
            "status": "CHECKED",
            "score": "N/A",
            "screenshot": None
        }

        try:
            # 1. Look for CV profile dropdown or selection
            # Try finding select elements or dropdown buttons
            cv_selected = False
            dropdowns = self.driver.find_elements(By.XPATH, "//button[contains(., 'CV') or contains(., 'Pilih') or contains(., 'Select')] | //select")
            for dd in dropdowns:
                try:
                    if cv_name.lower() in dd.text.lower():
                        cv_selected = True
                        break
                    dd.click()
                    self.browser.human_delay(1, 2)
                    option = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{cv_name}')]")
                    option.click()
                    cv_selected = True
                    logger.info(f"Selected CV profile: {cv_name}")
                    break
                except Exception:
                    continue

            # 2. Look for Job Title / Description input fields
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")

            for inp in inputs:
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                name_attr = (inp.get_attribute("name") or "").lower()
                if "url" in placeholder or "link" in placeholder or "url" in name_attr:
                    inp.clear()
                    inp.send_keys(job_url)
                elif "role" in placeholder or "title" in placeholder or "posisi" in placeholder:
                    inp.clear()
                    inp.send_keys(job_title)

            if textareas and job_description:
                for ta in textareas:
                    placeholder = (ta.get_attribute("placeholder") or "").lower()
                    if "deskripsi" in placeholder or "description" in placeholder or "job" in placeholder:
                        ta.clear()
                        ta.send_keys(job_description[:3000])

            self.browser.human_delay(1, 2)

            # 3. Click Match / Submit button
            submit_btn = None
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                txt = btn.text.strip().lower()
                if any(k in txt for k in ["match", "cocokkan", "analisis", "analyze", "cek", "submit"]):
                    submit_btn = btn
                    break

            if submit_btn and submit_btn.is_enabled():
                submit_btn.click()
                logger.info("Clicked Job Matching submit button.")
                self.browser.human_delay(3, 6)

            # Take screenshot of matching result
            screenshot_path = self.browser.take_screenshot("revou_job_matching")
            result["screenshot"] = screenshot_path
            result["status"] = "SUCCESS"
            logger.info("Job matching completed.")

        except Exception as e:
            logger.warning(f"Error during job matching interaction: {e}")
            result["status"] = "PARTIAL"
            result["screenshot"] = self.browser.take_screenshot("revou_job_matching_error")

        return result

    def submit_application_tracker(self, application_data: dict) -> bool:
        """
        Submits the applied job details to RevoU Application Tracker:
        https://next.revou.tech/dashboard/quality-application/application
        Uploads screenshot proof and ensures submission.
        """
        logger.info(f"Navigating to RevoU Application Tracker to log '{application_data.get('job_title')}'...")
        self.driver.get(REVOU_APPLICATION_URL)
        self.browser.human_delay(2, 4)

        try:
            # Check if there is an 'Add Application' or 'Tambah Lamaran' button first
            add_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'Tambah') or contains(., 'Add') or contains(., 'Submit') or contains(., 'New')]"
            )
            for btn in add_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        self.browser.human_delay(1.5, 2.5)
                        break
                except Exception:
                    pass

            company = application_data.get("company_name", "")
            role = application_data.get("job_title", "")
            job_url = application_data.get("job_url", "")
            screenshot_path = application_data.get("screenshot_path", "")
            outreach_screenshot = application_data.get("outreach_screenshot", "")

            # Fill Company Name
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                p = (inp.get_attribute("placeholder") or "").lower()
                n = (inp.get_attribute("name") or "").lower()
                t = (inp.get_attribute("type") or "").lower()

                if t == "text":
                    if "perusahaan" in p or "company" in p or "perusahaan" in n or "company" in n:
                        inp.clear()
                        inp.send_keys(company)
                    elif "posisi" in p or "role" in p or "title" in p or "job" in n:
                        inp.clear()
                        inp.send_keys(role)
                    elif "url" in p or "link" in p:
                        inp.clear()
                        inp.send_keys(job_url)

                elif t == "file":
                    # Upload screenshot proof
                    proof_file = screenshot_path or outreach_screenshot
                    if proof_file and os.path.exists(proof_file):
                        inp.send_keys(str(Path(proof_file).resolve()))
                        logger.info(f"Uploaded proof file to tracker form: {proof_file}")
                        self.browser.human_delay(2, 3)

            self.browser.human_delay(1.5, 3)

            # Look for submit button
            submit_btn = None
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                txt = btn.text.strip().lower()
                if any(k in txt for k in ["simpan", "submit", "save", "kirim"]):
                    submit_btn = btn
                    break

            if submit_btn and submit_btn.is_enabled():
                submit_btn.click()
                logger.info("Submitted RevoU quality application form.")
                self.browser.human_delay(3, 5)

            # Capture confirmation screenshot
            final_proof = self.browser.take_screenshot("revou_application_submitted")
            logger.info("RevoU Application Tracker submission finished successfully.")
            return True

        except Exception as e:
            logger.error(f"Failed to submit to RevoU application tracker: {e}")
            self.browser.take_screenshot("revou_submit_error")
            return False
