import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('clickmart')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.task_default_retry_delay = 60
app.conf.task_max_retries = 3
app.conf.task_soft_time_limit = 300
app.conf.task_time_limit = 600
app.conf.result_expires = 3600

app.autodiscover_tasks()
