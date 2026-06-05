import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.account_id = os.environ.get("CF_ACCOUNT_ID")
        self.api_token = os.environ.get("CF_API_TOKEN")
        self.model = "@cf/meta/llama-4-scout-17b-16e-instruct"
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"

        if not self.account_id or not self.api_token:
            logger.error("Cloudflare Worker AI credentials not found in environment variables.")

    def _call_llm(self, messages, json_mode=False):
        """
        Helper method to call Cloudflare Workers AI LLM API.
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {"messages": messages}
        
        # Cloudflare Workers AI supports response_format in some models,
        # but to be safe and compatible, we can enforce JSON via prompts.
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data["result"]["response"]
                else:
                    logger.error(f"Cloudflare LLM returned success=False: {data}")
            else:
                logger.error(f"Cloudflare LLM request failed (Status {response.status_code}): {response.text}")
        except Exception as e:
            logger.exception(f"Error calling Cloudflare LLM: {e}")
            
        return None

    def classify_intent(self, user_message: str) -> str:
        """
        Classifies the intent of the user's message using the LLM.
        Returns 'FATWA_QUERY', 'GREETING', or 'OUT_OF_SCOPE'.
        """
        system_prompt = (
            "أنت نظام توجيه ذكي (Router) يعمل ضمن نظام 'دار الإفتاء الليبية'.\n"
            "مهمتك الوحيدة هي قراءة رسالة المستخدم وتصنيف نيتها (Intent Classification) إلى واحدة من الفئات الثلاث التالية فقط:\n\n"
            "1. 'GREETING':\n"
            "استخدم هذا التصنيف إذا كانت الرسالة عبارة عن تحية، ترحيب، سؤال عن الحال، أو عبارات مجاملة عامة (مثال: \"السلام عليكم\"، \"مرحبا\"، \"كيف حالك\"، \"صباح الخير\"، \"أهلاً\").\n\n"
            "2. 'FATWA_QUERY':\n"
            "استخدم هذا التصنيف إذا كان المستخدم يطرح سؤالاً فقهياً، شرعياً، أو يستفسر عن حكم ديني أو حلال وحرام وكل ما يتعلق بالشريعة الإسلامية ويحتاج لفتوى من الدار (مثال: \"ما حكم صلاة الكسوف؟\"، \"كيف توزع التركة؟\"، \"ما حكم بيع التقسيط؟\").\n\n"
            "3. 'OUT_OF_SCOPE':\n"
            "استخدم هذا التصنيف إذا كان المستخدم يسأل سؤالاً عاماً غير فقهي وغير شرعي، أو يطلب مهام عامة خارجة عن نطاق الفتوى والدين (مثال: \"كم سعر جرام الذهب؟\"، \"اكتب كود بريد إلكتروني بالبايثون\"، \"ما عاصمة فرنسا؟\"، \"من هو صلاح الدين؟\").\n\n"
            "يجب أن يكون ردك حصرياً بصيغة JSON صالحة (Valid JSON) كما في المثال التالي، بدون أي نص أو شرح أو علامات اقتباس برمجية إضافية لكي يتمكن النظام من قراءتها برمجياً:\n"
            "{\n"
            "  \"intent\": \"FATWA_QUERY\"\n"
            "}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"رسالة المستخدم:\n{user_message}"}
        ]
        
        response_text = self._call_llm(messages)
        if not response_text:
            return "FATWA_QUERY"  # Fallback to search if LLM fails
            
        if isinstance(response_text, dict):
            intent = response_text.get("intent", "FATWA_QUERY")
            if intent in ["FATWA_QUERY", "OUT_OF_SCOPE", "GREETING"]:
                return intent
            return "FATWA_QUERY"
            
        # Clean response in case LLM wrapped it in markdown code blocks
        clean_text = str(response_text).strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        try:
            result = json.loads(clean_text)
            intent = result.get("intent", "FATWA_QUERY")
            if intent in ["FATWA_QUERY", "OUT_OF_SCOPE", "GREETING"]:
                return intent
        except Exception as e:
            logger.warning(f"Failed to parse intent JSON: {response_text}. Error: {e}")
            # Try a simple text search as backup
            str_resp = str(response_text)
            if "GREETING" in str_resp:
                return "GREETING"
            if "OUT_OF_SCOPE" in str_resp:
                return "OUT_OF_SCOPE"
                
        return "FATWA_QUERY"

    def generate_general_response(self, user_message: str) -> str:
        """
        Generates a friendly response for out-of-scope queries (like greetings).
        """
        system_prompt = (
            "أنت المساعد الذكي الرسمي لدار الإفتاء الليبية.\n"
            "رسالة المستخدم الحالية مصنفة كرسالة عامة (مثل التحية أو الاستفسار العام) وليست سؤالاً فقهياً مباشراً.\n"
            "قم بالرد على رسالة المستخدم بلطف واحترام باللغة العربية الفصحى، ورحب به، ثم ذكّره بلطف بأنك هنا لمساعدته في الإجابات الشرعية والفقهية المستمدة من فتاوى دار الإفتاء الليبية."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = self._call_llm(messages)
        if response:
            return response
            
        return "مرحباً بك. أنا المساعد الذكي لدار الإفتاء الليبية. كيف يمكنني مساعدتك اليوم في الاستفسارات الشرعية والفقهية؟"
    def generate_fatwa_response(self, user_message: str, fatwas: list) -> str:
        """
        Generates an answer based on the provided fatwas using the official strict system prompt.
        """
        system_instructions = (
            "أنت المساعد الذكي الرسمي والممثل لجهة \"دار الإفتاء الليبية\".\n"
            "مهمتك الأساسية والوحيدة هي الإجابة عن أسئلة واستفسارات المستخدمين الفقهية والشرعية باللغة العربية الفصحى، وبدقة ومهنية عالية.\n\n"
            "يجب عليك الالتزام المطلق بالقواعد التالية:\n"
            "1. الاعتماد حصراً على نصوص الفتاوى المقدمة لك في قسم \"سياق الفتاوى\" أدناه. يمنع منعاً باتاً اختراع، أو تأليف، أو استنتاج أي أحكام فقهية من معلوماتك العامة خارج هذا السياق.\n"
            "2. إذا كان السياق المقدم لا يحتوي على إجابة واضحة وشافية لسؤال المستخدم، يجب عليك الاعتذار بأدب والقول: \"عذراً، لم أتمكن من العثور على فتوى مسجلة ومطابقة لسؤالك في قاعدة بيانات دار الإفتاء الحالية. يرجى صياغة السؤال بشكل مختلف أو استشارة أحد المفتين مباشرة.\"\n"
            "3. اجعل إجابتك واضحة، سهلة الفهم، ومباشرة.\n"
            "4. لزيادة الموثوقية، احرص دائماً على الإشارة لمصدر الفتوى (مثل إرفاق الرابط أو عنوان الفتوى) بناءً على ما هو متوفر في السياق.\n"
            "5. تحدث دائماً بصفة الاحترام والتقدير للسائل.\n"
        )
        
        # Build context from matched fatwas
        context_parts = []
        for i, fatwa in enumerate(fatwas):
            context_parts.append(
                f"العنوان: {fatwa.get('title')}\n"
                f"نص الفتوى: {fatwa.get('content')}\n"
                f"الرابط: {fatwa.get('link')}"
            )
            
        context_string = "\n---\n".join(context_parts)
        
        full_system_prompt = (
            f"{system_instructions}\n"
            f"---\n"
            f"سياق الفتاوى المستخرج من قاعدة البيانات لحالة المستخدم الحالية:\n\n"
            f"{context_string}\n"
            f"---\n"
        )
        
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": f"السؤال الموجه من المستخدم:\n{user_message}"}
        ]
        
        response = self._call_llm(messages)
        if response:
            return response
            
        return "عذراً، حدث خطأ أثناء معالجة الإجابة. يرجى المحاولة مرة أخرى."
