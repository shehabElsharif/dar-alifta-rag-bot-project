import logging
import requests
import time
from bs4 import BeautifulSoup
from chatbot.services.embedding import EmbeddingService
from chatbot.services.supabase_db import SupabaseService

logger = logging.getLogger(__name__)

class FatwaScraper:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.supabase_service = SupabaseService()
        self.base_url = "https://ifta.ly/wp-json/wp/v2/posts"

    def strip_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        # BeautifulSoup is used to remove HTML tags and extract clean Arabic text
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator=" ", strip=True)

    def fetch_posts(self, page=1, per_page=20):
        url = f"{self.base_url}?page={page}&per_page={per_page}"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Error fetching page {page} from API: {response.status_code}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Network error when fetching page {page}: {e}")
            return None

    def run_scrape(self, max_pages=100, per_page=20, consecutive_existing_limit=3, full_scan=False):
        """
        Runs the scraper.
        
        Args:
            max_pages (int): Maximum pages to scrape.
            per_page (int): Number of posts per page.
            consecutive_existing_limit (int): In incremental mode (full_scan=False), 
                                              stop scraping if we find this many consecutive already-existing posts.
            full_scan (bool): If True, does not stop when hitting existing posts (scrapes all pages up to max_pages).
        """
        from django.utils import timezone
        from chatbot.models import ScraperLog

        logger.info(f"Starting fatwa scrape (full_scan={full_scan}, max_pages={max_pages}, per_page={per_page})...")
        
        # Create a DB log entry
        log_entry = ScraperLog.objects.create(status='RUNNING')

        try:
            page = 1
            total_added = 0
            total_skipped = 0
            consecutive_existing = 0
            stop_scraping = False

            while page <= max_pages and not stop_scraping:
                logger.info(f"Scraping page {page}...")
                posts = self.fetch_posts(page=page, per_page=per_page)

                if not posts:
                    logger.info("No more posts or error occurred. Ending pagination.")
                    break

                logger.info(f"Found {len(posts)} posts on page {page}.")

                for post in posts:
                    post_id = post.get("id")
                    if not post_id:
                        continue

                    # Check if this fatwa already exists in Supabase database
                    exists = self.supabase_service.fatwa_exists(post_id)
                    if exists:
                        total_skipped += 1
                        logger.info(f"Fatwa {post_id} already exists in database. Skipped.")
                        
                        if not full_scan:
                            consecutive_existing += 1
                            if consecutive_existing >= consecutive_existing_limit:
                                logger.info(f"Hit limit of {consecutive_existing_limit} consecutive existing posts. Stopping incremental scan.")
                                stop_scraping = True
                                break
                        continue

                    # Reset consecutive counter since we found a new post
                    consecutive_existing = 0

                    title = post.get("title", {}).get("rendered", "")
                    raw_content = post.get("content", {}).get("rendered", "")
                    clean_content = self.strip_html(raw_content)
                    date = post.get("date")
                    link = post.get("link")
                    categories = post.get("categories", [])
                    tags = post.get("tags", [])

                    # Format the text to embed
                    text_to_embed = f"سؤال/فتوى: {title}\n\nالإجابة: {clean_content}"

                    # Truncate to ~20,000 characters to stay safely under limit
                    if len(text_to_embed) > 20000:
                        text_to_embed = text_to_embed[:20000]

                    logger.info(f"Generating embedding for fatwa {post_id}...")
                    embedding = self.embedding_service.get_embedding(text_to_embed)
                    if not embedding:
                        logger.error(f"Failed to generate embedding for fatwa {post_id}. Skipping insertion.")
                        continue

                    fatwa_data = {
                        "id": post_id,
                        "title": title,
                        "content": clean_content,
                        "date": date,
                        "link": link,
                        "categories": categories,
                        "tags": tags,
                        "embedding": embedding
                    }

                    logger.info(f"Inserting fatwa {post_id} into Supabase...")
                    success = False
                    for attempt in range(3):
                        if self.supabase_service.upsert_fatwa(fatwa_data):
                            success = True
                            break
                        logger.warning(f"Retry upsert for fatwa {post_id} (attempt {attempt + 1})...")
                        time.sleep(2)

                    if success:
                        logger.info(f"Successfully added fatwa {post_id} to database.")
                        total_added += 1
                    else:
                        logger.error(f"Failed to add fatwa {post_id} to database after 3 attempts.")

                if len(posts) < per_page:
                    logger.info("Last page reached (fewer posts returned than per_page).")
                    break

                page += 1

            summary = f"Scrape complete. Added {total_added} new fatwas, skipped {total_skipped} existing fatwas."
            logger.info(summary)
            
            # Save success log
            log_entry.status = 'SUCCESS'
            log_entry.added_count = total_added
            log_entry.skipped_count = total_skipped
            log_entry.end_time = timezone.now()
            log_entry.summary = summary
            log_entry.save()

            return {"added": total_added, "skipped": total_skipped, "summary": summary}

        except Exception as e:
            # Save failure log
            log_entry.status = 'FAILED'
            log_entry.end_time = timezone.now()
            log_entry.summary = f"Error during execution: {str(e)}"
            log_entry.save()
            logger.error(f"Scraper encountered exception: {e}")
            raise e

