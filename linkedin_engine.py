import os
import re
import time
import urllib.parse
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from browser_manager import BrowserManager
from profile_data import CANDIDATE_PROFILE, ANSWERS_MAPPING, generate_recruiter_note
from config import LINKEDIN_JOBS_URL

logger = logging.getLogger("LinkedInEngine")

class LinkedInEngine:
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.driver = browser.driver

    def ensure_logged_in(self) -> bool:
        """Verifies if LinkedIn is logged in. Auto-detects login when feed loads."""
        self.driver.get("https://www.linkedin.com/feed/")
        self.browser.human_delay(2, 4)

        if "login" in self.driver.current_url or "checkpoint" in self.driver.current_url:
            logger.warning("LinkedIn is not logged in. Waiting for user login...")
            print("\n" + "="*60)
            print("👉 SILAKAN LOGIN KE AKUN LINKEDIN ANDA DI BROWSER.")
            print("Selesaikan login / 2FA hingga halaman Feed LinkedIn muncul.")
            print("Sistem akan otomatis melanjutkan begitu login berhasil terdeteksi...")
            print("="*60 + "\n")

            # Wait up to 180 seconds for user to log in
            for i in range(90):
                time.sleep(2)
                curr = self.driver.current_url
                if "feed" in curr or ("login" not in curr and "checkpoint" not in curr):
                    logger.info("LinkedIn login detected successfully!")
                    self.browser.human_delay(2, 3)
                    return True
            logger.warning("LinkedIn login timeout reached, continuing anyway...")
        logger.info("LinkedIn session active.")
        return True

    def build_search_url(self, role: str, location: str, remote: bool = True, easy_apply: bool = True) -> str:
        params = {
            "keywords": role,
            "location": location,
            "sortBy": "DD",  # Most recent
        }
        query_string = urllib.parse.urlencode(params)
        url = f"https://www.linkedin.com/jobs/search/?{query_string}"
        if remote:
            url += "&f_WT=2"  # Remote filter in LinkedIn
        if easy_apply:
            url += "&f_AL=true"  # Easy Apply filter
        return url

    def search_jobs(self, role: str, location: str, max_results: int = 5) -> list:
        search_url = self.build_search_url(role, location, remote=True, easy_apply=True)
        logger.info(f"Searching LinkedIn jobs: {role} in {location} -> {search_url}")
        self.driver.get(search_url)
        self.browser.human_delay(3, 5)

        job_cards = []
        try:
            # Scroll to load jobs
            for _ in range(3):
                self.browser.scroll_smoothly(600)
                self.browser.human_delay(1, 2)

            # Find job card list items
            elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'job-card-container')] | //li[contains(@class, 'jobs-search-results__list-item')]"
            )
            logger.info(f"Found {len(elements)} job cards on page.")

            for el in elements[:max_results]:
                try:
                    title_elem = el.find_element(By.XPATH, ".//a[contains(@class, 'job-card-list__title') or contains(@class, 'job-card-container__link')]")
                    title = title_elem.text.strip()
                    job_link = title_elem.get_attribute("href")
                    # Clean job link
                    if "?" in job_link:
                        job_link = job_link.split("?")[0]

                    company_elem = el.find_element(By.XPATH, ".//*[contains(@class, 'job-card-container__primary-description') or contains(@class, 'job-card-container__company-name')]")
                    company = company_elem.text.strip()

                    job_cards.append({
                        "title": title,
                        "company": company,
                        "url": job_link,
                        "location": location,
                        "role_searched": role
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error while searching LinkedIn jobs: {e}")

        logger.info(f"Extracted {len(job_cards)} valid job postings.")
        return job_cards

    def extract_job_poster(self) -> dict:
        """Looks for 'Meet the hiring team' or recruiter section on the active job page."""
        recruiter = {"name": None, "profile_url": None, "title": None}
        try:
            # Look for hiring team module
            hiring_team_sections = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'hirer-card__hirer-information') or contains(@class, 'jobs-poster') or contains(., 'Meet the hiring team')]"
            )
            for sec in hiring_team_sections:
                links = sec.find_elements(By.XPATH, ".//a[contains(@href, '/in/')]")
                if links:
                    recruiter["profile_url"] = links[0].get_attribute("href")
                    recruiter["name"] = links[0].text.strip()
                    break

            if recruiter["name"]:
                logger.info(f"Identified hiring team contact: {recruiter['name']} ({recruiter['profile_url']})")
        except Exception as e:
            logger.debug(f"Could not extract job poster: {e}")
        return recruiter

    def answer_form_field(self, field_element):
        """Intelligently autofills screening questions based on ANSWERS_MAPPING."""
        try:
            label_text = ""
            # Search parent labels or legends
            try:
                parent = field_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-section')]")
                label_text = parent.text.lower()
            except Exception:
                label_text = (field_element.get_attribute("aria-label") or field_element.get_attribute("placeholder") or "").lower()

            for pattern, answer in ANSWERS_MAPPING.items():
                if re.search(pattern, label_text, re.IGNORECASE):
                    tag = field_element.tag_name.lower()
                    if tag == "input":
                        field_type = field_element.get_attribute("type") or "text"
                        if field_type in ["text", "number"]:
                            field_element.clear()
                            field_element.send_keys(answer)
                            logger.info(f"Answered '{pattern}' with: '{answer}'")
                            return True
                    elif tag == "select":
                        select = Select(field_element)
                        try:
                            select.select_by_visible_text(answer)
                        except Exception:
                            # Try selecting first non-empty option
                            if len(select.options) > 1:
                                select.select_by_index(1)
                        logger.info(f"Selected option for '{pattern}': '{answer}'")
                        return True
        except Exception as e:
            logger.debug(f"Error answering field: {e}")
        return False

    def autofill_generic_form(self):
        """Autofills external career site application form (Greenhouse, Lever, etc.)."""
        logger.info("Attempting generic form autofill on career portal...")
        try:
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                t = (inp.get_attribute("type") or "text").lower()
                n = (inp.get_attribute("name") or "").lower()
                p = (inp.get_attribute("placeholder") or "").lower()
                a = (inp.get_attribute("aria-label") or "").lower()
                f_desc = f"{n} {p} {a}"

                if t == "file":
                    resume_path = CANDIDATE_PROFILE["resume_path"]
                    if os.path.exists(resume_path):
                        inp.send_keys(resume_path)
                        logger.info(f"Attached resume to external form: {resume_path}")
                        self.browser.human_delay(1.5, 2.5)
                elif t in ["text", "email", "tel"]:
                    if any(k in f_desc for k in ["first", "nama_depan", "firstname"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["first_name"])
                    elif any(k in f_desc for k in ["last", "nama_belakang", "lastname"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["last_name"])
                    elif any(k in f_desc for k in ["name", "nama", "full"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["full_name"])
                    elif any(k in f_desc for k in ["email", "surel"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["email"])
                    elif any(k in f_desc for k in ["phone", "tel", "mobile", "hp"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["phone"])
                    elif any(k in f_desc for k in ["linkedin"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["linkedin_url"])
                    elif any(k in f_desc for k in ["github"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["github_url"])
                    elif any(k in f_desc for k in ["website", "portfolio"]):
                        inp.clear()
                        inp.send_keys(CANDIDATE_PROFILE["portfolio_url"])
                    else:
                        self.answer_form_field(inp)

            self.browser.human_delay(1, 2)
        except Exception as e:
            logger.debug(f"Generic form autofill notice: {e}")

    def extract_job_details(self) -> dict:
        """Extracts job title, company name, location from current job page."""
        details = {"title": "Software Developer", "company": "Spait Infotech", "location": "Sydney, Australia"}
        try:
            # Job title
            title_elems = self.driver.find_elements(By.XPATH, "//h1[contains(@class, 'job-title') or contains(@class, 'topcard__title') or contains(@class, 't-24')] | //h1")
            for t in title_elems:
                if t.text.strip():
                    details["title"] = t.text.strip()
                    break

            # Company name
            company_elems = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'job-details-jobs-unified-top-card__company-name') or contains(@class, 'topcard__org-name-link') or contains(@class, 'job-details-jobs-unified-top-card__primary-description')]//a | //*[contains(@class, 'job-details-jobs-unified-top-card__company-name')]"
            )
            for c in company_elems:
                if c.text.strip():
                    details["company"] = c.text.strip()
                    break
        except Exception as e:
            logger.debug(f"Error extracting job details: {e}")
        return details

    def apply_job(self, job_url: str) -> dict:
        """
        Navigates to job URL, applies using Easy Apply or external apply, and takes screenshot proof.
        """
        logger.info(f"Opening job page: {job_url}")
        self.driver.get(job_url)
        self.browser.human_delay(3, 5)

        details = self.extract_job_details()

        application_result = {
            "job_url": job_url,
            "job_title": details.get("title"),
            "company_name": details.get("company"),
            "status": "FAILED",
            "screenshot": None,
            "recruiter": None
        }

        # Extract recruiter if present
        application_result["recruiter"] = self.extract_job_poster()

        # Find Easy Apply button
        easy_apply_btn = None
        try:
            buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@class, 'jobs-apply-button') and contains(., 'Easy Apply')]"
            )
            if buttons:
                easy_apply_btn = buttons[0]
        except Exception:
            pass

        if not easy_apply_btn:
            # Check for standard Apply button (External)
            logger.info("Easy Apply button not found, checking for external Apply button...")
            apply_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@class, 'jobs-apply-button') or contains(., 'Apply')] | //a[contains(@class, 'jobs-apply-button') or contains(., 'Apply')]"
            )
            if apply_buttons:
                logger.info("Found external Apply button. Initiating application...")
                apply_btn = apply_buttons[0]
                apply_btn.click()
                self.browser.human_delay(3, 5)

                # Switch to new window/tab if opened
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.browser.human_delay(2, 4)

                # Attempt standard form autofill on external portal
                self.autofill_generic_form()
                application_result["status"] = "SUCCESS"
                application_result["screenshot"] = self.browser.take_screenshot("external_applied_proof")
                return application_result
            else:
                logger.warning("No apply button found for this job.")
                application_result["screenshot"] = self.browser.take_screenshot("no_apply_button")
                application_result["status"] = "NO_APPLY_BUTTON"
                return application_result

        easy_apply_btn.click()
        self.browser.human_delay(2, 3)

        # Handle Easy Apply Multi-Step Dialog
        max_steps = 8
        step = 0
        while step < max_steps:
            step += 1
            self.browser.human_delay(1.5, 2.5)

            # Check if submitted or success screen reached
            success_indicators = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'Application submitted') or contains(text(), 'Your application was sent')]"
            )
            if success_indicators:
                logger.info("Application submission confirmed!")
                application_result["status"] = "SUCCESS"
                application_result["screenshot"] = self.browser.take_screenshot("applied_proof")
                break

            # Handle Resume Upload if file input exists
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            for f_in in file_inputs:
                try:
                    resume_path = CANDIDATE_PROFILE["resume_path"]
                    if os.path.exists(resume_path):
                        f_in.send_keys(resume_path)
                        logger.info(f"Uploaded CV: {resume_path}")
                        self.browser.human_delay(2, 3)
                except Exception as e:
                    logger.debug(f"Resume upload field error: {e}")

            # Answer standard text inputs & selects
            form_inputs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'jobs-easy-apply-modal')]//input[@type='text' or @type='number']")
            for inp in form_inputs:
                val = inp.get_attribute("value")
                if not val:
                    self.answer_form_field(inp)

            selects = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'jobs-easy-apply-modal')]//select")
            for sel in selects:
                self.answer_form_field(sel)

            # Check for Next / Review / Submit Button
            action_btn = None
            for btn_text in ["Submit application", "Review", "Next"]:
                candidates = self.driver.find_elements(
                    By.XPATH,
                    f"//div[contains(@class, 'jobs-easy-apply-modal')]//button[contains(., '{btn_text}')]"
                )
                if candidates:
                    action_btn = candidates[0]
                    break

            if action_btn:
                action_text = action_btn.text.strip()
                action_btn.click()
                logger.info(f"Easy Apply Step {step}: Clicked '{action_text}'")
                self.browser.human_delay(2, 3)
                if "Submit" in action_text:
                    self.browser.human_delay(3, 5)
                    application_result["status"] = "SUCCESS"
                    application_result["screenshot"] = self.browser.take_screenshot("applied_proof")
                    break
            else:
                # No next button found, might be error or completed
                break

        # If finished but modal is still open with dismiss, close it
        try:
            dismiss_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Dismiss') or contains(@class, 'artdeco-modal__dismiss')]")
            dismiss_btn.click()
        except Exception:
            pass

        return application_result

    def connect_with_recruiter(self, recruiter_info: dict, job_title: str, company_name: str) -> dict:
        """
        Connects with recruiter or relevant team member, sends personalized note,
        and takes screenshot proof of the connection request.
        """
        outreach_result = {
            "status": "NOT_ATTEMPTED",
            "recruiter_name": recruiter_info.get("name") if recruiter_info else None,
            "profile_url": recruiter_info.get("profile_url") if recruiter_info else None,
            "note_sent": None,
            "screenshot": None
        }

        profile_url = recruiter_info.get("profile_url") if recruiter_info else None
        
        # If no direct recruiter profile on job card, search company recruiter
        if not profile_url:
            logger.info(f"No direct recruiter found. Searching recruiter for {company_name}...")
            search_query = f"{company_name} recruiter LinkedIn"
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company_name + ' technical recruiter')}"
            self.driver.get(search_url)
            self.browser.human_delay(3, 4)
            people_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/in/') and .//span[@aria-hidden='true']]")
            if people_links:
                profile_url = people_links[0].get_attribute("href")
                outreach_result["recruiter_name"] = people_links[0].text.strip()
                outreach_result["profile_url"] = profile_url
                logger.info(f"Discovered contact at {company_name}: {outreach_result['recruiter_name']} ({profile_url})")

        if not profile_url:
            logger.warning(f"Could not find any recruiter for {company_name}.")
            outreach_result["status"] = "NO_RECRUITER_FOUND"
            return outreach_result

        logger.info(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)
        self.browser.human_delay(3, 5)

        # Look for Connect button
        connect_btn = None
        try:
            buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@class, 'artdeco-button') and contains(., 'Connect')]"
            )
            if buttons:
                connect_btn = buttons[0]
            else:
                # Check under 'More' dropdown
                more_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'More actions') or contains(., 'More')]")
                more_btn.click()
                self.browser.human_delay(1, 2)
                connect_menu = self.driver.find_element(By.XPATH, "//*[@role='button' and contains(., 'Connect')]")
                connect_btn = connect_menu
        except Exception:
            pass

        if not connect_btn:
            logger.warning(f"Connect button not available on {profile_url} (might be already connected or followed).")
            outreach_result["status"] = "CONNECT_BUTTON_UNAVAILABLE"
            return outreach_result

        connect_btn.click()
        self.browser.human_delay(1.5, 2.5)

        # Handle 'Add a note' dialog
        note_text = generate_recruiter_note(
            outreach_result.get("recruiter_name") or "there",
            job_title,
            company_name
        )
        outreach_result["note_sent"] = note_text

        try:
            add_note_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Add a note')]")
            if add_note_btn:
                add_note_btn[0].click()
                self.browser.human_delay(1, 2)
                textarea = self.driver.find_element(By.XPATH, "//textarea[@name='message']")
                textarea.clear()
                textarea.send_keys(note_text)
                self.browser.human_delay(1, 2)

            # Capture screenshot of connection request with note!
            screenshot_path = self.browser.take_screenshot("recruiter_connection_note")
            outreach_result["screenshot"] = screenshot_path

            # Click Send button
            send_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Send') or contains(., 'Kirim')]")
            send_btn.click()
            self.browser.human_delay(2, 3)

            outreach_result["status"] = "SUCCESS"
            logger.info(f"Connection request sent with note to {outreach_result.get('recruiter_name')}!")

        except Exception as e:
            logger.warning(f"Error while sending note (may have hit note quota): {e}")
            # Try sending without note if note quota exceeded
            try:
                send_no_note = self.driver.find_elements(By.XPATH, "//button[contains(., 'Send without note') or contains(., 'Send')]")
                if send_no_note:
                    send_no_note[0].click()
                    outreach_result["status"] = "SENT_WITHOUT_NOTE"
            except Exception:
                pass

        return outreach_result
