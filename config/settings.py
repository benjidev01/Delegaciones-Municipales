import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
local = Path(os.environ.get('DJANGO_CONFIG_FILE', BASE_DIR / '.local' / 'config.json'))
LOCAL = json.loads(local.read_text()) if local.exists() else {}

def setting(name, default=None):
    return os.environ.get(name, LOCAL.get(name, default))

SECRET_KEY = setting('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('Configure DJANGO_SECRET_KEY o ejecute scripts/prepare.py.')
DEBUG = setting('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = setting('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'axes', 'apps.delegaciones', 'apps.cuentas', 'apps.vecinos',
    'apps.solicitudes', 'apps.auditoria', 'apps.agenda', 'apps.reportes',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'config.middleware.DatosPrivadosMiddleware',
    'config.middleware.InactividadMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 'axes.middleware.AxesMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
    'NAME': setting('POSTGRES_DB', 'delegaciones'), 'USER': setting('POSTGRES_USER', 'delegaciones'),
    'PASSWORD': setting('POSTGRES_PASSWORD'), 'HOST': setting('POSTGRES_HOST', '127.0.0.1'),
    'PORT': setting('POSTGRES_PORT', '55432')}}
AUTH_USER_MODEL = 'cuentas.Usuario'
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend', 'django.contrib.auth.backends.ModelBackend']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_LOCKOUT_TEMPLATE = 'registration/locked.html'
AXES_CLIENT_IP_CALLABLE = 'config.network.client_ip'
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = Path(setting('DJANGO_STATIC_ROOT', BASE_DIR / 'staticfiles'))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800
SESSION_IDLE_TIMEOUT = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Enable only behind a private proxy that overwrites the forwarded headers.
TRUST_PROXY = setting('DJANGO_TRUST_PROXY', 'false').lower() == 'true'
if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
