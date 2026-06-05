import os
import sys
import time
import threading
import logging
from django.apps import AppConfig

logger = logging.getLogger("chatbot")

class ChatbotConfig(AppConfig):
    name = 'chatbot'

    def ready(self):
        auto_run = os.environ.get("SCRAPER_AUTO_RUN", "False").lower() == "true"
        if auto_run:
            is_run_main = os.environ.get('RUN_MAIN') == 'true'
            # If the reload command is used, we check if we are in the main process
            is_runserver = 'runserver' in sys.argv
            
            if not is_runserver or is_run_main:
                from chatbot.services.scraper import FatwaScraper
                
                def run_scheduler():
                    # Wait 10 seconds to ensure database/network/app initialization is complete
                    time.sleep(10)
                    scraper = FatwaScraper()
                    interval_mins = int(os.environ.get("SCRAPER_INTERVAL_MINUTES", "1440"))
                    logger.info(f"Background scraper thread started. Interval: {interval_mins} minutes.")
                    
                    while True:
                        try:
                            logger.info("Background scraper thread executing scheduled incremental scrape...")
                            scraper.run_scrape(
                                max_pages=10,
                                per_page=20,
                                consecutive_existing_limit=3,
                                full_scan=False
                            )
                        except Exception as e:
                            logger.error(f"Error in background scraper thread: {e}")
                        
                        # Sleep in 1-second chunks to react gracefully to application exit
                        for _ in range(interval_mins * 60):
                            time.sleep(1)
                
                thread = threading.Thread(target=run_scheduler, daemon=True, name="FatwaScraperThread")
                thread.start()

