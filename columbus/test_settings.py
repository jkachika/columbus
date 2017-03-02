"""
Django settings for columbus project on production server.
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import socket
import mimetypes

mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Webservice for Galileo. Needed only when columbus is integrated to work with galileo.
WEBSERVICE_HOST = 'http://tomcat.columbus-sandbox.tk/galileo-web-service'
SUPERVISOR_PORT = 56789
CONTAINER_SIZE_MB = 256  # 256 MB containers for any target
USER_DIRPATH = '/mnt/ldsk/'
USER_GCSPATH = '/mnt/bdsk/'
TEMP_DIRPATH = '/mnt/tdsk/'
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
WORKERS = [socket.getfqdn()]
# default is ~/columbus. If specified path must be fully qualified
WORKER_VIRTUAL_ENV = None
WORKER_SSH_PORT = 22
WORKER_SSH_USER = 'johnsoncharles26'
# used for password based login or as passphrase for private key file
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

# Cloud Storage Bucket to use for temporary file storing. The service account key specified for EE_CREDENTIALS must have
# full access to this bucket.
CS_TEMP_BUCKET = 'staging.columbus-csu.appspot.com'

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

# list of host names to which django server should serve. Must be specified when DEBUG = False
ALLOWED_HOSTS = ['www.columbus.cs.colostate.edu']

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

LOGIN_URL = '/login/'
LOGOUT_URL = '/login/'
# LOGIN_REDIRECT_URL = '/home'

ADMINS = [
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
]

# Refer to configuring sendgrid using Postfix on Google Compute Engine here
# https://cloud.google.com/compute/docs/tutorials/sending-mail/using-sendgrid
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'sendgrid-username'
EMAIL_HOST_PASSWORD = 'sendgrid-password'
EMAIL_PORT = 2525
EMAIL_USE_TLS = True

EMAIL_SUBJECT_PREFIX = '[Columbus] '
EMAIL_SENDER = 'Sender Name <senders email address including angular brackets>'

MANAGERS = (
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
)

SEND_BROKEN_LINK_EMAILS = True


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