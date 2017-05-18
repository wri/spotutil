import os
import subprocess


def launch_putty(ip_address):

    cwd = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(cwd)
    
    ppk_file = os.path.join(root_dir, 'tokens', 'chofmann-wri.ppk')
    
    if not os.path.exists(ppk_file):
        raise ValueError('Could not find ppk file {}'.format(ppk_file))
        
    host_name = 'ubuntu@{0}'.format(ip_address)
    
    cmd = ['putty', host_name, '-ssh', '-i', ppk_file]
    
    subprocess.check_call(cmd)