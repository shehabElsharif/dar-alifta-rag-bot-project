import os
import django
import json
import logging

# Set up logging to print to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from chatbot.views import api_chat

rf = RequestFactory()

test_queries = [
    "السلام عليكم كيف حالك",
    "ما حكم من أفطر متعمدا في رمضان؟",
    "ما حكم صلاة الكسوف؟",
    "how much is a gram of gold?"
]

for query in test_queries:
    print(f"\n--- TESTING QUERY: {query} ---")
    request = rf.post('/api/chat/', data=json.dumps({"message": query}), content_type='application/json')
    response = api_chat(request)
    print(f"Status Code: {response.status_code}")
    try:
        data = json.loads(response.content.decode('utf-8'))
        print("Response data keys:", list(data.keys()))
        if "response" in data:
            print("Response preview:", data["response"][:200])
        if "error" in data:
            print("Error details:", data["error"])
    except Exception as e:
        print("Failed to parse JSON response:", e)
        print("Raw content:", response.content)
    print("-" * 50)
