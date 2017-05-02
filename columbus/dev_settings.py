"""
Django settings for columbus project.

Generated by 'django-admin startproject' using Django 1.8.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import mimetypes
import socket

mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Webservice for Galileo. Needed only when columbus is integrated to work with galileo.
WEBSERVICE_HOST = 'http://tomcat.columbus.cs.colostate.edu/galileo-web-service'
SUPERVISOR_PORT = 56789
CONTAINER_SIZE_MB = 256  # 256 MB containers for any target
USER_DIRPATH = 'D:/_LCL'
USER_GCSPATH = 'columbus-csu.appspot.com'
TEMP_DIRPATH = 'D:/_TMP/'
BQ_TABLES = 'bigquery.tables'
BQ_FEATURES = 'bigquery.features'
BQ_FEATURES_SUFFIX = '::features'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECURED_DIR = os.path.join(BASE_DIR, 'secured')
REQUIRES_DIR = os.path.join(BASE_DIR, 'requires')
# service account credentials from Google dev console for Google Earth Engine
EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Bigquery
BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
# service account credentials from Google dev console for Google Cloud Storage
CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Fusion Tables and Google Drive
FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# client secret to gain access to end users google drive
GD_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-client-secret.json')

# WORKERS CONFIGURATION
# file having the list of worker host names one on each line
WORKERS = ['aries.c.columbus-csu.internal', 'taurus.c.columbus-csu.internal', 'gemini.c.columbus-csu.internal',
           'cancer.c.columbus-csu.internal', 'leo.c.columbus-csu.internal', 'virgo.c.columbus-csu.internal',
           'libra.c.columbus-csu.internal', 'scorpio.c.columbus-csu.internal', 'sagittarius.c.columbus-csu.internal',
           'capricorn.c.columbus-csu.internal', 'aquarius.c.columbus-csu.internal', 'pisces.c.columbus-csu.internal']
# default is ~/columbus. If specified path must be fully qualified
WORKER_VIRTUAL_ENV = None
WORKER_SSH_PORT = 22
WORKER_SSH_USER = 'johnsoncharles26'
WORKER_SSH_PASSWORD = None
# fully qualified path for the priavte key file. if not specified ~/.ssh/id_rsa is tried
WORKER_SSH_PRIVATE_KEY = None

# Scheduler Configuration
# must be one of local, remote, hybrid
PIPELINE_SCHEDULING_STRATEGY = "hybrid"
# waiting-running target ratio used only for hybrid scheduling strategy.
# Default is 1, meaning targets are sent to the same worker as long as the number
# of targets waiting is less than or equal to the number of running targets of any user
HYBRID_SCHEDULING_WR_RATIO = 1

# Cloud Storage Bucket to use for temporary file storing. The service account key specified for CS_CREDENTIALS must have
# full access to this bucket.
CS_TEMP_BUCKET = 'staging.columbus-csu.appspot.com'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '3bg_5!zlet5)+60!(shqj2!#yi+d%2tuk2ydo(*^bbf+9iz0$k'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# TEMPLATE_DEBUG = True
ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pyedf.apps.ColumbusConfig',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pyedf.middleware.ColumbusMiddleware',
)

ROOT_URLCONF = 'columbus.urls'
# WSGI_APPLICATION = 'columbus.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'columbus',
        'USER': 'jcharles',
        'PASSWORD': '830390177',
        'HOST': '127.0.0.1',
        'PORT': '3306'
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# static file directory inclusion
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

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

EMAIL_SENDER = 'Columbus <noreply@columbus.cs.colostate.edu>'

ADMINS = [
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
]

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/
LANGUAGE_CODE = 'en-us'
# Local timezone
TIME_ZONE = 'America/Denver'
USE_I18N = True
USE_L10N = True
# Use time zone information for saving date time fields
USE_TZ = True

# Application settings
LOGIN_URL = '/login/'
LOGOUT_URL = '/login/'
# LOGIN_REDIRECT_URL = '/home'

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
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'pyedf.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'INFO',
        },
        'pyedf': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    }
}
