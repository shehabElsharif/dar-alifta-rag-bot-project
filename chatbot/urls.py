from django.urls import path
from chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("", views.chat_page, name="chat_page"),
    path("api/chat/", views.api_chat, name="api_chat"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/save-settings/", views.save_settings, name="save_settings"),
    path("admin-dashboard/run-scraper/", views.run_scraper_api, name="run_scraper_api"),
]

