# Gunicorn configuration file
# ===========================

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"  # Port 8000 (yoki sizning portingiz)
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # CPU yadrolar * 2 + 1
worker_class = 'sync'  # 'sync', 'gevent', 'eventlet'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# MUHIM: Timeout sozlamalari (Excel upload uchun)
# Excel yuklash 5-10 daqiqa olishi mumkin!
timeout = 600  # 10 daqiqa (600 sekund) - ASOSIY YECHIM!
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'chilonzor_face_login'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (agar kerak bo'lsa)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

print(f"Gunicorn starting with {workers} workers and {timeout}s timeout")
