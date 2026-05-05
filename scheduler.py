import time
import os
from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from scraper import run_all_scrapers
from intelligence import evaluate_opportunity, generate_application_draft
import database

def scan_and_evaluate():
    print("Starting periodic opportunity scan...")
    profile = database.get_user_profile()
    
    if not profile:
        print("No user profile configured. Please set up your profile in the Dashboard first.")
        return

    # Scrape raw opportunities
    raw_opps = run_all_scrapers()
    print(f"Scraped {len(raw_opps)} new opportunities. Evaluating...")

    email_opps = []

    for opp in raw_opps:
        # Evaluate
        eval_result = evaluate_opportunity(profile, opp)
        opp.relevance_score = eval_result.relevance_score
        opp.reasoning = eval_result.reasoning
        opp.difficulty_level = eval_result.difficulty_level
        opp.is_urgent = eval_result.is_urgent
        
        # Save to DB
        database.save_opportunity(opp)
        
        # Collect for email summary
        email_opps.append(opp)
        
        # Auto-draft if highly relevant
        if opp.relevance_score >= 80:
            existing_draft = database.get_draft(opp.id)
            if not existing_draft:
                print(f"Generating draft for high-value opportunity: {opp.title}")
                draft = generate_application_draft(profile, opp)
                database.save_draft(opp.id, draft)

    print("Scan complete.")
    
    # Send email summary for all scanned opps
    if email_opps:
        from notifier import send_email_summary
        send_email_summary(email_opps)

if __name__ == "__main__":
    # Ensure DB is initialized
    database.init_db()
    
    # Run once immediately on startup
    scan_and_evaluate()
    
    # Set up scheduler
    scheduler = BlockingScheduler()
    # Run every 6 hours (Prototype scale)
    scheduler.add_job(scan_and_evaluate, 'interval', hours=6)
    print("Scheduler running. Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
