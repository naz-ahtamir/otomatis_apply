import os
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

from config import (
    DB_FILE, TARGET_ROLES, TARGET_COUNTRIES,
    DEFAULT_WEEKLY_LIMIT, HEADLESS
)
from browser_manager import BrowserManager
from revou_companion import RevoUCompanion
from linkedin_engine import LinkedInEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Orchestrator")

class JobAgentOrchestrator:
    def __init__(self, headless: bool = False, use_existing_chrome: bool = False):
        self.browser = BrowserManager(headless=headless, use_existing_chrome=use_existing_chrome)
        self.revou = None
        self.linkedin = None
        self.database = self.load_database()

    def load_database(self) -> dict:
        if DB_FILE.exists():
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load database, creating new: {e}")
        return {"applications": [], "last_run": None}

    def save_database(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.database, f, indent=2, ensure_ascii=False)
        logger.info(f"Updated local database: {len(self.database['applications'])} total jobs tracked.")

    def is_already_applied(self, job_url: str) -> bool:
        for app in self.database["applications"]:
            if app.get("job_url") == job_url:
                return True
        return False

    def display_status(self):
        apps = self.database.get("applications", [])
        print("\n" + "="*70)
        print("📊 STATUS TRACKER LAMARAN KERJA (CAREER COMPANION & LINKEDIN)")
        print("="*70)
        print(f"Total lamaran tercatat: {len(apps)}")
        if not apps:
            print("Belum ada lowongan yang diapply.")
            print("="*70 + "\n")
            return

        for idx, app in enumerate(apps[-10:], 1):
            print(f"[{idx}] {app.get('applied_at')} | {app.get('company_name')} - {app.get('job_title')}")
            print(f"    LinkedIn Apply  : {app.get('application_status')}")
            print(f"    Recruiter Reach : {app.get('recruiter_status')} ({app.get('recruiter_name', 'N/A')})")
            print(f"    RevoU Tracker   : {app.get('revou_tracker_status')}")
            print(f"    Bukti Screenshot: {app.get('application_screenshot')}")
            print("-" * 70)
        print("="*70 + "\n")

    def run_pipeline(self, target_count: int = 10):
        logger.info(f"Starting Job Application Agent. Target this session: {target_count} jobs.")
        self.browser.start_driver()
        self.revou = RevoUCompanion(self.browser)
        self.linkedin = LinkedInEngine(self.browser)

        try:
            # 1. Ensure authenticated on both platforms
            logger.info("Step 1: Checking authentication...")
            self.revou.ensure_logged_in()
            self.linkedin.ensure_logged_in()

            applied_this_session = 0

            # 2. Search & Apply Loop across roles and countries
            for role in TARGET_ROLES:
                if applied_this_session >= target_count:
                    break

                for country in TARGET_COUNTRIES:
                    if applied_this_session >= target_count:
                        break

                    logger.info(f"Searching for '{role}' in '{country}' (Remote)...")
                    jobs = self.linkedin.search_jobs(role=role, location=country, max_results=5)

                    for job in jobs:
                        if applied_this_session >= target_count:
                            break

                        job_url = job["url"]
                        if self.is_already_applied(job_url):
                            logger.info(f"Skipping already processed job: {job['title']} at {job['company']}")
                            continue

                        print("\n" + "#"*70)
                        logger.info(f"Processing candidate job: {job['title']} at {job['company']}")
                        print("#"*70)

                        record = {
                            "job_title": job["title"],
                            "company_name": job["company"],
                            "job_url": job_url,
                            "country": country,
                            "applied_at": datetime.now().isoformat(),
                            "job_matching_status": "PENDING",
                            "application_status": "PENDING",
                            "application_screenshot": None,
                            "recruiter_status": "PENDING",
                            "recruiter_name": None,
                            "recruiter_screenshot": None,
                            "revou_tracker_status": "PENDING"
                        }

                        # PHASE 1: RevoU Job Matching
                        logger.info("[PHASE 1] RevoU Job Matching with CV 'Nasaruddin,ST2'...")
                        match_res = self.revou.run_job_matching(
                            job_title=job["title"],
                            job_description=f"{job['title']} at {job['company']}",
                            job_url=job_url,
                            cv_name="Nasaruddin,ST2"
                        )
                        record["job_matching_status"] = match_res.get("status")

                        # PHASE 2: LinkedIn Easy Apply
                        logger.info("[PHASE 2] Executing LinkedIn Easy Apply...")
                        apply_res = self.linkedin.apply_job(job_url)
                        record["application_status"] = apply_res.get("status")
                        record["application_screenshot"] = apply_res.get("screenshot")

                        if apply_res.get("status") != "SUCCESS":
                            logger.warning(f"Could not complete Easy Apply for {job['title']}. Skipping outreach & tracker.")
                            self.database["applications"].append(record)
                            self.save_database()
                            continue

                        # PHASE 3: Recruiter Connection & Outreach
                        logger.info("[PHASE 3] Connecting with recruiter / closest contact...")
                        recruiter_info = apply_res.get("recruiter") or {}
                        outreach_res = self.linkedin.connect_with_recruiter(
                            recruiter_info=recruiter_info,
                            job_title=job["title"],
                            company_name=job["company"]
                        )
                        record["recruiter_status"] = outreach_res.get("status")
                        record["recruiter_name"] = outreach_res.get("recruiter_name")
                        record["recruiter_screenshot"] = outreach_res.get("screenshot")

                        # PHASE 4: Submit to RevoU Application Tracker
                        logger.info("[PHASE 4] Submitting to RevoU Quality Application Tracker...")
                        tracker_payload = {
                            "company_name": job["company"],
                            "job_title": job["title"],
                            "job_url": job_url,
                            "screenshot_path": record["application_screenshot"],
                            "outreach_screenshot": record["recruiter_screenshot"]
                        }
                        revou_submitted = self.revou.submit_application_tracker(tracker_payload)
                        record["revou_tracker_status"] = "SUBMITTED" if revou_submitted else "FAILED"

                        # Save record
                        self.database["applications"].append(record)
                        self.database["last_run"] = datetime.now().isoformat()
                        self.save_database()

                        applied_this_session += 1
                        logger.info(f"✅ Successfully processed {applied_this_session}/{target_count} jobs!")

                        # Human pause between applications
                        logger.info("Pausing before next job to respect rate limits...")
                        self.browser.human_delay(15, 30)

            logger.info(f"Pipeline finished! Applied to {applied_this_session} jobs this session.")

        finally:
            self.display_status()
            self.browser.quit()

    def process_single_job(self, job_url: str):
        """Processes a single specific job URL end-to-end."""
        logger.info(f"Targeting single job application: {job_url}")
        self.browser.start_driver()
        self.revou = RevoUCompanion(self.browser)
        self.linkedin = LinkedInEngine(self.browser)

        try:
            # 1. Ensure authenticated on both platforms
            logger.info("Checking authentication on RevoU & LinkedIn...")
            self.revou.ensure_logged_in()
            self.linkedin.ensure_logged_in()

            print("\n" + "#"*70)
            logger.info(f"Navigating to job: {job_url}")
            print("#"*70)

            # Get job details from page
            self.linkedin.driver.get(job_url)
            self.browser.human_delay(3, 5)
            details = self.linkedin.extract_job_details()
            job_title = details.get("title", "Software Developer")
            company_name = details.get("company", "Company")

            logger.info(f"Detected Job: '{job_title}' at '{company_name}'")

            record = {
                "job_title": job_title,
                "company_name": company_name,
                "job_url": job_url,
                "country": details.get("location", "Australia"),
                "applied_at": datetime.now().isoformat(),
                "job_matching_status": "PENDING",
                "application_status": "PENDING",
                "application_screenshot": None,
                "recruiter_status": "PENDING",
                "recruiter_name": None,
                "recruiter_screenshot": None,
                "revou_tracker_status": "PENDING"
            }

            # PHASE 1: RevoU Job Matching
            logger.info("[PHASE 1] RevoU Job Matching with CV 'Nasaruddin,ST2'...")
            match_res = self.revou.run_job_matching(
                job_title=job_title,
                job_description=f"{job_title} at {company_name}",
                job_url=job_url,
                cv_name="Nasaruddin,ST2"
            )
            record["job_matching_status"] = match_res.get("status")

            # PHASE 2: Apply for Job (LinkedIn Easy Apply or Form Apply)
            logger.info("[PHASE 2] Executing Job Application & Capturing Screenshot...")
            apply_res = self.linkedin.apply_job(job_url)
            record["application_status"] = apply_res.get("status")
            record["application_screenshot"] = apply_res.get("screenshot")

            # PHASE 3: Recruiter Connection & Outreach
            logger.info("[PHASE 3] Connecting with recruiter / closest contact...")
            recruiter_info = apply_res.get("recruiter") or {}
            outreach_res = self.linkedin.connect_with_recruiter(
                recruiter_info=recruiter_info,
                job_title=job_title,
                company_name=company_name
            )
            record["recruiter_status"] = outreach_res.get("status")
            record["recruiter_name"] = outreach_res.get("recruiter_name")
            record["recruiter_screenshot"] = outreach_res.get("screenshot")

            # PHASE 4: Submit to RevoU Quality Application Tracker
            logger.info("[PHASE 4] Submitting to RevoU Quality Application Tracker...")
            tracker_payload = {
                "company_name": company_name,
                "job_title": job_title,
                "job_url": job_url,
                "screenshot_path": record["application_screenshot"],
                "outreach_screenshot": record["recruiter_screenshot"]
            }
            revou_submitted = self.revou.submit_application_tracker(tracker_payload)
            record["revou_tracker_status"] = "SUBMITTED" if revou_submitted else "FAILED"

            # Save record to database
            self.database["applications"].append(record)
            self.database["last_run"] = datetime.now().isoformat()
            self.save_database()

            print("\n" + "="*70)
            logger.info(f"🎉 Selesai memproses lowongan: {job_title} di {company_name}!")
            print("="*70)

        finally:
            self.display_status()
            self.browser.quit()

def main():
    parser = argparse.ArgumentParser(description="LinkedIn & RevoU Career Companion Automation Agent")
    parser.add_argument("--run", action="store_true", help="Start the automated job application cycle")
    parser.add_argument("--job-url", type=str, help="Apply directly to a specific LinkedIn job URL")
    parser.add_argument("--count", type=int, default=10, help="Number of applications to complete (default: 10)")
    parser.add_argument("--status", action="store_true", help="Display application history and status")
    parser.add_argument("--connect-existing", action="store_true", help="Connect to existing Chrome on port 9222")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()
    orchestrator = JobAgentOrchestrator(headless=args.headless, use_existing_chrome=args.connect_existing)

    if args.status:
        orchestrator.display_status()
    elif args.job_url:
        orchestrator.process_single_job(args.job_url)
    elif args.run:
        orchestrator.run_pipeline(target_count=args.count)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
