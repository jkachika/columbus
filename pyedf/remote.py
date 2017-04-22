import logging
import os
import socket

import getpass
import paramiko
import traceback
from columbus import settings

logger = logging.getLogger(__name__)


class AllowAllKeys(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return


def release_resource(resource):
    if resource is not None:
        resource.close()


def exec_commands(hostname, commands, port=22, username=None, password=None, key_filename=None):
    client, channel, std_in, std_out = None, None, None, None
    try:
        if username is None:
            username = getpass.getuser()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, key_filename=key_filename)
        channel = client.invoke_shell()
        std_in = channel.makefile('wb')
        std_out = channel.makefile('rb')
        std_in.write(commands)
        if '\nexit\n' not in commands:
            std_in.write('exit\n')
        output = std_out.read()
        logger.info()
        return output
    except BaseException as e:
        logger.error("Something went wrong while executing the commands on host %s" % hostname)
        logger.error(traceback.format_exc())
        return e
    finally:
        release_resource(std_in)
        release_resource(std_out)
        release_resource(channel)
        release_resource(client)


def install_prerequisites(hostname, port=22, username=None, password=None, key_filename=None):
    client, channel, std_in, std_out = None, None, None, None
    try:
        if username is None:
            username = getpass.getuser()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, key_filename=key_filename)
        channel = client.invoke_shell()
        std_in = channel.makefile('wb')
        std_out = channel.makefile('rb')
        # exit must be present at the end of last std_in to get the output
        std_in.write(('sudo apt-get update\n'
                      'curl -O https://bootstrap.pypa.io/get-pip.py\n'
                      'sudo python get-pip.py\n'
                      'sudo pip install virtualenv\n'
                      'sudo apt-get install -y build-essential libmysqlclient-dev python-dev libssl-dev '
                      'libffi-dev libxml2-dev libxslt-dev\n'
                      'exit\n'))
        logger.info(std_out.read())
    except BaseException as e:
        logger.error("Something went wrong while installing the prerequisites on host %s" % hostname)
        logger.error(traceback.format_exc())
        raise e
    finally:
        release_resource(std_in)
        release_resource(std_out)
        release_resource(channel)
        release_resource(client)


def install_worker(hostname, virtualenv=None, upgrade=False, port=22, username=None, password=None, key_filename=None):
    client, channel, sftp, std_in, std_out = None, None, None, None, None
    try:
        if username is None:
            username = getpass.getuser()
        installables = []
        for installable in os.listdir(settings.REQUIRES_DIR):
            installables.append((installable, "%s/%s" % (settings.REQUIRES_DIR, installable)))
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, key_filename=key_filename)
        sftp = client.open_sftp()
        if not virtualenv:
            virtualenv = "%s/columbus" % str(sftp.normalize('.'))
        channel = client.invoke_shell()
        std_in = channel.makefile('wb')
        std_out = channel.makefile('rb')
        logger.debug("writing commands to channel for host %s" % hostname)
        if not upgrade:
            logger.info("Initiating installation on %s" % hostname)
            std_in.write(('mkdir -p %s\n'
                          'virtualenv --no-site-packages -p /usr/bin/python2.7 %s\n'
                          'exit\n') % (virtualenv, virtualenv))
            logger.info(std_out.read())
            release_resource(std_in)
            release_resource(std_out)
            release_resource(channel)
            channel = client.invoke_shell()
            std_in = channel.makefile('wb')
            std_out = channel.makefile('rb')
        else:
            logger.info("Initiating upgrade on %s" % hostname)
        for installable, local_path in installables:
            remote_path = "%s/%s" % (virtualenv, installable)
            logger.info("Uploading %s to %s:%s" % (local_path, hostname, remote_path))
            sftp.put(local_path, remote_path)
            std_in.write('cd %s\nsource bin/activate\npip install --upgrade %s\ndeactivate\n' % (
                virtualenv, remote_path))
        std_in.write('exit\n')
        logger.debug("write successful")
        logger.info(std_out.read())
        logger.debug("read successful")
    except BaseException as e:
        logger.error("Something went wrong while installing/upgrading the installables on host %s" % hostname)
        logger.error(traceback.format_exc())
        raise e
    finally:
        release_resource(std_in)
        release_resource(std_out)
        release_resource(channel)
        release_resource(sftp)
        release_resource(client)


def start_worker(hostname, master_port, virtualenv=None, port=22, username=None, password=None, key_filename=None):
    client, channel, std_in, std_out = None, None, None, None
    try:
        if username is None:
            username = getpass.getuser()
        master = socket.getfqdn()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, key_filename=key_filename)
        channel = client.invoke_shell()
        std_in = channel.makefile('wb')
        std_out = channel.makefile('rb')
        logger.debug("writing commands to channel for host %s" % hostname)
        std_in.write('cd %s\nsource bin/activate\nnohup python -m colorker %s %d %s/%s.log &\ndeactivate\n' % (
            virtualenv, str(master), int(master_port), virtualenv, hostname))
        std_in.write('ps -u %s\nexit\n' % username)
        logger.debug("write successful")
        logger.info(std_out.read())
        logger.debug("read successful")
    except BaseException as e:
        logger.error("Failed to start the worker on host %s" % hostname)
        logger.error(traceback.format_exc())
        raise e
    finally:
        release_resource(std_in)
        release_resource(std_out)
        release_resource(channel)
        release_resource(client)


def force_stop_worker(hostname, port=22, username=None, password=None, key_filename=None):
    client, channel, std_in, std_out = None, None, None, None
    try:
        if username is None:
            username = getpass.getuser()
        # CAUTION: if a worker is running on the master machine, both get killed
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, key_filename=key_filename)
        channel = client.invoke_shell()
        std_in = channel.makefile('wb')
        std_out = channel.makefile('rb')
        std_in.write('pkill python > /dev/null 2>&1\nps -u %s\nexit\n' % username)
        logger.debug("write successful")
        logger.info(std_out.read())
        logger.debug("read successful")
    except BaseException as e:
        logger.error("Failed to stop the worker on host %s" % hostname)
        logger.error(traceback.format_exc())
        raise e
    finally:
        release_resource(std_in)
        release_resource(std_out)
        release_resource(channel)
        release_resource(client)
