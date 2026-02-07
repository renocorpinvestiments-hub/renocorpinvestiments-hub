# core/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.timezone = "UTC"

app.conf.beat_schedule = {
    # ----------------------------------
    # Sunday Payroll
    # ----------------------------------
    "payroll-every-sunday-midnight": {
        "task": "transactions.run_sunday_payroll",
        "schedule": crontab(hour=0, minute=0, day_of_week="sun"),
        "options": {"queue": "high_priority"},
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f"[Celery Debug Task] Request: {self.request!r}")
