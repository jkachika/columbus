"""
Django settings for columbus project on production server.
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import mimetypes
import socket

mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Webservice for Galileo. Needed only when columbus is integrated to work with galileo.
# See the deployment of Galileo Web Service here. https://github.com/jkachika/galileo-web-service
WEBSERVICE_HOST = 'http://www.columbus.cs.colostate.edu/galileo-web-service'
# The port number on which the Columbus master listens for workers to connect and communicate
SUPERVISOR_PORT = 56789
# The maximum memory allowed for any process to execute a Target of any workflow. Set this to an optimal value
# depending on your needs. When a target requires more memory than that is set here, the worker retries the
# Target by doubling the container size every time.
CONTAINER_SIZE_MB = 1024  # 1024 MB containers for any target
# The directory path without trailing slash where the serialization files or pickles are stored on both
# master and workers. The directory must be present with read and write permissions to the user running the application
USER_DIRPATH = '/mnt/ldsk'
# Google cloud storage bucket name for fault tolerance and data transfers between master and workers
USER_GCSPATH = 'gcs-bucket-name'
# Temporary directory path without trailing slash where files are stored for temporary purpose such as while uploading
# data to the cloud or during the creation of fusion tables. Files will not be cleared by the application from this path
TEMP_DIRPATH = '/mnt/tdsk'

# Do not change. Used for internal purposes.
BQ_TABLES = 'bigquery.tables'
BQ_FEATURES = 'bigquery.features'
BQ_FEATURES_SUFFIX = '::features'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Place all the service account files in this directory
SECURED_DIR = os.path.join(BASE_DIR, 'secured')

# Do not change. Used for internal purposes.
REQUIRES_DIR = os.path.join(BASE_DIR, 'requires')

# service account credentials from Google dev console for Google Earth Engine. Required if GIS computations are
# performed in the Targets.
EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Bigquery. Required if Bigquery serves as one of
# the data source options.
BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
# service account credentials from Google dev console for Google Cloud Storage. Required for fault tolerance and data
# transfers. The service account listed here must have full permissions to the bucket listed for the property
# USER_GCSPATH above
CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# service account credentials from Google dev console for Google Fusion Tables and Google Drive. Required to enable
# web-mapping visualizations.
FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
# client secret to gain access to end users google drive. Required to obtain permission to client's Google Drive if
# the same is serving as one of the data source options.
GD_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-client-secret.json')

# WORKERS CONFIGURATION
# the list of fully qualified worker host names. Master must be able to login to all those workers using
# passwordless SSH.
WORKERS = [socket.getfqdn()]
# default is ~/columbus. If specified path must be fully qualified
WORKER_VIRTUAL_ENV = None
# port number to SSH into the worker machines
WORKER_SSH_PORT = 22
# username to SSH into the worker machines
WORKER_SSH_USER = 'johnsoncharles26'
# password if any to SSH into the worker machines. If passwordless SSH is enabled and the private key has a passphrase
# this must be that passphrase.
WORKER_SSH_PASSWORD = None
# fully qualified path for the priavte key file. if not specified ~/.ssh/id_rsa is tried
WORKER_SSH_PRIVATE_KEY = None

# Scheduler Configuration
# must be one of local, remote, hybrid
# learn about the scheduling strategies from the Columbus paper. If not sure, leave the defaults
PIPELINE_SCHEDULING_STRATEGY = "hybrid"
# waiting-running target ratio used only for hybrid scheduling strategy.
# Default is 1, meaning targets are sent to the same worker as long as the number
# of targets waiting is less than or equal to the number of running targets of any user
HYBRID_SCHEDULING_WR_RATIO = 1

# Cloud Storage Bucket to use for temporary file storing while communicating with Google Earth Engine.
# The service account key specified for EE_CREDENTIALS must have full access to this bucket.
CS_TEMP_BUCKET = 'staging.columbus-csu.appspot.com'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Change the key to something else after deployment
SECRET_KEY = '3bg_5!omle5)+60!(qndj2!#yi+d%2oug2ydo(*^nup+9if0$k'
# Remove the following debug params after successful deployment
DEBUG = True

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

# Do not forget to whitelist the IP of compute engine accessing this database in the Google cloud sql, assuming the
# database is running on Google cloud SQL.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # assuming the database is MySQL
        'NAME': 'database-name',  # name of the database to use
        'USER': 'user-name',  # user name to use while connecting to the database
        'PASSWORD': 'password',  # password to use while connecting the database
        'HOST': 'mysql-ip-address',  # public IP of the database server
        'PORT': '3306'  # port number of the database server
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# list of domain names to which django server should serve. Must be specified when DEBUG = False
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

LOGIN_URL = '/login'
LOGOUT_URL = '/login'

# Change the admin name and email address
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

# Use appropriate prefix to add to the subject line of all the emails sent from the application
EMAIL_SUBJECT_PREFIX = '[Columbus] '
# Email address of the sender to use while sending emails from the application.
# Typically, noreply@somedomain.com
EMAIL_SENDER = 'Sender Name <senders email address including angular brackets>'

# Change the manager name and email address
MANAGERS = (
    ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
)

SEND_BROKEN_LINK_EMAILS = True

# Logger settings
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
