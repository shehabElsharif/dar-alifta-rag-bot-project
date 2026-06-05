import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.services.embedding import EmbeddingService
from chatbot.services.supabase_db import SupabaseService

load_dotenv()

def main():
    embedding_service = EmbeddingService()
    supabase_service = SupabaseService()
    
    query = "ما حكم تافطر متعمد"
    print(f"Query: {query}")
    
    embedding = embedding_service.get_embedding(query)
    fatwas = supabase_service.search_similar_fatwas(embedding, match_threshold=0.3, match_count=4)
    
    # Print only Fatwa 1 and 2
    for i, f in enumerate(fatwas[:2]):
        print(f"\n--- Fatwa {i+1} ---")
        print(f"Title: {f.get('title')}")
        print(f"Similarity: {f.get('similarity')}")
        print(f"Content Length: {len(f.get('content', ''))}")
        print(f"Full Content Snippet:\n{f.get('content')[:1000]}")

if __name__ == "__main__":
    main()
