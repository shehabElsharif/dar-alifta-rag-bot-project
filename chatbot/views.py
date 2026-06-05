import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chatbot.services.embedding import EmbeddingService
from chatbot.services.supabase_db import SupabaseService
from chatbot.services.llm import LLMService

logger = logging.getLogger(__name__)

# Initialize services lazily
_embedding_service = None
_supabase_service = None
_llm_service = None

def get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

def get_supabase_service():
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

def chat_page(request):
    """
    Renders the chat interface.
    """
    return render(request, "chatbot/index.html")

@csrf_exempt
def api_chat(request):
    """
    API endpoint that accepts JSON {"message": "..."} and orchestrates RAG.
    """
    if request.method != "POST":
        logger.warning(f"Rejected non-POST request of type {request.method}")
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)
        
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
    except Exception as e:
        logger.error(f"Failed to parse incoming JSON payload: {e}")
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        
    if not user_message:
        logger.warning("Received empty user message.")
        return JsonResponse({"error": "Message is required."}, status=400)

    # Log incoming user message
    logger.info("=" * 60)
    logger.info(f"INCOMING REQUEST: User Message = '{user_message}'")
    logger.info("=" * 60)

    try:
        llm_service = get_llm_service()
        
        # 1. Classify Intent
        logger.info("Step 1: Commencing Intent Classification via Llama 3.1...")
        intent = llm_service.classify_intent(user_message)
        logger.info(f"Step 1 Complete: Intent classified as '{intent}'")
        
        if intent == "GREETING":
            logger.info("Intent is GREETING. Bypassing RAG search database step.")
            logger.info("Calling LLM to generate warm welcome response...")
            response_text = llm_service.generate_general_response(user_message)
            logger.info(f"Greeting response generated successfully: '{response_text}'")
            logger.info("Sending response to client.")
            logger.info("=" * 60)
            return JsonResponse({
                "response": response_text,
                "intent": intent,
                "sources": []
            })
            
        elif intent == "OUT_OF_SCOPE":
            logger.info("Intent is OUT_OF_SCOPE. Bypassing RAG search database step and returning refusal.")
            response_text = (
                "عذراً، أنا مساعد فقهي مخصص للإجابة عن الأسئلة الشرعية والفقهية بناءً على فتاوى دار الإفتاء الليبية الرسمية فقط. "
                "لا يمكنني الإجابة عن الأسئلة العامة أو الاستفسارات الخارجة عن هذا النطاق."
            )
            logger.info("Sending out-of-scope refusal to client.")
            logger.info("=" * 60)
            return JsonResponse({
                "response": response_text,
                "intent": intent,
                "sources": []
            })
            
        # 2. FATWA_QUERY: Proceed with RAG
        logger.info("Intent is FATWA_QUERY. Initiating RAG process.")
        embedding_service = get_embedding_service()
        supabase_service = get_supabase_service()
        
        # Generate query embedding
        logger.info("Step 2: Vectorizing user query using Cloudflare BGE-M3...")
        query_embedding = embedding_service.get_embedding(user_message)
        if not query_embedding:
            logger.error("Step 2 Failed: Could not generate vector embedding for the query.")
            response_text = "عذراً، واجهنا مشكلة في معالجة طلبك حالياً (فشل في استخراج المتجهات). يرجى المحاولة لاحقاً."
            return JsonResponse({
                "response": response_text,
                "intent": "ERROR",
                "sources": []
            })
        logger.info(f"Step 2 Complete: Embedding generated successfully. Vector length: {len(query_embedding)}")
            
        # Search similar fatwas
        logger.info("Step 3: Querying Supabase pgvector 'match_fatwas' RPC (threshold=0.30, count=3)...")
        fatwas = supabase_service.search_similar_fatwas(query_embedding, match_threshold=0.30, match_count=3)
        logger.info(f"Step 3 Complete: Supabase similarity search completed. Retrieved {len(fatwas)} fatwas.")
        
        # Format sources for user visibility (exluding the large embedding vector)
        cleaned_sources = []
        for i, fatwa in enumerate(fatwas):
            similarity_pct = int(fatwa.get("similarity", 0) * 100)
            logger.info(f"  - Source [{i+1}] ID: {fatwa.get('id')} | Title: '{fatwa.get('title')}' | Similarity: {similarity_pct}%")
            cleaned_sources.append({
                "id": fatwa.get("id"),
                "title": fatwa.get("title"),
                "content": fatwa.get("content"),
                "link": fatwa.get("link"),
                "similarity": fatwa.get("similarity")
            })
            
        # 3. Generate answer based on context
        logger.info("Step 4: Preparing prompt and context for answer generation...")
        official_fallback = (
            "عذراً، لم أتمكن من العثور على فتوى مسجلة ومطابقة لسؤالك في قاعدة بيانات دار الإفتاء الحالية. "
            "يرجى صياغة السؤال بشكل مختلف أو استشارة أحد المفتين مباشرة."
        )

        if not cleaned_sources:
            logger.info("Step 4: No matching fatwas met the similarity threshold. Triggering direct fallback.")
            response_text = official_fallback
        else:
            logger.info("Step 5: Calling LLM with fatwa context for structured JSON answer...")
            llm_result = llm_service.generate_fatwa_response(user_message, cleaned_sources)
            logger.info(f"Step 5 Complete: LLM responded with found={llm_result['found']}.")

            if llm_result["found"] and llm_result["answer"]:
                logger.info("Context was sufficient. Using LLM answer.")
                response_text = llm_result["answer"]
            else:
                logger.info("LLM signalled context insufficient (found=False). Triggering official fallback.")
                response_text = official_fallback
                cleaned_sources = []  # don't show source cards when falling back
            
        logger.info("=" * 60)
        logger.info(f"FINAL OUTGOING RESPONSE: '{response_text[:150]}...'")
        logger.info("=" * 60)

        return JsonResponse({
            "response": response_text,
            "intent": intent,
            "sources": cleaned_sources
        })
        
    except Exception as e:
        logger.exception(f"Error in api_chat view: {e}")
        return JsonResponse({"error": "Internal server error occurred."}, status=500)
