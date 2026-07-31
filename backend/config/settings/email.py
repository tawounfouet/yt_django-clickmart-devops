EMAIL_BACKEND_TYPE = env('EMAIL_BACKEND_TYPE', default='console')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@clickmart.local')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@clickmart.local')

if EMAIL_BACKEND_TYPE == 'resend':
    EMAIL_BACKEND = 'core.mail.ResendEmailBackend'
    RESEND_API_KEY = env('RESEND_API_KEY')
elif EMAIL_BACKEND_TYPE == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
