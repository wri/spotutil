import os
from fabric.operations import run, put, sudo
from fabric.api import env
from retrying import retry

# lots of connection attempts given that we're waiting for machine to start
env.connection_attempts = 20


def start_process(local_file_name, proc_type):

    basename = os.path.basename(local_file_name)
    remote_file_path = r'/home/ubuntu/{}'.format(basename)

    put(local_file_name, remote_file_path)

    # cmd has to be string, apparently
    cmd = ' '.join(['python', remote_file_path])

    if proc_type == 'prep':
        run(cmd)

    else:
        # source: http://www.prschmid.com/2014/02/running-background-tasks-with-fabric.html
        install_dtach()

        sockname = 'dtach'
        run("dtach -n `mktemp -u /tmp/{}.XXXX` {}".format(sockname, cmd))


@retry(wait_fixed=15000, stop_max_attempt_number=10)
def install_dtach():
    print 'trying to install dtach-- may run into issues given that machine still starting'
    print 'set to retry this every 15 seconds + fail after 10 attempts'
    sudo("apt-get install dtach")
