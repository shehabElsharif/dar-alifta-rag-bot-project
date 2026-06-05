import os
import re
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

    def generate_fatwa_response(self, user_message: str, fatwas: list) -> dict:
        """
        Generates an answer based on the provided fatwas.
        Returns a dict: {"found": True/False, "answer": "..."}
        - found=True  → context was sufficient; answer contains the fatwa-based response.
        - found=False → context was insufficient; caller should use the official fallback.
        """
        system_instructions = (
            "أنت المساعد الذكي الرسمي والممثل لجهة \"دار الإفتاء الليبية\".\n"
            "مهمتك الأساسية والوحيدة هي الإجابة عن أسئلة واستفسارات المستخدمين الفقهية والشرعية باللغة العربية الفصحى، وبدقة ومهنية عالية.\n\n"
            "يجب عليك الالتزام المطلق بالقواعد التالية:\n"
            "1. الاعتماد حصراً على نصوص الفتاوى المقدمة لك في قسم \"سياق الفتاوى\" أدناه. يمنع منعاً باتاً اختراع أو تأليف أي أحكام فقهية من معلوماتك العامة خارج هذا السياق.\n"
            "2. اجعل إجابتك واضحة، سهلة الفهم، ومباشرة.\n"
            "3. لزيادة الموثوقية، احرص دائماً على الإشارة لمصدر الفتوى (رابطها أو عنوانها) بناءً على ما هو متوفر في السياق.\n"
            "4. تحدث دائماً بصفة الاحترام والتقدير للسائل.\n\n"
            "يجب أن يكون ردك حصرياً بصيغة JSON صالحة (Valid JSON) فقط، بدون أي نص أو علامات اقتباس برمجية خارجها:\n"
            "- إذا كان السياق يحتوي على إجابة واضحة وشافية: {\"found\": true, \"answer\": \"إجابتك الكاملة هنا بالعربية الفصحى\"}\n"
            "- إذا كان السياق لا يحتوي على إجابة كافية لسؤال المستخدم: {\"found\": false, \"answer\": \"\"}\n"
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
        
        raw = self._call_llm(messages)
        if not raw:
            logger.error("LLM returned no response for fatwa generation.")
            return {"found": False, "answer": ""}

        # If the gateway already parsed it as a dict, use it directly
        if isinstance(raw, dict):
            return {"found": bool(raw.get("found", False)), "answer": str(raw.get("answer", ""))}

        # Otherwise strip markdown fences and parse JSON
        clean = str(raw).strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            result = json.loads(clean)
            return {"found": bool(result.get("found", False)), "answer": str(result.get("answer", ""))}
        except Exception as e:
            logger.warning(f"Strict JSON parse failed (likely unescaped quotes in answer): {e}. Attempting regex extraction...")

            # Stage 2: regex extraction — robust against unescaped quotes inside the answer.
            # Extract "found" value
            found = True
            found_match = re.search(r'"found"\s*:\s*(true|false)', clean, re.IGNORECASE)
            if found_match:
                found = found_match.group(1).lower() == "true"

            # Extract everything after the first occurrence of '"answer": "'
            answer = ""
            answer_marker = '"answer": "'
            if answer_marker in clean:
                after_marker = clean.split(answer_marker, 1)[1]
                # Strip trailing closing JSON characters from the end
                # Walk backwards to drop the final '"' or '"}'
                after_marker = after_marker.rstrip()
                if after_marker.endswith('"}'):
                    after_marker = after_marker[:-2]
                elif after_marker.endswith('"'):
                    after_marker = after_marker[:-1]
                answer = after_marker.strip()

            if answer:
                logger.info(f"Regex extraction succeeded. found={found}, answer length={len(answer)}")
                return {"found": found, "answer": answer}

            # Stage 3: last resort — the LLM ignored JSON entirely; use the raw text as the answer.
            logger.warning("Regex extraction also failed. Returning raw text as answer.")
            return {"found": True, "answer": clean}
