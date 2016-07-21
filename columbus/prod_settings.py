"""
Django settings for columbus project on production server.
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import mimetypes

mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Webservice for Galileo. Needed only when columbus is integrated to work with galileo.
WEBSERVICE_HOST = 'http://tongue.cs.colostate.edu:8787/columbus'
USER_DIRPATH = '/mnt/ldsk/'
USER_GCSPATH = '/mnt/bdsk/'
TEMP_DIRPATH = '/mnt/tdsk/'
BQ_TABLES = 'bigquery.tables'
BQ_FEATURES = 'bigquery.features'
BQ_FEATURES_SUFFIX = '::features'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECURED_DIR = os.path.join(BASE_DIR, 'secured')
# service account credentials from Google dev console for Google Earth Engine
EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Bigquery
BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
# service account credentials from Google dev console for Google Cloud Storage
CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Fusion Tables and Google Drive
FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Change the key to something else after deployment
SECRET_KEY = '3bg_5!omle5)+60!(qndj2!#yi+d%2oug2ydo(*^nup+9if0$k'
# Remove the following debug params after successful deployment
DEBUG = True
# TEMPLATE_DEBUG = True

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pyedf',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'columbus.urls'
# WSGI_APPLICATION = 'columbus.wsgi.application'

# Do not forget to whitelist the ip of compute engine in cloud sql
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'database-name',
        'USER': 'user-name',
        'PASSWORD': 'password',
        'HOST': 'mysql-ip-address',
        'PORT': '3306'
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# static file directory inclusion
# STATICFILES_DIRS = (
#     os.path.join(BASE_DIR, 'static'),
# )


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR + '/templates/'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Application settings

LOGIN_URL = '/login'
LOGOUT_URL = '/login'
LOGIN_REDIRECT_URL = '/home'

ADMINS = (
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
)

# EMAIL_HOST =
# EMAIL_HOST_USER =
# EMAIL_HOST_PASSWORD =
# EMAIL_PORT =
# EMAIL_USE_TLS =

EMAIL_SUBJECT_PREFIX = '[Columbus] '

MANAGERS = (
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
)

SEND_BROKEN_LINK_EMAILS = False


# Logger settings
# dev_settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'edffile': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'pyedf.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose'
        },
        'djangofile': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['djangofile'],
            'propagate': True,
            'level': 'ERROR',
        },
        'pyedf': {
            'handlers': ['edffile'],
            'level': 'INFO',
        },
    }
}