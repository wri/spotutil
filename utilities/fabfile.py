import os
from fabric.operations import run, put, sudo
from fabric.api import env

# lots of connection attempts given that we're waiting for machine to start
env.connection_attempts = 20


def start_process(local_file_name, proc_type):

    print os.path.realpath(local_file_name)

    basename = os.path.basename(local_file_name)
    remote_file_path = r'/home/ubuntu/{}'.format(basename)

    put(local_file_name, remote_file_path)

    # cmd has to be string, apparently
    cmd = ' '.join(['python', remote_file_path])

    if proc_type == 'prep':
        run(cmd)

    else:
        # source: http://www.prschmid.com/2014/02/running-background-tasks-with-fabric.html
        sudo("apt-get install dtach")

        sockname = 'dtach'
        run("dtach -n `mktemp -u /tmp/{}.XXXX` {}".format(sockname, cmd))
