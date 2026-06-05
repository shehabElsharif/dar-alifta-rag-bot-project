from django.db import models

class ChatBotSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="Key")
    value = models.TextField(verbose_name="Value")
    description = models.TextField(blank=True, verbose_name="Description")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ChatBot Setting"
        verbose_name_plural = "ChatBot Settings"

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_val(cls, key: str, default=None):
        try:
            setting = cls.objects.get(key=key)
            return setting.value
        except cls.DoesNotExist:
            import os
            # Fallback to env or default
            return os.environ.get(key, default)

    @classmethod
    def set_val(cls, key: str, value, description=""):
        cls.objects.update_or_create(
            key=key,
            defaults={'value': str(value), 'description': description}
        )

class ScraperLog(models.Model):
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='RUNNING')  # RUNNING, SUCCESS, FAILED
    added_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = "Scraper Log"
        verbose_name_plural = "Scraper Logs"

    def __str__(self):
        return f"Scrape on {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.status}"

class ChatLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user_message = models.TextField()
    intent = models.CharField(max_length=50)
    response_text = models.TextField()
    matched_sources_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Chat Log"
        verbose_name_plural = "Chat Logs"

    def __str__(self):
        return f"Chat at {self.timestamp.strftime('%Y-%m-%d %H:%M')} ({self.intent})"
