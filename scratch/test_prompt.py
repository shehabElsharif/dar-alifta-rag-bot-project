import os
import requests
from dotenv import load_dotenv

load_dotenv()

account_id = os.environ.get("CF_ACCOUNT_ID")
api_token = os.environ.get("CF_API_TOKEN")
# Using Llama 4 Scout MoE model
url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-4-scout-17b-16e-instruct"

query = "ما حكم تافطر متعمد"

strict_instructions = (
    "أنت المساعد الذكي الرسمي والممثل لجهة \"دار الإفتاء الليبية\".\n"
    "مهمتك الأساسية والوحيدة هي الإجابة عن أسئلة واستفسارات المستخدمين الفقهية والشرعية باللغة العربية الفصحى، وبدقة ومهنية عالية.\n\n"
    "يجب عليك الالتزام المطلق بالقواعد التالية:\n"
    "1. الاعتماد حصراً على نصوص الفتاوى المقدمة لك في قسم \"سياق الفتاوى\" أدناه. يمنع منعاً باتاً اختراع، أو تأليف، أو استنتاج أي أحكام فقهية من معلوماتك العامة خارج هذا السياق.\n"
    "2. إذا كان السياق المقدم لا يحتوي على إجابة واضحة وشافية لسؤال المستخدم، يجب عليك الاعتذار بأدب والقول: \"عذراً، لم أتمكن من العثور على فتوى مسجلة ومطابقة لسؤالك في قاعدة بيانات دار الإفتاء الحالية. يرجى صياغة السؤال بشكل مختلف أو استشارة أحد المفتين مباشرة.\"\n"
    "3. اجعل إجابتك واضحة، سهلة الفهم، ومباشرة.\n"
    "4. لزيادة الموثوقية، احرص دائماً على الإشارة لمصدر الفتوى (مثل إرفاق الرابط أو عنوان الفتوى) بناءً على ما هو متوفر في السياق.\n"
    "5. تحدث دائماً بصفة الاحترام والتقدير للسائل.\n"
)

def run_test(instructions, test_fatwas):
    context_parts = []
    for f in test_fatwas:
        context_parts.append(f"العنوان: {f['title']}\nنص الفتوى: {f['content']}\nالرابط: {f['link']}")
    context_string = "\n---\n".join(context_parts)
    
    full_prompt = (
        f"{instructions}\n"
        f"---\n"
        f"سياق الفتاوى المستخرج من قاعدة البيانات لحالة المستخدم الحالية:\n\n"
        f"{context_string}\n"
        f"---\n"
    )
    
    messages = [
        {"role": "system", "content": full_prompt},
        {"role": "user", "content": f"السؤال الموجه من المستخدم:\n{query}"}
    ]
    
    response = requests.post(
        url, 
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        json={"messages": messages}
    )
    return response.status_code, response.text

related_fatwas = [
    {
        "title": "حكم من أفطر رمضانَ متعمدا سنوات متعددة",
        "content": "بسم الله الرحمن الرحيم رقم الفتوى (  ) ورد إلى دار الإفتاء السؤال التالي: رجل يبلغ من العمر ستّاً وأربعين سنة، وكان حين بلغ من العمر السابعة عشرة قد أفطر في شهر رمضان متعمّداً وبدون عذر، واستمر على ذلك حتى بلغ من العمر إحدى وعشرين سنة، أي أفطر شهر رمضان متعمّداً خمس سنوات من عمره، فكيف يكفر عن الشهور التي أفطرها في تلك السنوات، وهل يمكنه أن يصوم الأيام المستحب صيامها مثل صيام يوم عرفة وعاشوراء قبل الكفارة؟. الجواب: الحمد لله، والصلاة والسلام على رسول الله، وعلى آله وصحبه ومن والاه. أما بعد: فإن من أفطر في نهار رمضان بغير عذر شرعي، قد ارتكب إثماً عظيماً، وأتى كبيرة من كبائر الذنوب بانتهاكه حرمة ركن من أركان الإسلام، ويجب على من فعل ذلك المسارعة بالتوبة والاستغفار، وعليه القضاء والكفارة عن كلّ يوم أفطر فيه بغير عذر شرعي والكفارة: عتق رقبة، أو صيام شهرين متتابعين، أو إطعام ستين مسكيناً، وهذه الكفارة على التخيير، ويكره تقديم النفل من الصيام على صيام القضاء والكفارة؛ لأن أداء الفرض أهم من التطوع، قال الدردير: “(وَ) كُرِهَ (تَطَوُّعٌ) بِصِيَامٍ (قَبْلَ) صَوْمِ (نَذْرٍ) غَيْرِ مُعَيَّنٍ (أَوْ",
        "link": "https://ifta.ly/ramadan-deliberate/"
    }
]

unrelated_fatwas = [
    {
        "title": "الصلاة في السفينة والطائرة",
        "content": "بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيمِ رقم الفتوى ( 1024 ) ورد إلى دار الإفتاء السؤال التالي: ما حكم صلاة الفريضة في السفينة أو الطائرة؟ الجواب: الحمد لله، والصلاة والسلام على رسول الله... تجوز الصلاة في السفينة والطائرة مع استقبال القبلة والقيام والركوع والسجود إن تيسر ذلك، وإلا صلى بحسب حاله.",
        "link": "https://ifta.ly/1024/"
    }
]

print("Testing Llama 4 Scout Strict Instructions with RELATED context:")
print("-" * 50)
code, text = run_test(strict_instructions, related_fatwas)
print(f"Status Code: {code}")
print(text)
print("=" * 50)

print("\nTesting Llama 4 Scout Strict Instructions with UNRELATED context:")
print("-" * 50)
code2, text2 = run_test(strict_instructions, unrelated_fatwas)
print(f"Status Code: {code2}")
print(text2)
print("=" * 50)
