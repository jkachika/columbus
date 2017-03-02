#!/usr/bin/env python
import os
import socket
import sys

if __name__ == "__main__":
    if socket.gethostname() == 'Jo_SpectreX':
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "columbus.dev_settings")
    elif socket.gethostname() == 'columbus-dev-server':
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "columbus.test_settings")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "columbus.prod_settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
