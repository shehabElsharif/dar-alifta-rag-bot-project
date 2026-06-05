import os
import requests
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.account_id = os.environ.get("CF_ACCOUNT_ID")
        self.api_token = os.environ.get("CF_API_TOKEN")
        self.model = "@cf/baai/bge-m3"
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        
        if not self.account_id or not self.api_token:
            logger.error("Cloudflare Worker AI credentials not found in environment variables.")

    def get_embedding(self, text: str):
        """
        Generates a 1024-dimensional embedding vector for the given text.
        """
        if not text:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # The Cloudflare AI output for embeddings is in data["result"]["data"][0]
                    return data["result"]["data"][0]
                else:
                    logger.error(f"Cloudflare AI returned success=False: {data}")
            else:
                logger.error(f"Cloudflare AI request failed (Status {response.status_code}): {response.text}")
        except Exception as e:
            logger.exception(f"Error generating embedding: {e}")
            
        return None
