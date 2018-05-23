import os
import subprocess

import requests


def launch_putty(ip_address):

    cwd = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(cwd)
    
    ppk_file = os.path.join(root_dir, 'tokens', 'chofmann-wri.ppk')
    
    if not os.path.exists(ppk_file):
        raise ValueError('Could not find ppk file {}'.format(ppk_file))
        
    host_name = 'ubuntu@{0}'.format(ip_address)
    
    cmd = ['putty', host_name, '-ssh', '-i', ppk_file]
    
    subprocess.Popen(cmd)


def in_office():
    
    # check our external IP
    # if we're out of the office, will have to use private IP and VPN

    in_office = False

    # https://stackoverflow.com/a/36205547/4355916
    r = requests.get('https://api.ipify.org')
    ip = r.text


    if ip == '216.70.220.184':
        in_office = True

    return in_office

