import os
from datetime import timedelta
from pathlib import Path


# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    load_dotenv = None
    
    
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-698=9lt4($dou4__kd&*tor4j5kp9g#g2mh8bp37v334-c$8h^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

LOCAL_APPS = [
    'apps.accounts',
    'apps.car',
    'apps.master',
    'apps.order',
    'apps.categories',
    'apps.chat',
]

INSTALLED_APPS = [
    'daphne',  # Must be first for WebSocket support
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    'channels',
    *LOCAL_APPS,
]

LOCAL_MIDDLEWARE = [
    'config.middleware.middleware.JsonErrorResponseMiddleware',
    'config.middleware.middleware.Custom404Middleware',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    *LOCAL_MIDDLEWARE,
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ASGI Application for WebSocket support
ASGI_APPLICATION = 'config.asgi.application'

# Channel Layers Configuration (InMemory - no Redis needed)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'checkavto'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', '0576'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
# Production uchun /var/www/media, development uchun local media folder
MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/var/www/media')


LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FileUploadParser",
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    "PAGE_SIZE": 100,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://31.128.43.149:6060",
    "http://31.128.43.149",
    "https://31.128.43.149:6060",
    "https://31.128.43.149",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://31.128.43.149:6060",
    "http://31.128.43.149",
    "https://31.128.43.149:6060",
    "https://31.128.43.149",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

# CORS Headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'pragma',
]

# CORS Methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# CSRF Settings for production
CSRF_COOKIE_SECURE = False  # Set True if using HTTPS
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_COOKIE_NAME = 'csrftoken'

# Session Settings
SESSION_COOKIE_SECURE = False  # Set True if using HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

# Security Settings for development/production
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Change to your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'sobirbobojonov2000@gmail.com'
EMAIL_HOST_PASSWORD = 'harntaefuxuvlqqw'
DEFAULT_FROM_EMAIL = 'sobirbobojonov2000@gmail.com'

# SMSC.ru SMS xizmati sozlamalari
# SMSC_LOGIN = 'sobirjon_0576'  # SMSC.ru login
# SMSC_PASSWORD = '05769452Sobir@#'  # SMSC.ru parol
SMSC_LOGIN = 'Check8Auto'  # SMSC.ru login
SMSC_PASSWORD = '8Check8Auto8'  # SMSC.ru parol
SMSC_API_URL = 'https://smsc.ru/sys/send.php'

# Альфа-Банк REST (шаблоны СБП QR: templates/*.do)
ALFA_PAYMENT_REST_BASE = os.getenv('ALFA_PAYMENT_REST_BASE', '').strip()
ALFA_API_USERNAME = os.getenv('ALFA_API_USERNAME', '').strip()
ALFA_API_PASSWORD = os.getenv('ALFA_API_PASSWORD', '').strip()
ALFA_HTTP_TIMEOUT = int(os.getenv('ALFA_HTTP_TIMEOUT', '60'))
# Только явный ALFA_MERCHANT (terminal id в это поле часто даёт errorCode 1 «Некорректный запрос»)
ALFA_MERCHANT = os.getenv('ALFA_MERCHANT', '').strip()
# Опционально: отдельный логин для getTemplateDetails (часто *-operator), если *-api даёт errorCode 5
ALFA_TEMPLATES_DETAILS_USERNAME = os.getenv('ALFA_TEMPLATES_DETAILS_USERNAME', '').strip()
ALFA_TEMPLATES_DETAILS_PASSWORD = os.getenv('ALFA_TEMPLATES_DETAILS_PASSWORD', '').strip()

# Alfa acquiring (dynamic orders): return/fail URLs for register.do
ALFA_RETURN_URL = os.getenv('ALFA_RETURN_URL', 'https://example.com/pay/success').strip()
ALFA_FAIL_URL = os.getenv('ALFA_FAIL_URL', 'https://example.com/pay/fail').strip()
ALFA_SESSION_TIMEOUT_SECS = int(os.getenv('ALFA_SESSION_TIMEOUT_SECS', '900'))

# Автозаполнение для POST .../sbp-gateway/templates/create/ (только price)
SBP_GATEWAY_TEMPLATE_QR_WIDTH = int(os.getenv('SBP_GATEWAY_TEMPLATE_QR_WIDTH', '300'))
SBP_GATEWAY_TEMPLATE_QR_HEIGHT = int(os.getenv('SBP_GATEWAY_TEMPLATE_QR_HEIGHT', '300'))
SBP_GATEWAY_TEMPLATE_DIST_CHANNEL = os.getenv('SBP_GATEWAY_TEMPLATE_DIST_CHANNEL', 'CheckAvto').strip()
SBP_GATEWAY_TEMPLATE_VALID_YEARS = int(os.getenv('SBP_GATEWAY_TEMPLATE_VALID_YEARS', '10'))
SBP_GATEWAY_TEMPLATE_NAME_PREFIX = os.getenv('SBP_GATEWAY_TEMPLATE_NAME_PREFIX', 'CheckAvto').strip()

# СБП: статическая ссылка на QR (НСПК), из личного кабинета банка
SBP_QR_PAY_URL = os.getenv(
    'SBP_QR_PAY_URL',
    'https://qr.nspk.ru/BS1A003T9OBLQLD499DOHMC28RE9OHG7?type=01&bank=100000000008&crc=2E88',
).strip()
# Секрет для POST /api/auth/balance/sbp-webhook/ (заголовок X-Sbp-Webhook-Secret)
SBP_WEBHOOK_SECRET = os.getenv('SBP_WEBHOOK_SECRET', '').strip()

# SMS сервис настройки
SMS_SERVICE = 'smsc'  # Основной SMS сервис
SMS_FALLBACK_SERVICE = 'smsc'  # Резервный SMS сервис

# Альтернативные SMS сервисы (для будущего использования)
# SMS_RU_LOGIN = 'your-sms-ru-login'
# SMS_RU_PASSWORD = 'your-sms-ru-password'
# SMS_RU_API_URL = 'https://sms.ru/sms/send'

# DRF Spectacular Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Check Avto APIs',
    'DESCRIPTION': 'Check Avto Apies - JWT Authentication Required',
    'VERSION': 'v1',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'SWAGGER_UI_FAVICON_HREF': '/static/favicon.ico',
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': True,
        'hideHostname': True,
    },
    'SERVERS': [
        {'url': 'http://31.128.43.149:6060', 'description': 'Production server'},
        {'url': 'http://localhost:8002', 'description': 'Development server'},
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'Cars', 'description': 'Car management endpoints'},
        {'name': 'Masters', 'description': 'Master/service provider endpoints'},
        {'name': 'Orders (Driver)', 'description': 'Order endpoints for Driver (client)'},
        {'name': 'Orders (Master)', 'description': 'Order endpoints for Master (service provider)'},
        {'name': 'Categories', 'description': 'Category management endpoints'},
        {'name': 'Payments', 'description': 'Balance top-up via SBP QR'},
    ],
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
    'GENERIC_ADDITIONAL_PROPERTIES': None,
    'CAMPAIGN': None,
    'CONTACT': {
        'name': 'API Support',
        'email': 'contact@snippets.local',
    },
    'LICENSE': {
        'name': 'BSD License',
    },
}