"""
WSGI config for columbus project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
# import sys
import socket
from django.core.wsgi import get_wsgi_application

# sys.path.append('/home/ec2-user/venv/columbus')
# sys.path.append('/home/ec2-user/venv/columbus/columbus')

if socket.gethostname() == 'Jo_SpectreX' or socket.gethostname() == 'tongue':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "columbus.dev_settings")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "columbus.prod_settings")

application = get_wsgi_application()
