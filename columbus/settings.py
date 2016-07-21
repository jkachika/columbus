import socket

if socket.gethostname() == 'Jo_SpectreX':
    from columbus.dev_settings import *
else:
    from columbus.prod_settings import *