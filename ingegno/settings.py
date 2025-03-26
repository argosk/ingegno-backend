import os
import sys
from datetime import timedelta
from pathlib import Path
from django.core.management.utils import get_random_secret_key
import dj_database_url
import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Reading .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('SECRET_KEY', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'tinymce',
    'django_celery_beat',

    'api',    
    'users',
    'connected_accounts',
    'subscriptions',
    'campaigns',
    'leads.apps.LeadsConfig',   
    'emails',
    # 'tracking', 
    'workflows.apps.WorkflowsConfig',
    # 'blog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ingegno.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ingegno.wsgi.application'

DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE') == 'True'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DEVELOPMENT_MODE = env.bool("DEVELOPMENT_MODE", False)

if DEVELOPMENT_MODE is True:
    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.sqlite3',
    #         'NAME': BASE_DIR / 'db.sqlite3',
    #     }
    # }
    DATABASES = {
        "default": dj_database_url.parse(env.str("DATABASE_URL_DEV")),
    }
elif len(sys.argv) > 0 and sys.argv[1] != 'collectstatic':
    if env.str("DATABASE_URL", None) is None:
        raise Exception("DATABASE_URL environment variable not defined")
    DATABASES = {
        "default": dj_database_url.parse(env.str("DATABASE_URL")),
    }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # Numero di elementi per pagina
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=20),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

CORS_ALLOW_CREDENTIALS = True

PASSWORD_RESET_TIMEOUT = 3600

FERNET_SECRET_KEY = SECRET_KEY[:32]  # Usa una parte della SECRET_KEY per generare la chiave

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.office365.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False  # Deve essere False se stai usando TLS
EMAIL_HOST_USER = 'mail@carouselly.com'  # La tua email Office365
EMAIL_HOST_PASSWORD = env.str('EMAIL_PASSWORD')  # La password del tuo account email
DEFAULT_FROM_EMAIL = 'mail@carouselly.com'

GOOGLE_CLIENT_ID = env.str('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = env.str('GOOGLE_CLIENT_SECRET', default='')
GOOGLE_REDIRECT_URI = env.str('GOOGLE_REDIRECT_URI', default='')

GMAIL_REDIRECT_URI = env.str('GMAIL_REDIRECT_URI', default='')

MICROSOFT_CLIENT_ID = env.str('MICROSOFT_CLIENT_ID', default='')
MICROSOFT_CLIENT_SECRET = env.str('MICROSOFT_CLIENT_SECRET', default='')
MICROSOFT_REDIRECT_URI = env.str('MICROSOFT_REDIRECT_URI', default='')

STRIPE_SECRET_KEY = env.str('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env.str('STRIPE_WEBHOOK_SECRET', default='')

FRONTEND_URL = env.str('FRONTEND_URL', default='')

OPENAI_API_KEY = env.str('OPENAI_API_KEY', default='')

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


OAUTH2_PROVIDERS = {
    'gmail': {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uri': GMAIL_REDIRECT_URI,
    },
    'outlook': {
        'client_id': MICROSOFT_CLIENT_ID,
        'client_secret': MICROSOFT_CLIENT_SECRET,
        'auth_uri': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        'token_uri': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        'redirect_uri': MICROSOFT_REDIRECT_URI,
        'scopes': [
            'https://graph.microsoft.com/Mail.Send',
            'https://graph.microsoft.com/Mail.Read',
            'https://graph.microsoft.com/User.Read',
            'offline_access'  # IMPORTANTE per ottenere il refresh token
        ]
    }
}

TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "height": 500,
    "menubar": False,
    "plugins": "advlist autolink lists link image charmap print preview anchor "
               "searchreplace visualblocks code fullscreen insertdatetime media table paste "
               "help wordcount",
    "toolbar": "undo redo | formatselect | "
               "bold italic backcolor | alignleft aligncenter "
               "alignright alignjustify | bullist numlist outdent indent | "
               "removeformat | code | help",  # Aggiungi il pulsante code
}


