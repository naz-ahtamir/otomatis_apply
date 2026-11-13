import os
import time
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from browser_manager import BrowserManager
from config import REVOU_JOB_MATCHING_URL, REVOU_APPLICATION_URL

logger = logging.getLogger("RevoUCompanion")


class RevoUCompanion:
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.driver = browser.driver

    def ensure_logged_in(self) -> bool:
        """Checks if logged into RevoU. If at /login, waits for user to log in on the browser."""
        self.driver.get(REVOU_JOB_MATCHING_URL)
        self.browser.human_delay(2, 4)

        current_url = self.driver.current_url
        if "login" in current_url:
            logger.warning("RevoU requires authentication! Please log in on the opened browser window...")
            print("\n" + "="*60)
            print("👉 SILAKAN LOGIN KE REVOU CAREER COMPANION DI BROWSER.")
            print("Sistem akan otomatis melanjutkan begitu login berhasil terdeteksi...")
            print("="*60 + "\n")

            for _ in range(90):
                time.sleep(2)
                if "login" not in self.driver.current_url:
                    logger.info("RevoU login detected successfully!")
                    self.browser.human_delay(2, 3)
                    return True
            logger.warning("RevoU login timeout reached, continuing anyway...")
        return True

    def run_job_matching(self, job_title: str, company_name: str, job_description: str, job_url: str, cv_name: str = "NASARUDDIN, ST 2") -> dict:
        """
        Runs job matching on RevoU Career Companion:
        Clicks '+ New match', selects CV 'NASARUDDIN, ST 2', fills job details, and captures match results.
        """
        logger.info(f"Navigating to RevoU Job Matching for '{job_title}' at '{company_name}' with CV '{cv_name}'...")
        self.driver.get(REVOU_JOB_MATCHING_URL)
        self.browser.human_delay(2, 4)

        result = {
            "cv_profile": cv_name,
            "job_title": job_title,
            "company_name": company_name,
            "job_url": job_url,
            "status": "CHECKED",
            "screenshot": None
        }

        try:
            # 1. Click '+ New match' button
            new_match_btns = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'New match') or contains(., '+ New')]"
            )
            for btn in new_match_btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    logger.info("Clicked '+ New match' button.")
                    self.browser.human_delay(1.5, 2.5)
                    break

            # Scope interaction to the modal dialog if present
            modal_scope = "//div[@role='dialog']"
            dialogs = self.driver.find_elements(By.XPATH, modal_scope)
            prefix = modal_scope if dialogs else ""

            # 2. Select CV profile ('NASARUDDIN, ST 2' or 'Nasaruddin,ST2')
            selects = self.driver.find_elements(By.XPATH, f"{prefix}//select" if prefix else "//select")
            for sel in selects:
                try:
                    s_obj = Select(sel)
                    for opt in s_obj.options:
                        if "nasaruddin" in opt.text.lower() or "st 2" in opt.text.lower() or "st2" in opt.text.lower():
                            s_obj.select_by_visible_text(opt.text)
                            logger.info(f"Selected CV profile: {opt.text}")
                            break
                except Exception:
                    pass

            cv_dropdowns = self.driver.find_elements(By.XPATH, f"{prefix}//button[@role='combobox']" if prefix else "//button[@role='combobox']")
            for dd in cv_dropdowns:
                try:
                    dd.click()
                    self.browser.human_delay(0.8, 1.5)
                    opt = self.driver.find_element(By.XPATH, "//*[@role='option' and (contains(., 'NASARUDDIN') or contains(., 'ST 2'))]")
                    opt.click()
                    logger.info("Selected CV from custom dropdown.")
                    break
                except Exception:
                    pass

            # 3. Fill Job Title, Company, and Job Description
            inputs = self.driver.find_elements(By.XPATH, f"{prefix}//input" if prefix else "//input")
            for inp in inputs:
                if not inp.is_displayed():
                    continue
                p = (inp.get_attribute("placeholder") or "").lower()
                n = (inp.get_attribute("name") or "").lower()
                lbl = f"{p} {n}"
                if any(k in lbl for k in ["title", "role", "posisi"]):
                    inp.clear()
                    inp.send_keys(job_title)
                elif any(k in lbl for k in ["company", "perusahaan"]):
                    inp.clear()
                    inp.send_keys(company_name)
                elif any(k in lbl for k in ["url", "link"]):
                    inp.clear()
                    inp.send_keys(job_url)

            textareas = self.driver.find_elements(By.XPATH, f"{prefix}//textarea" if prefix else "//textarea")
            for ta in textareas:
                if ta.is_displayed():
                    ta.clear()
                    desc_to_paste = job_description if job_description else f"{job_title} at {company_name}"
                    ta.send_keys(desc_to_paste[:4000])
                    logger.info("Filled job description in Job Matching form.")
                    break

            self.browser.human_delay(1, 2)

            # 4. Click Match / Analyze / Submit button inside modal/form
            buttons = self.driver.find_elements(By.XPATH, f"{prefix}//button" if prefix else "//button")
            for btn in buttons:
                if not btn.is_displayed() or not btn.is_enabled():
                    continue
                txt = btn.text.strip().lower()
                if "new match" in txt or "scored against" in txt or "cancel" in txt or "close" in txt:
                    continue
                if any(k in txt for k in ["match", "analyze", "run", "score", "submit", "cek", "create"]):
                    btn.click()
                    logger.info(f"Clicked Job Matching submit button: '{btn.text.strip()}'")
                    self.browser.human_delay(8, 12)
                    break

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
        Uploads networking/application screenshot proof and waits for submission confirmation.
        """
        company = application_data.get("company_name", "")
        role = application_data.get("job_title", "")
        job_desc = application_data.get("job_description", "")
        screenshot_path = application_data.get("screenshot_path", "")
        outreach_screenshot = application_data.get("outreach_screenshot", "")

        logger.info(f"Navigating to RevoU Application Tracker to log '{role}' at '{company}'...")
        self.driver.get(REVOU_APPLICATION_URL)
        self.browser.human_delay(2, 4)

        try:
            # 1. Try selecting the newly matched job in 'Job match result' dropdown
            match_selected = False
            dropdowns = self.driver.find_elements(By.XPATH, "//select | //button[@role='combobox']")
            for dd in dropdowns:
                try:
                    if dd.tag_name == "select":
                        s_obj = Select(dd)
                        for opt in s_obj.options:
                            if company.lower() in opt.text.lower() or role.lower() in opt.text.lower():
                                s_obj.select_by_visible_text(opt.text)
                                match_selected = True
                                logger.info(f"Selected job match result: {opt.text}")
                                break
                    else:
                        dd.click()
                        self.browser.human_delay(0.8, 1.5)
                        opts = self.driver.find_elements(By.XPATH, f"//*[@role='option' and (contains(., '{company}') or contains(., '{role}'))]")
                        for o in opts:
                            if o.is_displayed():
                                o.click()
                                match_selected = True
                                logger.info(f"Selected job match result from combobox: {o.text}")
                                break
                        if not match_selected:
                            # Close dropdown so it does not obscure Submit button
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            self.browser.human_delay(0.5, 1.0)
                except Exception:
                    pass
                if match_selected:
                    break

            self.browser.human_delay(1, 2)

            # 2. Explicitly ensure Job title, Company, and Job description match current job
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                t = (inp.get_attribute("type") or "text").lower()
                if t == "file":
                    # Upload proof screenshot (prioritize recruiter outreach screenshot per RevoU label)
                    proof_file = outreach_screenshot or screenshot_path
                    if proof_file and os.path.exists(proof_file):
                        inp.send_keys(str(Path(proof_file).resolve()))
                        logger.info(f"Uploaded proof screenshot to tracker: {proof_file}")
                        self.browser.human_delay(2, 3)
                    continue

                if not inp.is_displayed():
                    continue
                p = (inp.get_attribute("placeholder") or "").lower()
                n = (inp.get_attribute("name") or "").lower()
                lbl = f"{p} {n}"
                if any(k in lbl for k in ["title", "posisi", "role"]):
                    inp.clear()
                    inp.send_keys(role)
                elif any(k in lbl for k in ["company", "perusahaan"]):
                    inp.clear()
                    inp.send_keys(company)

            # Also check labels by sibling/parent if inputs had no placeholder/name
            try:
                title_input = self.driver.find_element(By.XPATH, "//label[contains(., 'Job title')]/following::input[1]")
                title_input.clear()
                title_input.send_keys(role)
            except Exception:
                pass
            try:
                comp_input = self.driver.find_element(By.XPATH, "//label[contains(., 'Company')]/following::input[1]")
                comp_input.clear()
                comp_input.send_keys(company)
            except Exception:
                pass
            try:
                desc_ta = self.driver.find_element(By.XPATH, "//label[contains(., 'Job description')]/following::textarea[1]")
                if job_desc:
                    desc_ta.clear()
                    desc_ta.send_keys(job_desc[:4000])
            except Exception:
                pass

            self.browser.human_delay(1.5, 2.5)

            # 3. Click Submit button (avoid clicking disabled/submitting)
            submit_btn = None
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    txt = btn.text.strip().lower()
                    if any(k in txt for k in ["submit", "simpan", "save", "kirim"]):
                        submit_btn = btn
                        break

            if submit_btn:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                self.browser.human_delay(0.5, 1.0)
                try:
                    submit_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                logger.info("Clicked Submit on RevoU Quality Application form. Waiting for completion...")

                # Wait up to 20 seconds for 'Submitting...' to finish
                for _ in range(10):
                    time.sleep(2)
                    still_submitting = self.driver.find_elements(By.XPATH, "//button[contains(., 'Submitting')]")
                    if not still_submitting:
                        break

            self.browser.take_screenshot("revou_application_submitted")
            logger.info("RevoU Application Tracker submission finished successfully.")
            return True

        except Exception as e:
            logger.error(f"Failed to submit to RevoU application tracker: {e}")
            self.browser.take_screenshot("revou_submit_error")
            return False
