import os
import signal
from django.core.exceptions import MiddlewareNotUsed


class ColumbusMiddleware(object):
    def __init__(self):
        current_pid = os.getpid()
        print "Checking for an already running supervisor"
        if os.path.exists('columbus-supervisor.pid'):
            with open('columbus-supervisor.pid', 'rb') as handle:
                existing_pid = int(handle.read())
            if existing_pid != current_pid:
                try:
                    os.kill(existing_pid, 0)
                    print "found a supervisor running in a different process with id " + str(existing_pid)
                    print "killing the existing supervisor"
                    os.kill(existing_pid, signal.SIGTERM)
                    print "killed the existing supervisor successfully"
                except OSError:
                    pass
            else:
                return
        with open('columbus-supervisor.pid', 'wb') as handle:
            handle.write(str(current_pid))
        from pyedf.coreengine import Supervisor
        supervisor = Supervisor()
        supervisor.start()
        raise MiddlewareNotUsed("Supervisor is up and running")
