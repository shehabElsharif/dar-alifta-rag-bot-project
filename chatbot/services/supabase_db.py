import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        
        if not self.url or not self.key:
            logger.error("Supabase credentials not found in environment variables.")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.url, self.key)
            except Exception as e:
                logger.exception(f"Failed to initialize Supabase client: {e}")
                self.client = None

    def search_similar_fatwas(self, query_embedding, match_threshold=0.4, match_count=5):
        """
        Calls the 'match_fatwas' RPC function in Supabase using the query embedding.
        Returns a list of dicts with keys: id, title, content, link, similarity
        """
        if not self.client:
            logger.error("Supabase client is not initialized.")
            return []
            
        if not query_embedding:
            logger.error("Query embedding is required for fatwa similarity search.")
            return []

        try:
            # Execute the pgvector match_fatwas stored procedure
            response = self.client.rpc("match_fatwas", {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count
            }).execute()
            
            # response.data contains the list of fatwas matched
            return response.data if response.data else []
        except Exception as e:
            logger.exception(f"Error querying match_fatwas RPC: {e}")
            return []
