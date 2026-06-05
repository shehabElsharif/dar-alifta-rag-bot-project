from django.urls import path
from chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("", views.chat_page, name="chat_page"),
    path("api/chat/", views.api_chat, name="api_chat"),
]
