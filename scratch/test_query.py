import os
import sys
from dotenv import load_dotenv

# Add project directory to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.services.embedding import EmbeddingService
from chatbot.services.supabase_db import SupabaseService
from chatbot.services.llm import LLMService

load_dotenv()

def main():
    print("Initializing services...")
    embedding_service = EmbeddingService()
    supabase_service = SupabaseService()
    llm_service = LLMService()
    
    query = "ما حكم الحبس على الذكور دون الإناث في الميراث أو الأحباس؟"
    print(f"\nUser Query: '{query}'")
    
    # 1. Classify Intent
    print("\n1. Classifying Intent...")
    intent = llm_service.classify_intent(query)
    print(f"Intended Category: {intent}")
    
    # 2. Get Embedding
    print("\n2. Generating Embedding...")
    embedding = embedding_service.get_embedding(query)
    if not embedding:
        print("Failed to generate embedding.")
        return
    print(f"Embedding length: {len(embedding)}")
    
    # 3. Match Fatwas
    print("\n3. Matching similar fatwas in Supabase...")
    fatwas = supabase_service.search_similar_fatwas(embedding, match_threshold=0.3, match_count=5)
    print(f"Matched {len(fatwas)} fatwas:")
    for i, fatwa in enumerate(fatwas):
        print(f"[{i+1}] Title: {fatwa.get('title')} (Similarity: {fatwa.get('similarity'):.4f})")
        print(f"    Link: {fatwa.get('link')}")
        print(f"    Snippet: {fatwa.get('content')[:200]}...\n")
        
    # 4. Generate LLM Answer
    print("\n4. Generating Answer via LLM Llama-3.1...")
    answer = llm_service.generate_fatwa_response(query, fatwas)
    print(f"\nAI Response:\n{answer}")

if __name__ == "__main__":
    main()
