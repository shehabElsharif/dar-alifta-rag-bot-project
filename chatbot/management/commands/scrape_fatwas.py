import time
import sys
import logging
from django.core.management.base import BaseCommand
from chatbot.services.scraper import FatwaScraper

logger = logging.getLogger("chatbot")

class Command(BaseCommand):
    help = "Scrape fatwas from ifta.ly and load them into Supabase."

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform a full scan (re-scrapes all pages, skips existing, but does not stop on existing)'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=None,
            help='Maximum number of pages to scan (default: 100 for full, 10 for incremental)'
        )
        parser.add_argument(
            '--per-page',
            type=int,
            default=20,
            help='Number of posts to fetch per page (default: 20)'
        )
        parser.add_argument(
            '--consecutive-limit',
            type=int,
            default=3,
            help='Stop incremental scrape after this many consecutive existing posts (default: 3)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run the scraper periodically in a background loop'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Daemon run interval in minutes (default: 60)'
        )

    def run_once(self, scraper, options):
        full_scan = options['full']
        per_page = options['per_page']
        consecutive_limit = options['consecutive_limit']
        
        # Determine default max pages if not specified
        max_pages = options['max_pages']
        if max_pages is None:
            max_pages = 100 if full_scan else 10

        self.stdout.write(self.style.WARNING(
            f"Starting scan (Full Scan: {full_scan}, Max Pages: {max_pages}, Per Page: {per_page})"
        ))
        
        try:
            results = scraper.run_scrape(
                max_pages=max_pages,
                per_page=per_page,
                consecutive_existing_limit=consecutive_limit,
                full_scan=full_scan
            )
            self.stdout.write(self.style.SUCCESS(results["summary"]))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during scrape: {e}"))
            logger.exception("Scraper failed")

    def handle(self, *args, **options):
        scraper = FatwaScraper()
        daemon_mode = options['daemon']
        interval_minutes = options['interval']

        if not daemon_mode:
            self.run_once(scraper, options)
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Starting scraper daemon. Scrape interval: {interval_minutes} minutes."
            ))
            
            try:
                while True:
                    self.stdout.write(f"\n--- Periodic Scrape Started: {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
                    # Run the scraper
                    self.run_once(scraper, options)
                    self.stdout.write(f"--- Periodic Scrape Finished. Next run in {interval_minutes} minutes. ---\n")
                    
                    # Sleep in 1-second increments so that keyboard interrupt is responsive
                    sleep_seconds = interval_minutes * 60
                    for _ in range(sleep_seconds):
                        time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\nScraper daemon stopped by user."))
                sys.exit(0)
