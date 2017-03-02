import socket

if socket.gethostname() == 'Jo_SpectreX':
    from columbus.dev_settings import *
elif socket.gethostname() == 'columbus-dev-server':
    from columbus.test_settings import *
else:
    from columbus.prod_settings import *